from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import json

from cstr_resolver import resolve_cstr
from doi_resolver import resolve_doi
from llm_api import qwen_chat, LABEL_TRANSLATIONS_EN
from field_filter import apply_requirement_filter
from get_id import get_typed_identifiers
from identifier import process_source_code


app = Flask(__name__)
CORS(app)


def normalize_llm_answer(raw_answer):
    if isinstance(raw_answer, dict):
        return raw_answer

    if isinstance(raw_answer, str):
        return json.loads(raw_answer)

    raise TypeError(f'Unsupported LLM answer type: {type(raw_answer)!r}')


def _first_present_value(answer, *keys):
    if not isinstance(answer, dict):
        return None

    for key in keys:
        if key in answer:
            return answer.get(key)
    return None


def _pick_fields(answer, canonical_alias_map):
    picked = {}
    for canonical_key, aliases in canonical_alias_map.items():
        value = _first_present_value(answer, canonical_key, *aliases)
        picked[canonical_key] = value if value is not None else None
    return picked


def _map_keys_recursive(obj, translations):
    """
    递归地将字典中的键名按照 translations 映射，
    保留原有非字典/非列表值结构。用于将 LLM 返回的中文键映射为英文键。
    """
    if isinstance(obj, dict):
        result = {}
        for k, v in obj.items():
            mapped_k = translations.get(k, k)
            result[mapped_k] = _map_keys_recursive(v, translations)
        return result
    if isinstance(obj, list):
        return [_map_keys_recursive(i, translations) for i in obj]
    return obj


def _is_missing_value(value):
    if value is None:
        return True
    if isinstance(value, str):
        normalized = value.strip().lower()
        return normalized in {'', 'not extracted', '未提取到', 'null'}
    if isinstance(value, list):
        return len(value) == 0
    if isinstance(value, dict):
        return len(value) == 0
    return False


def _merge_missing_values(primary, fallback):
    """
    用 fallback 填充 primary 中缺失的值。primary 优先，fallback 只补空缺。
    """
    if _is_missing_value(primary):
        return fallback

    if isinstance(primary, dict) and isinstance(fallback, dict):
        merged = dict(primary)
        for key, fallback_value in fallback.items():
            if key not in merged:
                merged[key] = fallback_value
                continue

            merged[key] = _merge_missing_values(merged[key], fallback_value)
        return merged

    if isinstance(primary, list) and isinstance(fallback, list):
        return primary if primary else fallback

    return primary


CORE_FIELD_ALIASES_ZH = {
    '标题': ['资源名称', 'Title', 'Resource Name'],
    'CSTR标识符': ['标识符', 'Identifier'],
    '创建者': ['作者', '作者姓名', 'Creators', 'Creators', 'Authors', 'Author Name', 'Data Paper Authors', 'Dataset Authors'],
    '发布机构': ['Publisher', '出版机构', '出版单位', 'publisher'],
    '发布日期': ['生成日期', '出版日期', 'Publication Date', 'publish_date', 'Received Date'],
    '描述': ['摘要', 'Description', 'Abstract', 'descriptions'],
    '关键词': ['Keywords', 'keywords'],
    '学科': ['学科分类', 'Discipline Classification', 'Subject Classification', 'subjects'],
    '语言': ['语种', 'Language', 'language'],
    '贡献者': ['Contributors', 'contributors'],
    '替代标识符': ['Alternative Identifiers', 'alternative_identifiers'],
    '关联标识符': ['Related Identifiers', 'related_identifiers'],
    '权限': ['资源使用许可', 'Usage License', 'rights'],
    '资助者': ['Funding Project', 'funders', '基金项目'],
    '版本': ['版本信息', 'Version Information', 'Version', 'version'],
    '资源链接': ['资源访问地址', '数据论文下载地址', 'Dataset Download URL', 'Data Paper Download URL', 'Resource Access URL', 'urls'],
    '资源类型': ['资源类型判定', 'Resource Type Classification', 'ResourceType'],
    '领域判定': ['Domain Classification'],
    '扩展信息': ['Extension Info'],
}


