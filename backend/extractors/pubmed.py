from typing import Optional, Dict, Any
from bs4 import BeautifulSoup
import re


def matches(url: str, title: str, content: str) -> bool:
    return bool(url and ('pubmed.ncbi.nlm.nih.gov' in url or 'pubmed' in url))


def _text_or_none(el):
    if not el:
        return None
    if isinstance(el, str):
        return el.strip() or None
    return ' '.join(el.stripped_strings) or None


def _get_meta(soup: BeautifulSoup, name: str) -> Optional[str]:
    m = soup.find('meta', {'name': name})
    if m and m.get('content'):
        return m.get('content').strip() or None
    m2 = soup.find('meta', {'property': name})
    if m2 and m2.get('content'):
        return m2.get('content').strip() or None
    return None


def _split_authors_from_meta(val: Optional[str]) -> list:
    if not val:
        return []
    parts = [p.strip() for p in re.split(r';|,\s*(?=[A-Z][a-z])', val) if p.strip()]
    return parts


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    """Extract basic metadata from a PubMed article page HTML.

    This implementation prefers stable `citation_*` meta tags and falls
    back to several DOM selectors to tolerate different PubMed variants.
    """
    if not content:
        return None

    soup = BeautifulSoup(content, 'html.parser')

    # Title: prefer meta, then h1, then <title>
    title_meta = _get_meta(soup, 'citation_title')
    if not title_meta:
        title_meta = _get_meta(soup, 'og:title')
    h1 = soup.find('h1', class_='heading-title')
    title_text = title_meta or _text_or_none(h1) or (soup.title.string.strip() if soup.title and soup.title.string else None) or (title or None)

    # Authors: meta tags first, then visible author list
    authors = []
    meta_authors = [m.get('content').strip() for m in soup.find_all('meta', {'name': 'citation_authors'}) if m.get('content')]
    if meta_authors:
        for entry in meta_authors:
            authors.extend(_split_authors_from_meta(entry))
    else:
        for a in soup.select('.authors-list .authors-list-item .full-name, .authors-list .full-name, .author-list .full-name, .authors .full-name'):
            t = _text_or_none(a)
            if t:
                authors.append(t)

    # Affiliations
    affs = []
    meta_affs = [m.get('content').strip() for m in soup.find_all('meta', {'name': 'citation_author_institution'}) if m.get('content')]
    if meta_affs:
        affs.extend(meta_affs)
    else:
        for li in soup.select('.affiliations .item-list li, li[id^="full-view-affiliation"]'):
            t = _text_or_none(li)
            if t:
                affs.append(t)

    # Abstract: several selector variants
    abstract = None
    abstract_meta = _get_meta(soup, 'citation_abstract') or _get_meta(soup, 'description')
    if abstract_meta:
        abstract = abstract_meta
    else:
        for sel in ('#eng-abstract', 'div.abstract-content', 'div.abstract', '#abstract', 'section.abstract'):
            el = soup.select_one(sel)
            if el:
                abstract = _text_or_none(el)
                if abstract:
                    break

    # Identifiers: PMID, DOI (prefer meta tags)
    pmid = _get_meta(soup, 'citation_pmid') or None
    doi = _get_meta(soup, 'citation_doi') or _get_meta(soup, 'dc.identifier') or None
    if not pmid:
        txt = soup.get_text(separator=' ')
        m = re.search(r'PMID: ?(\d{3,})', txt)
        if m:
            pmid = m.group(1)

    # Journal / year / volume / issue / pages via meta when available
    journal = _get_meta(soup, 'citation_journal_title') or _get_meta(soup, 'citation_journal_abbrev')
    year = _get_meta(soup, 'citation_date')
    volume = _get_meta(soup, 'citation_volume')
    issue = _get_meta(soup, 'citation_issue')
    firstpage = _get_meta(soup, 'citation_firstpage')
    lastpage = _get_meta(soup, 'citation_lastpage')
    pages = None
    if firstpage and lastpage:
        pages = f"{firstpage}-{lastpage}"
    elif _get_meta(soup, 'citation_pages'):
        pages = _get_meta(soup, 'citation_pages')

    # if meta absent, try to parse visible citation line
    if not (journal and year):
        cit_span = soup.select_one('.article-citation .cit') or soup.select_one('.citation')
        if cit_span:
            cit = _text_or_none(cit_span) or ''
            m = re.search(r'(\d{4})', cit)
            if m and not year:
                year = m.group(1)
            m2 = re.search(r'(\d+)\((\d+)\):([\d\-]+)', cit)
            if m2 and not volume:
                volume, issue, pages = m2.group(1), m2.group(2), m2.group(3)
            if not journal:
                jm = re.match(r'^(.*?)\s+\d{4}', cit)
                if jm:
                    journal = jm.group(1).strip()

    # Keywords / MeSH
    mesh = []
    for m in soup.find_all('meta', {'name': 'citation_keywords'}):
        if m.get('content'):
            mesh.extend([k.strip() for k in m.get('content').split(';') if k.strip()])
    if not mesh:
        for li in soup.select('#mesh-terms .keywords-list .keyword-actions-trigger, #mesh-terms .keywords-list li, .mesh-terms li'):
            t = _text_or_none(li)
            if t:
                mesh.append(t)

    if authors == []:
        authors = None
    if affs == []:
        affs = None
    if mesh == []:
        mesh = None

    payload = {
        'zh': {
            '核心元数据': {
                '标题': {'value': title_text},
                '作者': {'value': authors},
                '机构': {'value': affs},
                '摘要': {'value': abstract},
                '期刊': {'value': journal},
                '年份': {'value': year},
                '卷': {'value': volume},
                '期': {'value': issue},
                '页码': {'value': pages},
                'DOI': {'value': doi},
                'PMID': {'value': pmid},
                'MeSH': {'value': mesh},
            }
        },
        'en': {
            '核心元数据': {
                'Title': {'value': title_text},
                'Authors': {'value': authors},
                'Affiliations': {'value': affs},
                'Abstract': {'value': abstract},
                'Journal': {'value': journal},
                'Year': {'value': year},
                'Volume': {'value': volume},
                'Issue': {'value': issue},
                'Pages': {'value': pages},
                'DOI': {'value': doi},
                'PMID': {'value': pmid},
                'MeSH': {'value': mesh},
            }
        }
    }

    return payload
