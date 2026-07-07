import re
import requests
from urllib.parse import quote, urljoin


FETCH_HEADERS = {
    'User-Agent': 'metadata-extractor/1.0 (+https://localhost)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
}


def _quote_doi(doi):
    return quote(doi, safe='/._;():-')


def _declared_response_encoding(response):
    content_type = ''
    headers = getattr(response, 'headers', None)
    if hasattr(headers, 'get'):
        content_type = headers.get('content-type', '') or ''

    match = re.search(r'charset=["\']?([^;"\']+)', str(content_type), flags=re.IGNORECASE)
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


def _redirect_url_with_fragment(response):
    for item in reversed(getattr(response, 'history', []) or []):
        location = ''
        headers = getattr(item, 'headers', None)
        if hasattr(headers, 'get'):
            location = headers.get('Location') or headers.get('location') or ''
        if '#' in str(location):
            return urljoin(getattr(item, 'url', '') or '', location)
    return None


def _flatten_crossref_value(value):
    if value is None:
        return ''
    if isinstance(value, list):
        return '; '.join(filter(None, [_flatten_crossref_value(item) for item in value]))
    if isinstance(value, dict):
        parts = []
        for key, nested_value in value.items():
            nested_text = _flatten_crossref_value(nested_value)
            if nested_text:
                parts.append(f'{key}: {nested_text}')
        return '; '.join(parts)
    return str(value).strip()


def _fetch_crossref_metadata(doi):
    url = f"https://api.crossref.org/works/{_quote_doi(doi)}"
    response = requests.get(url, headers=FETCH_HEADERS, timeout=10)
    response.raise_for_status()
    payload = response.json()
    message = payload.get('message', {})
    if not isinstance(message, dict):
        raise ValueError('Crossref response is missing message object')

    fields = [
        'DOI', 'URL', 'title', 'subtitle', 'abstract', 'author', 'container-title',
        'publisher', 'published-print', 'published-online', 'issued', 'subject',
        'license', 'link', 'reference', 'type',
    ]
    lines = ['Metadata Source: Crossref']
    for field in fields:
        text = _flatten_crossref_value(message.get(field))
        if text:
            lines.append(f'{field}: {text}')

    if len(lines) == 1:
        raise ValueError('Crossref response has no usable metadata')

    return {
        'content': '\n'.join(lines),
        'url': message.get('URL') or url,
        'source': 'crossref',
    }


def _fetch_landing_page(doi, clean_html):
    url = f"https://doi.org/{_quote_doi(doi)}"
    response = requests.get(url, headers=FETCH_HEADERS, timeout=10)
    response.raise_for_status()
    response.encoding = _select_response_encoding(response)
    content = response.text
    # if clean_html is not None:
    #     content = clean_html(content)
    if not content:
        raise ValueError('DOI landing page has no readable content')

    return {
        'content': content,
        'url': _redirect_url_with_fragment(response) or (response.url if isinstance(response.url, str) and response.url else url),
        'source': 'doi.org',
    }


def resolve_doi_landing_page(doi, clean_html=None):
    return _fetch_landing_page(doi, clean_html)


def resolve_doi_metadata(doi):
    return _fetch_crossref_metadata(doi)


def resolve_doi(doi, clean_html=None):
    try:
        return resolve_doi_landing_page(doi, clean_html)
    except Exception as landing_error:
        print(f"[WARNING] DOI landing page failed for {doi}, falling back to Crossref: {landing_error}")
        try:
            return resolve_doi_metadata(doi)
        except Exception as crossref_error:
            raise ValueError(
                f"Failed to resolve DOI {doi}; doi.org error: {landing_error}; "
                f"Crossref error: {crossref_error}"
            ) from crossref_error