CORE_FIELD_ALIASES_EN = {
    'Title': ['titles', 'Resource Name', 'title'],
    'Identifier': ['identifier', 'CSTR Identifier', '标识符'],
    'Creators': ['creators', 'Authors', 'Author Name', 'Data Paper Authors', 'Dataset Authors', '创建者'],
    'Publisher': ['publisher', '出版机构', '出版单位', '发布机构'],
    'Publication Date': ['publish_date', 'Generated Date', 'Received Date', '出版日期', '发布日期'],
    'Description': ['descriptions', 'Abstract', '摘要', '描述'],
    'Keywords': ['keywords', '关键词'],
    'Subjects': ['subjects', 'Discipline Classification', 'Subject Classification', '学科'],
    'Language': ['language', '语种', '语言'],
    'Contributors': ['contributors', '贡献者'],
    'Alternative Identifiers': ['alternative_identifiers', '替代标识符'],
    'Related Identifiers': ['related_identifiers', '关联标识符'],
    'Rights': ['rights', 'Usage License', '资源使用许可'],
    'Funders': ['funders', 'Funding Project', '资助者'],
    'Version': ['version', 'Version Information', '版本'],
    'Resource URL': ['urls', 'Resource Access URL', 'Dataset Download URL', 'Data Paper Download URL', '资源链接'],
    'ResourceType': ['Resource Type Classification', 'ResourceType', '资源类型'],
    'Domain Classification': ['领域判定'],
    'Extension Info': ['扩展信息'],
}


def _infer_domain_section(resource_type_value, language='zh'):
    resource = str(resource_type_value or '').strip()
    if not resource:
        return '核心元数据' if language == 'zh' else 'Core Metadata'

    if language == 'en':
        return {
            'Dataset': 'Dataset Metadata',
            'Data Paper': 'Data Paper Metadata',
            'Standard Literature': 'Standard Literature Metadata',
            'Ecological Data': 'Ecological Science Data Metadata',
            'Other': 'Core Metadata',
            'Core Metadata': 'Core Metadata',
        }.get(resource, 'Core Metadata')

    return {
        '数据集': '数据集元数据',
        '数据论文': '数据论文元数据',
        '标准文献': '标准文献元数据',
        '生态科学数据': '生态科学数据元数据',
        '其他': '核心元数据',
        '核心元数据': '核心元数据',
    }.get(resource, '核心元数据')


def _resource_type_from_domain(domain_value, language='zh'):
    domain = str(domain_value or '').strip()
    if not domain:
        return '其他' if language == 'zh' else 'Other'

    if language == 'en':
        return {
            'Dataset Metadata': 'Dataset',
            'Data Paper Metadata': 'Data Paper',
            'Standard Literature Metadata': 'Standard Literature',
            'Ecological Science Data Metadata': 'Ecological Data',
            'Core Metadata': 'Other',
        }.get(domain, 'Other')

    return {
        '数据集元数据': '数据集',
        '数据论文元数据': '数据论文',
        '标准文献元数据': '标准文献',
        '生态科学数据元数据': '生态科学数据',
        '核心元数据': '其他',
    }.get(domain, '其他')


