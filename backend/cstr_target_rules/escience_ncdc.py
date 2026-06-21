import re
from html import unescape
from urllib.parse import quote

import requests


API_URL = 'https://api.escience.org.cn/metadata/metadata/search/detail'
DETAIL_URL = 'https://www.escience.org.cn/metadata/detail'
NCDC_ESCIENCE_ORG_ID = '9bc0652f0dce29823c0c9842001ae890'

FETCH_HEADERS = {
    'User-Agent': 'metadata-extractor/1.0 (+https://localhost)',
    'Accept': 'application/json,text/plain,*/*',
    'Referer': 'https://www.escience.org.cn/metadata/detail',
}

TEXT_FIELDS = [
    ('资源名称（中文）', 'title'),
    ('Resource Name (Foreign Language)', 'titleEn'),
    ('标识符', 'cstrId'),
    ('CSTR标识符', 'cstrId'),
    ('学科分类', 'subject'),
    ('主题分类', 'theme'),
    ('关键词', 'keywords'),
    ('描述', 'descr'),
    ('资源生成日期', 'generateDateStr'),
    ('最近发布日期', 'utime'),
    ('资源信息链接发布地址', 'link'),
    ('共享途径', 'sharePathway'),
    ('共享范围', 'shareScope'),
    ('申请流程', 'applicationProcess'),
    ('服务机构名称', 'serviceOrg'),
    ('服务机构通信地址', 'serviceOrgAddr'),
    ('服务机构邮政编码', 'serviceOrgPostCode'),
    ('服务机构联系电话', 'serviceOrgPhone'),
    ('服务机构电子信箱', 'serviceOrgEmail'),
    ('所属平台', 'orgName'),
]


def matches(cstr):
    return bool(re.match(r'^11738\.11\.ncdc\.', str(cstr or ''), flags=re.IGNORECASE))


def resolve(cstr, clean_html=None):
    detail_id = build_detail_id(cstr)
    metadata = _fetch_metadata(detail_id)
    content = _metadata_to_labeled_text(metadata)

    return {
        'content': content,
        'url': build_detail_url(cstr),
        'source': 'escience-ncdc',
    }


def build_detail_id(cstr):
    return f'{NCDC_ESCIENCE_ORG_ID}:CSTR:{cstr}'


def build_detail_url(cstr):
    cstr_id = f'CSTR:{cstr}'
    detail_id = build_detail_id(cstr)
    return (
        f'{DETAIL_URL}?id={quote(detail_id, safe="")}'
        f'&cstrId={quote(cstr_id, safe="")}'
    )


def _fetch_metadata(detail_id):
    response = requests.get(
        API_URL,
        params={'cstrId': detail_id},
        headers=FETCH_HEADERS,
        timeout=10,
    )
    response.raise_for_status()
    payload = response.json()

    if payload.get('code') != 200:
        raise ValueError(f'eScience metadata API failed: {payload.get("msg") or payload.get("code")}')

    data = payload.get('data')
    if not isinstance(data, dict) or not data:
        raise ValueError('eScience metadata API returned no metadata')

    return data


def _metadata_to_labeled_text(metadata):
    lines = ['中国科技资源共享网 资源详情']

    for label, key in TEXT_FIELDS:
        value = _normalize_value(metadata.get(key))
        if value:
            lines.append(f'{label}: {value}')

    extend_fields = metadata.get('extendFields')
    if isinstance(extend_fields, list):
        for item in extend_fields:
            if not isinstance(item, dict):
                continue
            key = _normalize_value(item.get('key'))
            value = _normalize_value(item.get('value'))
            if key and value:
                lines.append(f'{key}: {value}')

    return '\n'.join(lines)


def _normalize_value(value):
    if value is None:
        return None
    if isinstance(value, list):
        parts = [_normalize_value(item) for item in value]
        return '; '.join(item for item in parts if item)
    if isinstance(value, dict):
        return '; '.join(
            item
            for item in (_normalize_value(part) for part in value.values())
            if item
        )

    text = unescape(str(value))
    text = re.sub(r'<[^>]+>', ' ', text)
    text = text.replace('&emsp;', ' ')
    text = re.sub(r'\s+', ' ', text).strip()
    return text or None
