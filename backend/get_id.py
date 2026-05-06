# 用于得到网页中的标识，并合成一个 list
import re


doi_pattern = re.compile(r'10\.\d{4,9}/[-._;()/:A-Z0-9]+', re.IGNORECASE)
cstr_pattern = re.compile(r'\d{5}\.\d{2}\.\d{6}\.\d{6}')
china_patent_pattern = re.compile(r'(?:CN|ZL)\d{9}(?:\.\d)?[A-Z]?')


def get_identifiers(text):
    doi_ids = doi_pattern.findall(text)
    cstr_ids = cstr_pattern.findall(text)
    patent_ids = china_patent_pattern.findall(text)
    all_ids = list(set(doi_ids + cstr_ids + patent_ids))
    return all_ids