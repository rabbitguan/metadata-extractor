import json
import re
from urllib.parse import quote, urljoin, urlsplit

import requests
from urllib3.exceptions import InsecureRequestWarning


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


def _redirect_url_with_fragment(response):
    for item in reversed(getattr(response, 'history', []) or []):
        location = ''
        headers = getattr(item, 'headers', None)
        if hasattr(headers, 'get'):
            location = headers.get('Location') or headers.get('location') or ''
        if '#' in str(location):
            return urljoin(getattr(item, 'url', '') or '', location)
    return None


def _response_to_content(response, clean_html):
    content_type = _get_content_type(response)
    if 'json' in content_type:
        try:
            payload = response.json()
            _raise_for_resolver_error(payload)
            return json.dumps(payload, ensure_ascii=False, indent=2)
        except Exception:
            if _looks_like_json_text_error(response.text):
                raise
            return response.text

    content = response.text
    if _looks_like_cstr_error_page(response.url, content):
        raise ValueError('CSTR landing page did not return metadata')
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


def _declared_response_encoding(response):
    content_type = _get_content_type(response)
    match = re.search(r'charset=["\']?([^;"\']+)', content_type, flags=re.IGNORECASE)
    if match:
        return match.group(1).strip()

    raw_head = getattr(response, 'content', b'')[:4096]
    for pattern in (
        br'<meta[^>]+charset=["\']?([^"\' >]+)',
        br'<\?xml[^>]+encoding=["\']([^"\']+)',
    ):
        match = re.search(pattern, raw_head, flags=re.IGNORECASE)
        if match:
            return match.group(1).decode('ascii', errors='ignore').strip()
    return None


def _select_response_encoding(response):
    declared = _declared_response_encoding(response)
    if declared:
        return declared

    current = getattr(response, 'encoding', None)
    if current and str(current).lower() not in {'iso-8859-1'}:
        return current

    return getattr(response, 'apparent_encoding', None) or current or 'utf-8'


def _raise_for_resolver_error(payload):
    if not isinstance(payload, dict):
        return
    candidates = [payload]
    data = payload.get('data')
    if isinstance(data, dict):
        candidates.append(data)
        nested = data.get('data')
        if isinstance(nested, dict):
            candidates.append(nested)
    for item in candidates:
        code = str(item.get('code') or '').strip()
        status = str(item.get('status') or '').strip()
        detail = str(item.get('detail') or item.get('message') or '').strip()
        if code in {'404', '500'} or status in {'8', '404'} or detail.lower() in {'not found', 'notfound'}:
            raise ValueError(detail or 'CSTR resolver returned no metadata')


def _looks_like_json_text_error(text):
    try:
        payload = json.loads(text or '')
    except Exception:
        return False
    _raise_for_resolver_error(payload)
    return False


def _looks_like_cstr_error_page(url, content):
    normalized_url = str(url or '').lower()
    if 'cstr.cn' not in normalized_url:
        return False
    text = str(content or '').lower()
    return (
        'error.css' in text
        or '科技资源标识服务平台' in str(content or '')
        and '404' in text
        or 'not found' in text
    )


def _fetch_page(url, source, clean_html, redirect_depth=0):
    verify_tls = 'scids.bdware.cn' not in urlsplit(url).netloc.lower()
    if not verify_tls:
        requests.packages.urllib3.disable_warnings(category=InsecureRequestWarning)
    response = requests.get(url, headers=FETCH_HEADERS, timeout=10, verify=verify_tls)
    response.raise_for_status()
    response.encoding = _select_response_encoding(response)
    final_url = _redirect_url_with_fragment(response) or (response.url if isinstance(response.url, str) and response.url else url)

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


def _append_escience_supplemental(result, cstr):
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


def resolve_cstr_landing_page(cstr, clean_html=None):
    normalized_cstr = _normalize_cstr(cstr)
    quoted_cstr = quote(normalized_cstr, safe='._;()/:A-Z0-9-')
    result = _fetch_page(f'https://cstr.cn/{quoted_cstr}', 'cstr.cn', clean_html)
    return _append_escience_supplemental(result, cstr)


def resolve_cstr_metadata(cstr, clean_html=None):
    normalized_cstr = _normalize_cstr(cstr)
    quoted_cstr = quote(normalized_cstr, safe='._;()/:A-Z0-9-')
    result = _fetch_page(f'https://scids.bdware.cn/idutil/resolve?id={quoted_cstr}', 'scids.bdware.cn', clean_html)
    return _append_escience_supplemental(result, cstr)


def resolve_cstr(cstr, clean_html=None):
    normalized_cstr = _normalize_cstr(cstr)
    quoted_cstr = quote(normalized_cstr, safe='._;()/:A-Z0-9-')
    candidates = [
        ('known-resource', KNOWN_CSTR_RESOURCE_URLS[normalized_cstr.lower()]),
    ] if normalized_cstr.lower() in KNOWN_CSTR_RESOURCE_URLS else []
    candidates.extend([
        ('scids.bdware.cn', f'https://scids.bdware.cn/idutil/resolve?id={quoted_cstr}'),
        ('cstr.cn', f'https://cstr.cn/{quoted_cstr}'),
    ])
    errors = []

    for source, url in candidates:
        try:
            result = _fetch_page(url, source, clean_html)
            return _append_escience_supplemental(result, cstr)
        except Exception as error:
            errors.append(f'{source}: {error}')
            print(f"[WARNING] CSTR resolver {source} failed for {cstr}: {error}")

    raise ValueError(f"Failed to resolve CSTR {cstr}; " + '; '.join(errors))
