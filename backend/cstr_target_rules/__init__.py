from . import escience_ncdc


RULES = [
    escience_ncdc,
]


def resolve(cstr, clean_html=None):
    for rule in RULES:
        if rule.matches(cstr):
            return rule.resolve(cstr, clean_html=clean_html)
    return None
