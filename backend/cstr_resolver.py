import json
import re
from urllib.parse import quote, urljoin

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


def _response_to_content(response, clean_html):
    content_type = _get_content_type(response)
    if 'json' in content_type:
        try:
            return json.dumps(response.json(), ensure_ascii=False, indent=2)
        except Exception:
            return response.text

    content = response.text
    if clean_html is not None:
        content = clean_html(content)
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
    final_url = response.url if isinstance(response.url, str) and response.url else url

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


def build_escience_metadata_url(cstr):
    normalized = re.sub(r'^CSTR\s*:\s*', '', str(cstr or '').strip(), flags=re.IGNORECASE)
    if not normalized:
        return None

    prefixed = f'CSTR:{normalized}'
    resource_id = f'9bc0652f0dce29823c0c9842001ae890:{prefixed}'
    return (
        'https://www.escience.org.cn/metadata/detail'
        f'?id={quote(resource_id, safe="")}'
        f'&cstrId={quote(prefixed, safe="")}'
    )


def resolve_cstr(cstr, clean_html=None):
    quoted_cstr = quote(cstr, safe='._;()/:A-Z0-9-')
    candidates = [
        ('cstr.cn', f'https://cstr.cn/{quoted_cstr}'),
        ('scids.bdware.cn', f'https://scids.bdware.cn/idutil/resolve?id={quoted_cstr}'),
    ]
    errors = []

    for source, url in candidates:
        try:
            result = _fetch_page(url, source, clean_html)
            escience_url = build_escience_metadata_url(cstr)
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
