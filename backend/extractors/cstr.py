from __future__ import annotations

import json
import re
from html import unescape
from typing import Any, Dict, Iterable, Optional


RULE_NAME = 'CSTR'


def _clean_text(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    text = unescape(str(value))
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None


def _has_cjk(value: Optional[str]) -> bool:
    return bool(re.search(r'[\u4e00-\u9fff]', str(value or '')))


def _english_text(value: Optional[str]) -> Optional[str]:
    cleaned = _clean_text(value)
    if not cleaned or _has_cjk(cleaned):
        return None
    return cleaned


def _english_list(values: Optional[list]) -> Optional[list]:
    result = [_english_text(value) for value in _ensure_list(values)]
    return [item for item in result if item] or None


def _ensure_list(value: Any) -> list:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    return [value]


def _unique_list(values: Iterable[Any]) -> list:
    seen = set()
    result = []
    for item in values:
        if item is None:
            continue
        if isinstance(item, str):
            key = item.strip()
            if not key:
                continue
        else:
            key = json.dumps(item, ensure_ascii=False, sort_keys=True)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _first_non_empty(*values: Optional[str]) -> Optional[str]:
    for value in values:
        cleaned = _clean_text(value)
        if cleaned:
            return cleaned
    return None


def _format_issue_date(issue: Any) -> Optional[str]:
    if not isinstance(issue, dict):
        return None
    year = str(issue.get('year') or '').strip()
    if not year:
        return None
    month = str(issue.get('month') or '').strip()
    day = str(issue.get('day') or '').strip()
    if month:
        month = month.zfill(2)
    if day:
        day = day.zfill(2)
    if month and day:
        return f'{year}-{month}-{day}'
    if month:
        return f'{year}-{month}'
    return year


def _load_json_payload(content: str) -> Optional[Any]:
    if not content:
        return None
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        decoder = json.JSONDecoder()
        for match in re.finditer(r'[\{\[]', content):
            start = match.start()
            try:
                payload, _ = decoder.raw_decode(content[start:])
                return payload
            except json.JSONDecodeError:
                continue
    return None


def _extract_content(payload: Any) -> Optional[Dict[str, Any]]:
    if isinstance(payload, list) and payload:
        payload = payload[0]
    if not isinstance(payload, dict):
        return None

    data = payload.get('data')
    if isinstance(data, dict):
        nested = data.get('data')
        if isinstance(nested, dict) and isinstance(nested.get('content'), dict):
            return nested.get('content')
        if isinstance(data.get('content'), dict):
            return data.get('content')
    if isinstance(payload.get('content'), dict):
        return payload.get('content')
    return payload


def matches(url: str, title: str, content: str) -> bool:
    normalized_url = (url or '').lower()
    combined = ' '.join([str(title or ''), str(url or ''), str(content or '')]).lower()
    if 'scids.bdware.cn' in normalized_url or 'scids.bdware.cn' in combined:
        return True
    return '"type"' in combined and 'cstr' in combined and '"resourceType"' in combined and '"identificationStatus"' in combined


def extract(content: str, url: str = '', title: str = '') -> Optional[Dict[str, Any]]:
    payload = _load_json_payload(content or '')
    content_data = _extract_content(payload) if payload is not None else None
    if not isinstance(content_data, dict):
        return None

    identifier = _clean_text(content_data.get('identifier'))
    urls = _unique_list([_clean_text(u) for u in _ensure_list(content_data.get('urls'))])
    single_url = _clean_text(content_data.get('url'))
    if single_url and single_url not in urls:
        urls.append(single_url)

    resource_type_code = _clean_text(str(content_data.get('resourceType') or '')) or None
    resource_type_map = {
        '11': ('数据集', 'Dataset', '数据集元数据', 'Dataset Metadata'),
        '14': ('数据论文', 'Data Paper', '数据论文元数据', 'Data Paper Metadata'),
    }
    resource_type_zh, resource_type_en, domain_zh, domain_en = resource_type_map.get(
        resource_type_code or '',
        ('其他', 'Other', '核心元数据', 'Core Metadata'),
    )

    title_zh = _first_non_empty(content_data.get('titleCN'), content_data.get('resourceChineseName'), title)
    title_en = _first_non_empty(content_data.get('titleEN'), content_data.get('resourceName'), title)
    if not title_zh:
        title_zh = title_en or identifier or url
    title_en = _english_text(title_en) or identifier or url

    abstract_zh = _first_non_empty(content_data.get('abstractCN'), content_data.get('descriptionCN'))
    abstract_en = _first_non_empty(content_data.get('abstractEN'), content_data.get('descriptionEN'))
    if not abstract_zh:
        abstract_zh = abstract_en
    abstract_en = _english_text(abstract_en)

    authors = content_data.get('authors') or []
    author_names = _unique_list(
        _clean_text(author.get('name')) for author in _ensure_list(authors) if isinstance(author, dict)
    )
    author_orgs = _unique_list(
        org
        for author in _ensure_list(authors)
        if isinstance(author, dict)
        for org in _ensure_list(author.get('organizations'))
        if _clean_text(org)
    )

    creators = content_data.get('creators') or []
    creator_names = _unique_list(
        _first_non_empty(creator.get('creatorNameCN'), creator.get('creatorNameEN'), creator.get('creatorName'))
        for creator in _ensure_list(creators)
        if isinstance(creator, dict)
    )
    creator_orgs = _unique_list(
        _first_non_empty(creator.get('creatorOrganizationCN'), creator.get('creatorOrganizationEN'))
        for creator in _ensure_list(creators)
        if isinstance(creator, dict)
    )

    creators_list = _unique_list([*author_names, *creator_names]) or None

    publisher_zh = _first_non_empty(content_data.get('journelCN'), content_data.get('registerOrganizationCN'))
    publisher_en = _first_non_empty(content_data.get('journelEN'), content_data.get('registerOrganizationEN'))
    if not publisher_zh:
        publisher_zh = publisher_en
    publisher_en = _english_text(publisher_en)

    issue_info = content_data.get('issue')
    publish_date = _first_non_empty(_format_issue_date(issue_info), content_data.get('publicationDate'))

    keywords_zh = _unique_list(
        _clean_text(keyword)
        for keyword in _ensure_list(content_data.get('keywordsCN') or content_data.get('keyWordsCN'))
        if _clean_text(keyword)
    )
    keywords_en = _unique_list(
        _clean_text(keyword)
        for keyword in _ensure_list(content_data.get('keywordsEN'))
        if _clean_text(keyword)
    )
    if not keywords_zh and keywords_en:
        keywords_zh = keywords_en
    keywords_en = _english_list(keywords_en)
    if not keywords_en:
        keywords_en = keywords_zh

    subject_classifications = content_data.get('subjectClassifications') or []
    subjects = _unique_list(
        _clean_text(name)
        for subject in _ensure_list(subject_classifications)
        if isinstance(subject, dict)
        for name in _ensure_list(subject.get('subjectName'))
        if _clean_text(name)
    ) or None
    subjects_en = _english_list(subjects)

    alternative_identifiers = _unique_list(
        _clean_text(item.get('identifierValue'))
        for item in _ensure_list(content_data.get('alternativeIdentifiers'))
        if isinstance(item, dict)
    )
    doi = _clean_text(content_data.get('doi'))
    if doi and doi not in alternative_identifiers:
        alternative_identifiers.append(doi)
    alternative_identifiers = alternative_identifiers or None

    rights = _unique_list(
        _clean_text(item.get('copyrightDescription'))
        for item in _ensure_list(content_data.get('copyrights'))
        if isinstance(item, dict)
    )
    rights = rights or None

    primary_right = rights[0] if rights else None

    resource_url = urls[0] if urls else None

    metadata: Dict[str, Any] = {
        'zh': {
            '标题': [title_zh] if title_zh else None,
            'CSTR标识符': identifier,
            '创建者': creators_list,
            '发布机构': publisher_zh,
            '发布日期': publish_date,
            '描述': [abstract_zh] if abstract_zh else None,
            '关键词': keywords_zh or None,
            '学科': subjects,
            '语言': None,
            '贡献者': None,
            '替代标识符': alternative_identifiers,
            '关联标识符': None,
            '权限': rights,
            '资助者': None,
            '版本': None,
            '资源链接': urls or None,
            '资源类型': resource_type_zh,
        },
        'en': {
            'Resource Type Classification': resource_type_en,
            'Domain Classification': domain_en,
            'Identifier': identifier,
            'titles': [{'lang': 'en', 'name': title_en}] if title_en else None,
            'creators': _english_list(creators_list),
            'publisher': {'names': [{'lang': 'en', 'name': publisher_en}], 'identifiers': None} if publisher_en else None,
            'publish_date': publish_date,
            'descriptions': [{'lang': 'en', 'description': abstract_en}] if abstract_en else None,
            'keywords': [{'lang': 'en', 'keyword': keywords_en}] if keywords_en else None,
            'subjects': [{'standard_gbt': None, 'standard_oecd': subjects_en}] if subjects_en else None,
            'language': None,
            'contributors': None,
            'alternative_identifiers': alternative_identifiers,
            'related_identifiers': None,
            'rights': rights,
            'funders': None,
            'version': None,
            'urls': urls or None,
            'resource_type': resource_type_en,
            'Title': title_en,
            'Description': abstract_en,
            'Keywords': keywords_en or None,
            'Discipline Classification': None,
            'Subject Classification': subjects_en,
            'Language': None,
            'Creators': _english_list(creators_list),
            'Publisher': publisher_en,
            'Publication Date': publish_date,
            'Contributors': None,
            'Alternative Identifiers': alternative_identifiers,
            'Related Identifiers': None,
            'Rights': rights,
            'Funders': None,
            'Version': None,
            'Resource URL': resource_url,
            'ResourceType': resource_type_en,
        },
    }

    if resource_type_code == '11':
        dataset_author_names = creator_names or author_names or None
        dataset_author_orgs = creator_orgs or author_orgs or None
        metadata['zh'].update({
            '数据集基本信息': {
                '标识符': identifier,
                '标题': title_zh,
                '摘要': abstract_zh,
                '关键词': keywords_zh or None,
                '范围': {
                    '时间范围': None,
                    '空间范围': None,
                },
                '语种': None,
                '文件内容': None,
                '基金项目': None,
                '数据量': None,
                '数据格式': None,
                '数据集作者': {
                    '作者姓名': dataset_author_names,
                    '工作单位': dataset_author_orgs,
                    '电子邮箱': None,
                    '工作贡献': None,
                    '作者简介': None,
                },
            },
            '数据集出版信息': {
                '发布日期': publish_date,
                '出版期刊': publisher_zh,
                '版本信息': None,
            },
            '数据集服务信息': {
                '数据集引用格式': None,
                '数据集共享许可协议': primary_right,
                '数据集使用声明': None,
                '数据集下载地址': resource_url,
                '数据论文访问地址': None,
            },
        })
        metadata['en'].update({
            'Dataset Basic Information': {
                'Identifier': identifier,
                'Title': title_en,
                'Abstract': abstract_en,
                'Keywords': keywords_en or None,
                'Coverage': {
                    'Temporal Coverage': None,
                    'Spatial Coverage': None,
                },
                'Language': None,
                'File Content': None,
                'Funding Projects': None,
                'Data Volume': None,
                'Data Format': None,
                'Dataset Authors': {
                    'Author Name': dataset_author_names,
                    'Affiliation': dataset_author_orgs,
                    'Email': None,
                    'Contribution': None,
                    'Biography': None,
                },
            },
            'Dataset Publication Information': {
                'Publication Date': publish_date,
                'Journal': publisher_en,
                'Version Information': None,
            },
            'Dataset Service Information': {
                'Dataset Citation Format': None,
                'Dataset License': primary_right,
                'Dataset Usage Statement': None,
                'Dataset Download URL': resource_url,
                'Data Paper Access URL': None,
            },
        })

    if resource_type_code == '14':
        data_paper_author_names = author_names or creator_names or None
        data_paper_author_orgs = author_orgs or creator_orgs or None
        metadata['zh'].update({
            '数据论文内容信息': {
                '标识符': identifier,
                '标题': title_zh,
                '摘要': abstract_zh,
                '关键词': keywords_zh or None,
                '数据集基本信息': None,
                '引言': None,
                '数据采集和处理方法': None,
                '数据样本描述': None,
                '数据质量控制和评估': None,
                '数据使用方法和建议': None,
                '参考文献': None,
                '致谢': None,
                '数据论文作者': {
                    '作者姓名': data_paper_author_names,
                    '工作单位': data_paper_author_orgs,
                    '电子邮箱': None,
                    '工作贡献': None,
                    '作者简介': None,
                },
            },
            '数据论文出版信息': {
                '收稿日期': None,
                '同评日期': None,
                '录用日期': None,
                '出版日期': publish_date,
                '版本信息': None,
                '出版期刊': publisher_zh,
            },
            '数据论文服务信息': {
                '数据论文引用格式': None,
                '数据论文下载地址': resource_url,
                '数据论文共享许可协议': primary_right,
                '数据集访问地址': None,
            },
        })
        metadata['en'].update({
            'Data Paper Content Information': {
                'Identifier': identifier,
                'Title': title_en,
                'Abstract': abstract_en,
                'Keywords': keywords_en or None,
                'Dataset Basic Information': None,
                'Introduction': None,
                'Data Collection and Processing Methods': None,
                'Data Sample Description': None,
                'Data Quality Control and Evaluation': None,
                'Data Use Methods and Recommendations': None,
                'References': None,
                'Acknowledgements': None,
                'Data Paper Authors': {
                    'Author Name': data_paper_author_names,
                    'Affiliation': data_paper_author_orgs,
                    'Email': None,
                    'Contribution': None,
                    'Biography': None,
                },
            },
            'Data Paper Publication Information': {
                'Received Date': None,
                'Review Date': None,
                'Accepted Date': None,
                'Publication Date': publish_date,
                'Version Information': None,
                'Journal': publisher_en,
            },
            'Data Paper Service Information': {
                'Data Paper Citation Format': None,
                'Data Paper Download URL': resource_url,
                'Data Paper License': primary_right,
                'Dataset Access URL': None,
            },
        })

    return metadata
