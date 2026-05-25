# 用于得到网页中的标识，并合成一个 list
import re


doi_pattern = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
# cstr_pattern = re.compile(r'\d{5}\.\d{2}\.\d{6}\.\d{6}')
cstr_pattern = re.compile(r'\d{5}\.\d{2}\.[-._;()/:A-Z0-9]+', re.IGNORECASE)
china_patent_pattern = re.compile(r'(?:CN|ZL)\d{9}(?:\.\d)?[A-Z]?')


def normalize_identifier(value):
    return value.strip().strip('.,;，；')


def get_typed_identifiers(text, include_patent=True):
    seen = set()
    identifiers = []

    for match in doi_pattern.findall(text or ''):
        identifier = normalize_identifier(match)
        key = ('doi', identifier.lower())
        if identifier and key not in seen:
            identifiers.append({'type': 'doi', 'id': identifier})
            seen.add(key)

    for match in cstr_pattern.findall(text or ''):
        identifier = normalize_identifier(match)
        key = ('cstr', identifier)
        if identifier and key not in seen:
            identifiers.append({'type': 'cstr', 'id': identifier})
            seen.add(key)

    if include_patent:
        for match in china_patent_pattern.findall(text or ''):
            identifier = normalize_identifier(match)
            key = ('patent', identifier)
            if identifier and key not in seen:
                identifiers.append({'type': 'patent', 'id': identifier})
                seen.add(key)

    return identifiers


def get_identifiers(text):
    return [item['id'] for item in get_typed_identifiers(text)]