def build_metadata_payload(text, mode, url='', title='', html='', strategy='auto'):
    llm_answer = normalize_llm_answer(
        qwen_chat(text, mode, url=url, title=title, raw_html=html, strategy=strategy)
    )
    zh_answer = llm_answer.get('zh')
    en_answer = llm_answer.get('en')
    if not isinstance(zh_answer, dict) or not isinstance(en_answer, dict):
        raise ValueError('LLM response must contain zh and en objects')

    # 如果 LLM 在英文对象中使用了中文键名，则尝试把这些键名映射为英文
    en_answer = _map_keys_recursive(en_answer, LABEL_TRANSLATIONS_EN)
    # 使用中文结果作为英文结果的缺失值保底，避免英文侧大面积出现 Not extracted
    en_fallback = _map_keys_recursive(zh_answer, LABEL_TRANSLATIONS_EN)
    en_answer = _merge_missing_values(en_answer, en_fallback)

    # 提取并规范化核心元数据和领域元数据
    core_zh = _pick_fields(zh_answer, CORE_FIELD_ALIASES_ZH)
    core_en = _pick_fields(en_answer, CORE_FIELD_ALIASES_EN)

    domain_fields_zh = {
        '数据论文内容信息',
        '数据论文出版信息',
        '数据论文服务信息',
        '数据集基本信息',
        '数据集出版信息',
        '数据集服务信息',
        '标准文献信息',
        '标准文献内容信息',
        '标准文献出版信息',
        '标准文献服务信息',
        '生态科学数据基本信息',
        '生态科学数据出版信息',
        '生态科学数据服务信息',
    }
    domain_fields_en = {
        'Data Paper Content Information',
        'Data Paper Publication Information',
        'Data Paper Service Information',
        'Dataset Basic Information',
        'Dataset Publication Information',
        'Dataset Service Information',
        'Standard Literature Information',
        'Standard Literature Content Information',
        'Standard Literature Publication Information',
        'Standard Literature Service Information',
        'Ecological Science Data Basic Information',
        'Ecological Science Data Publication Information',
        'Ecological Science Data Service Information',
    }

    domain_zh = {k: v for k, v in zh_answer.items() if k in domain_fields_zh}
    domain_en = {k: v for k, v in en_answer.items() if k in domain_fields_en}

    # 将领域判定写回核心层，供前端切换领域表使用
    resource_type_zh = _first_present_value(zh_answer, '资源类型', '资源类型判定')
    resource_type_en = _first_present_value(en_answer, 'ResourceType', 'Resource Type Classification')
    domain_class_zh = _first_present_value(zh_answer, '领域判定')
    domain_class_en = _first_present_value(en_answer, 'Domain Classification')

    if not core_zh.get('资源类型'):
        core_zh['资源类型'] = resource_type_zh or _resource_type_from_domain(domain_class_zh, 'zh')
    if not core_zh.get('领域判定'):
        core_zh['领域判定'] = domain_class_zh or _infer_domain_section(core_zh.get('资源类型'), 'zh')
    if not core_zh.get('扩展信息'):
        core_zh['扩展信息'] = _first_present_value(zh_answer, '扩展信息')

    if not core_en.get('ResourceType'):
        core_en['ResourceType'] = resource_type_en or _resource_type_from_domain(domain_class_en, 'en')
    if not core_en.get('Domain Classification'):
        core_en['Domain Classification'] = domain_class_en or _infer_domain_section(core_en.get('ResourceType'), 'en')
    if not core_en.get('Extension Info'):
        core_en['Extension Info'] = _first_present_value(en_answer, 'Extension Info')

    domain_section_zh = _infer_domain_section(core_zh.get('资源类型'), 'zh')
    domain_section_en = _infer_domain_section(core_en.get('ResourceType'), 'en')

    result_zh = {'核心元数据': core_zh}
    if domain_zh:
        result_zh[domain_section_zh] = domain_zh

    result_en = {'Core Metadata': core_en}
    if domain_en:
        result_en[domain_section_en] = domain_en

    merged_answer = {'zh': result_zh, 'en': result_en}

    # 应用字段过滤：所有字段都是必选，空值按语言替换占位文本
    merged_answer['zh'] = apply_requirement_filter(merged_answer['zh'], empty_placeholder='未提取到')
    merged_answer['en'] = apply_requirement_filter(merged_answer['en'], empty_placeholder='Not extracted')

    return merged_answer


