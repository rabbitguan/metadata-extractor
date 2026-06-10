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


def _value(value):
    return {'value': value}


def _first_available(*values):
    for value in values:
        if value:
            return value
    return None


def _canonical_url(soup: BeautifulSoup, fallback: str = '') -> Optional[str]:
    link = soup.find('link', {'rel': 'canonical'})
    if link and link.get('href'):
        return link.get('href').strip() or None
    return _first_available(
        _get_meta(soup, 'citation_abstract_html_url'),
        _get_meta(soup, 'og:url'),
        fallback or None,
    )


def _citation_text(*, authors, title_text, journal, year, volume, issue, pages, doi, pmid):
    chunks = []
    if authors:
        chunks.append(', '.join(authors) if isinstance(authors, list) else str(authors))
    if title_text:
        chunks.append(str(title_text))
    journal_parts = []
    if journal:
        journal_parts.append(str(journal))
    if year:
        journal_parts.append(str(year))
    if volume:
        volume_text = str(volume)
        if issue:
            volume_text = f"{volume_text}({issue})"
        journal_parts.append(volume_text)
    if pages:
        journal_parts.append(str(pages))
    if journal_parts:
        chunks.append('. '.join(journal_parts))
    if doi:
        chunks.append(f"doi: {doi}")
    if pmid:
        chunks.append(f"PMID: {pmid}")
    return '. '.join(chunks) if chunks else None


def _extension_info(*, journal, volume, issue, pages, doi, pmid, affiliations):
    parts = []
    for label, value in (
        ('Journal', journal),
        ('Volume', volume),
        ('Issue', issue),
        ('Pages', pages),
        ('DOI', doi),
        ('PMID', pmid),
    ):
        if value:
            parts.append(f"{label}: {value}")
    if affiliations:
        aff_text = '; '.join(affiliations) if isinstance(affiliations, list) else str(affiliations)
        parts.append(f"Affiliations: {aff_text}")
    return '; '.join(parts) if parts else None


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

    alternative_identifiers = []
    if doi:
        alternative_identifiers.append(doi)
    if pmid:
        alternative_identifiers.append(f"PMID:{pmid}")

    resource_url = _canonical_url(soup, url)
    citation = _citation_text(
        authors=authors,
        title_text=title_text,
        journal=journal,
        year=year,
        volume=volume,
        issue=issue,
        pages=pages,
        doi=doi,
        pmid=pmid,
    )
    extension_info = _extension_info(
        journal=journal,
        volume=volume,
        issue=issue,
        pages=pages,
        doi=doi,
        pmid=pmid,
        affiliations=affs,
    )

    payload = {
        'zh': {
            '标题': _value(title_text),
            '创建者': _value(authors),
            '发布机构': _value(journal),
            '发布日期': _value(year),
            '描述': _value(abstract),
            '关键词': _value(mesh),
            '语言': _value('en'),
            '替代标识符': _value(alternative_identifiers or None),
            '资源链接': _value(resource_url),
            '资源类型判定': '数据论文',
            '领域判定': '数据论文元数据',
            '扩展信息': _value(extension_info),
            '数据论文内容信息': {
                '标识符': _value(doi or (f"PMID:{pmid}" if pmid else None)),
                '标题': _value(title_text),
                '摘要': _value(abstract),
                '关键词': _value(mesh),
                '数据论文作者': {
                    '作者姓名': _value(authors),
                    '工作单位': _value(affs),
                },
            },
            '数据论文出版信息': {
                '出版日期': _value(year),
                '版本信息': _value(None),
                '出版期刊': _value(journal),
                '卷': _value(volume),
                '期': _value(issue),
                '页码': _value(pages),
                'PMID': _value(pmid),
                'DOI': _value(doi),
            },
            '数据论文服务信息': {
                '数据论文引用格式': _value(citation),
                '数据论文下载地址': _value(resource_url),
                '数据论文共享许可协议': _value(None),
            },
        },
        'en': {
            'Title': _value(title_text),
            'Creators': _value(authors),
            'Publisher': _value(journal),
            'Publication Date': _value(year),
            'Description': _value(abstract),
            'Keywords': _value(mesh),
            'Language': _value('en'),
            'Alternative Identifiers': _value(alternative_identifiers or None),
            'Resource URL': _value(resource_url),
            'Resource Type Classification': 'Data Paper',
            'Domain Classification': 'Data Paper Metadata',
            'Extension Info': _value(extension_info),
            'Data Paper Content Information': {
                'Identifier': _value(doi or (f"PMID:{pmid}" if pmid else None)),
                'Title': _value(title_text),
                'Abstract': _value(abstract),
                'Keywords': _value(mesh),
                'Data Paper Authors': {
                    'Author Name': _value(authors),
                    'Affiliation': _value(affs),
                },
            },
            'Data Paper Publication Information': {
                'Publication Date': _value(year),
                'Version Information': _value(None),
                'Journal': _value(journal),
                'Volume': _value(volume),
                'Issue': _value(issue),
                'Pages': _value(pages),
                'PMID': _value(pmid),
                'DOI': _value(doi),
            },
            'Data Paper Service Information': {
                'Data Paper Citation Format': _value(citation),
                'Data Paper Download URL': _value(resource_url),
                'Data Paper Sharing License': _value(None),
            },
        },
    }

    return payload
