import json
import re
from urllib.parse import quote, urljoin, urlsplit

import requests


FETCH_HEADERS = {
    'User-Agent': 'metadata-extractor/1.0 (+https://localhost)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
}


def _extract_json_redirect(value):
    if not isinstance(value, dict):
        return None

    for key in ('url', 'href', 'location', 'redirect', 'redirectUrl', 'target', 'targetUrl'):
        target = value.get(key)
        if isinstance(target, str) and target.startswith(('http://', 'https://', '/')):
            return target

    data = value.get('data')
    if isinstance(data, dict):
        return _extract_json_redirect(data)
    return None


def _extract_html_redirect(html):
    patterns = [
        r'<meta[^>]+http-equiv=["\']?refresh["\']?[^>]+content=["\'][^"\']*url=([^"\';>]+)',
        r'(?:window\.)?location(?:\.href)?\s*=\s*["\']([^"\']+)["\']',
        r'location\.(?:replace|assign)\(["\']([^"\']+)["\']\)',
    ]
    for pattern in patterns:
        match = re.search(pattern, html or '', re.IGNORECASE)
        if match:
            return match.group(1).strip()
    return None


def _extract_redirect_target(response):
    content_type = _get_content_type(response)
    if 'json' in content_type:
        try:
            return _extract_json_redirect(response.json())
        except Exception:
            return None
    return _extract_html_redirect(response.text)


def _same_netloc(left, right):
    return urlsplit(left or '').netloc.lower() == urlsplit(right or '').netloc.lower()


def _should_extract_embedded_redirect(request_url, final_url):
    # After a resolver HTTP redirect reaches the real resource page, do not
    # treat arbitrary page JavaScript as another redirect.
    return _same_netloc(request_url, final_url)


def _response_to_content(response, clean_html):
    content_type = _get_content_type(response)
    if 'json' in content_type:
        try:
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception:
            return response.text

    content = response.text
    # if clean_html is not None:
    #     content = clean_html(content)
    # 这里 clean_html 的逻辑可以去除，因为 extractor 用的是原始 html
    return content


def _get_content_type(response):
    headers = getattr(response, 'headers', None)
    if hasattr(headers, 'get'):
        content_type = headers.get('content-type', '')
        if isinstance(content_type, str):
            return content_type.lower()
    return ''


def _fetch_page(url, source, clean_html, redirect_depth=0):
    response = requests.get(url, headers=FETCH_HEADERS, timeout=10)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding
    final_url = response.url if isinstance(response.url, str) and response.url else url

    redirect_target = None
    if _should_extract_embedded_redirect(url, final_url):
        redirect_target = _extract_redirect_target(response)
    if redirect_target and redirect_depth < 3:
        next_url = urljoin(final_url, redirect_target)
        if next_url != final_url:
            return _fetch_page(next_url, f'{source}->redirect', clean_html, redirect_depth + 1)

    content = _response_to_content(response, clean_html)
    if not content:
        raise ValueError(f'{source} page has no readable content')

    return {
        'content': content,
        'url': final_url,
        'source': source,
    }


ESCIENCE_ORG_IDS = {
    'ncdc': '9bc0652f0dce29823c0c9842001ae890',
    'tpdc': 'da0e21dd01bcbea6d33bd0c6ce9c2c33',
    'micro': '774e79461ac511e980780242ac120006',
}

KNOWN_CSTR_RESOURCE_URLS = {
    '13913.12.micro.ncov.sequence': 'https://nmdc.cn/resource/ncov/globalsequence/',
}


def _normalize_cstr(cstr):
    return re.sub(r'^CSTR\s*:\s*', '', str(cstr or '').strip(), flags=re.IGNORECASE)


def build_escience_metadata_url(cstr, org_id=None):
    normalized = _normalize_cstr(cstr)
    if not normalized:
        return None

    org_id = org_id or ESCIENCE_ORG_IDS['ncdc']
    prefixed = f'CSTR:{normalized}'
    resource_id = f'{org_id}:{prefixed}'
    return (
        'https://www.escience.org.cn/metadata/detail'
        f'?id={quote(resource_id, safe="")}'
        f'&cstrId={quote(prefixed, safe="")}'
    )


def _select_escience_org_id(cstr, resolved_url=''):
    normalized_cstr = str(cstr or '').lower()
    normalized_url = str(resolved_url or '').lower()
    if 'ncdc.ac.cn' in normalized_url or '.ncdc.' in normalized_cstr:
        return ESCIENCE_ORG_IDS['ncdc']
    if 'data.tpdc.ac.cn' in normalized_url or '.tpdc.' in normalized_cstr:
        return ESCIENCE_ORG_IDS['tpdc']
    if 'nmdc.cn' in normalized_url or '.micro.' in normalized_cstr:
        return ESCIENCE_ORG_IDS['micro']
    return None


def resolve_cstr(cstr, clean_html=None):
    normalized_cstr = _normalize_cstr(cstr)
    quoted_cstr = quote(normalized_cstr, safe='._;()/:A-Z0-9-')
    candidates = [
        ('known-resource', KNOWN_CSTR_RESOURCE_URLS[normalized_cstr.lower()]),
    ] if normalized_cstr.lower() in KNOWN_CSTR_RESOURCE_URLS else []
    candidates.extend([
        ('cstr.cn', f'https://cstr.cn/{quoted_cstr}'),
        ('scids.bdware.cn', f'https://scids.bdware.cn/idutil/resolve?id={quoted_cstr}'),
    ])
    errors = []

    for source, url in candidates:
        try:
            result = _fetch_page(url, source, clean_html)
            result_url = str(result.get('url') or '').lower()
            escience_org_id = _select_escience_org_id(cstr, result_url)
            escience_url = build_escience_metadata_url(cstr, escience_org_id) if escience_org_id else None
            if escience_url:
                result['supplemental_urls'] = [
                    {
                        'source': 'escience.org.cn',
                        'url': escience_url,
                        'priority': 'fallback',
                    }
                ]
            return result
        except Exception as error:
            errors.append(f'{source}: {error}')
            print(f"[WARNING] CSTR resolver {source} failed for {cstr}: {error}")

    raise ValueError(f"Failed to resolve CSTR {cstr}; " + '; '.join(errors))