@app.route('/info', methods=['POST'])
def search():
    print("Received request")
    data = request.get_json() or {}
    source = data.get('source', 'text')
    mode = data.get('mode', 'common')
    strategy = data.get('strategy', 'auto')
    if source == 'identifier':
        items, error_payload = resolve_identifier_content(data)
        if error_payload:
            return jsonify({"status": "error", **error_payload}), 400

        results = []
        for item in items:
            if item.get('status') != 'ok':
                results.append(item)
                continue
            text = item.get('content', '')
            url = item.get('resolved_url', '')
            title = item.get('title', '')
            try:
                print("Asking LLM to process identifier content")
                print(
                    f"[Request Debug] strategy=llm, text_len={len(text or '')}, html_len=0, url={url}"
                )
                payload = build_metadata_payload(text, mode, url=url, title=title, html='', strategy='llm')
                results.append({
                    'identifier': item.get('identifier'),
                    'type': item.get('type'),
                    'resolved_url': url,
                    'source': item.get('source'),
                    'status': 'ok',
                    'payload': payload,
                    'updated_at': datetime.utcnow().isoformat() + 'Z',
                })
            except (json.JSONDecodeError, ValueError, TypeError) as error:
                print(f"LLM Error: {error}")
                results.append({
                    'identifier': item.get('identifier'),
                    'type': item.get('type'),
                    'resolved_url': url,
                    'source': item.get('source'),
                    'status': 'error',
                    'message': 'Invalid bilingual JSON format from LLM',
                    'updated_at': datetime.utcnow().isoformat() + 'Z',
                })

        return jsonify({'items': results})

    text = data.get('text', '')
    html = data.get('html', '')
    url = data.get('url', '')
    title = data.get('title', '')
    print("Asking LLM to process text")
    print(
        f"[Request Debug] strategy={strategy}, text_len={len(text or '')}, html_len={len(html or '')}, url={url}"
    )

    try:
        merged_answer = build_metadata_payload(text, mode, url=url, title=title, html=html, strategy=strategy)
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print(f"LLM Error: {error}")
        return jsonify({"status": "error", "message": "Invalid bilingual JSON format from LLM"}), 400

    print("LLM processing complete")
    print("Merged answer:", json.dumps(merged_answer, ensure_ascii=False, indent=2))
    return merged_answer


def collect_identifier_text(data):
    raw_identifiers = data.get('identifiers')
    if isinstance(raw_identifiers, list):
        chunks = [str(item) for item in raw_identifiers if item is not None]
        return '\n'.join(chunks)
    if raw_identifiers is not None:
        return str(raw_identifiers)
    return str(data.get('text') or data.get('html') or '')


def extract_doi_cstr_identifiers(text):
    return [
        item
        for item in get_typed_identifiers(text, include_patent=False)
        if item['type'] in ('doi', 'cstr')
    ]


def resolve_identifier_item(identifier_type, identifier):
    if identifier_type == 'doi':
        return resolve_doi(identifier, clean_html=process_source_code)
    if identifier_type == 'cstr':
        return resolve_cstr(identifier, clean_html=process_source_code)
    raise ValueError(f'Unsupported identifier type: {identifier_type}')


def resolve_identifier_content(data):
    identifier_text = collect_identifier_text(data)
    identifiers = extract_doi_cstr_identifiers(identifier_text)
    if not identifiers:
        return None, {'message': 'No DOI or CSTR identifier found'}

    items = []
    for item in identifiers:
        identifier_type = item['type']
        identifier = item['id']
        try:
            resolved = resolve_identifier_item(identifier_type, identifier)
            content = resolved.get('content')
            resolved_url = resolved.get('url')
            source = resolved.get('source', identifier_type)
            if not content:
                raise ValueError('Resolved page has no readable content')

            items.append({
                'identifier': identifier,
                'type': identifier_type,
                'resolved_url': resolved_url,
                'source': source,
                'content': content,
                'status': 'ok',
            })
        except Exception as error:
            print(f"[WARNING] Failed to resolve {identifier_type.upper()} {identifier}: {error}")
            items.append({
                'identifier': identifier,
                'type': identifier_type,
                'status': 'error',
                'message': str(error),
            })

    if all(item.get('status') != 'ok' for item in items):
        return None, {
            'message': 'Failed to resolve any DOI or CSTR identifier',
            'errors': [
                {
                    'identifier': item.get('identifier'),
                    'type': item.get('type'),
                    'message': item.get('message'),
                }
                for item in items
                if item.get('status') != 'ok'
            ],
        }

    return items, None


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=4000, threaded=True)
