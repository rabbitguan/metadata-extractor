import requests
from urllib.parse import quote


FETCH_HEADERS = {
    'User-Agent': 'metadata-extractor/1.0 (+https://localhost)',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,application/json;q=0.8,*/*;q=0.7',
}


def _quote_doi(doi):
    return quote(doi, safe='/._;():-')


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
    content = response.text
    # if clean_html is not None:
    #     content = clean_html(content)
    if not content:
        raise ValueError('DOI landing page has no readable content')

    return {
        'content': content,
        'url': response.url if isinstance(response.url, str) and response.url else url,
        'source': 'doi.org',
    }


def resolve_doi(doi, clean_html=None):
    try:
        return _fetch_landing_page(doi, clean_html)
    except Exception as landing_error:
        print(f"[WARNING] DOI landing page failed for {doi}, falling back to Crossref: {landing_error}")
        try:
            return _fetch_crossref_metadata(doi)
        except Exception as crossref_error:
            raise ValueError(
                f"Failed to resolve DOI {doi}; doi.org error: {landing_error}; "
                f"Crossref error: {crossref_error}"
            ) from crossref_error
