from flask import Flask, request, jsonify
from flask_cors import CORS
import json

from cstr_resolver import resolve_cstr
from doi_resolver import resolve_doi
from llm_api import qwen_chat
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


def build_metadata_response(raw_answer):
    llm_answer = normalize_llm_answer(raw_answer)
    zh_answer = llm_answer.get('zh')
    en_answer = llm_answer.get('en')
    if not isinstance(zh_answer, dict) or not isinstance(en_answer, dict):
        raise ValueError('LLM response must contain zh and en objects')

    # 获取领域判定
    schema_name_zh = zh_answer.get('领域判定', '核心元数据')
    schema_name_en_map = {
        '核心元数据': 'Core Metadata',
        '数据集元数据': 'Dataset Metadata',
        '数据论文元数据': 'Data Paper Metadata',
        '标准文献元数据': 'Standard Literature Metadata',
        '生态科学数据元数据': 'Ecological Science Data Metadata'
    }
    schema_name_en = schema_name_en_map.get(schema_name_zh, 'Core Metadata')
    
    # 提取核心元数据字段（排除类型判定和领域判定）
    core_exclude_keys = ['资源类型判定', '领域判定', '数据论文内容信息', '数据论文出版信息', '数据论文服务信息', 
                         '数据集基本信息', '数据集出版信息', '数据集服务信息', '扩展信息']
    
    core_zh = {k: v for k, v in zh_answer.items() if k not in core_exclude_keys}
    core_zh['资源类型判定'] = zh_answer.get('资源类型判定')
    core_zh['领域判定'] = zh_answer.get('领域判定')
    
    core_en = {k: v for k, v in en_answer.items() if k not in [x.replace('资源类型判定', 'Resource Type Classification').replace('领域判定', 'Domain Classification').replace('扩展信息', 'Extension Info') 
                                                                for x in core_exclude_keys]}
    core_en['Resource Type Classification'] = en_answer.get('Resource Type Classification')
    core_en['Domain Classification'] = en_answer.get('Domain Classification')
    
    # 提取领域元数据
    domain_keys = ['数据论文内容信息', '数据论文出版信息', '数据论文服务信息', 
                   '数据集基本信息', '数据集出版信息', '数据集服务信息']
    domain_zh = {k: v for k, v in zh_answer.items() if k in domain_keys}
    domain_en = {k: v for k, v in en_answer.items() if k in [x.replace('数据论文内容信息', 'Data Paper Content Information')
                                                              .replace('数据论文出版信息', 'Data Paper Publication Information')
                                                              .replace('数据论文服务信息', 'Data Paper Service Information')
                                                              .replace('数据集基本信息', 'Dataset Basic Information')
                                                              .replace('数据集出版信息', 'Dataset Publication Information')
                                                              .replace('数据集服务信息', 'Dataset Service Information') 
                                                              for x in domain_keys]}
    
    # 提取扩展信息
    extension_zh = zh_answer.get('扩展信息', '')
    extension_en = en_answer.get('Extension Info', '')
    if extension_zh:
        core_zh['扩展信息'] = extension_zh
    if extension_en:
        core_en['Extension Info'] = extension_en
    
    # 构建返回结构：核心元数据层 + 领域元数据层
    result_zh = {
        '核心元数据': core_zh,
    }
    if domain_zh:
        result_zh[schema_name_zh] = domain_zh
    
    result_en = {
        'Core Metadata': core_en,
    }
    if domain_en:
        result_en[schema_name_en] = domain_en
    
    merged_answer = {
        'zh': result_zh,
        'en': result_en,
    }

    # 应用字段过滤：所有字段都是必选，空值替换为"未提取到"
    merged_answer['zh'] = apply_requirement_filter(merged_answer['zh'])
    merged_answer['en'] = apply_requirement_filter(merged_answer['en'])

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

    content_sections = []
    resolved_urls = []
    errors = []

    for item in identifiers:
        identifier_type = item['type']
        identifier = item['id']
        try:
            resolved = resolve_identifier_item(identifier_type, identifier)
            content = resolved['content']
            resolved_url = resolved['url']
            source = resolved.get('source', identifier_type)
            if not content:
                raise ValueError('Resolved page has no readable content')

            resolved_urls.append(resolved_url)
            content_sections.append(
                '\n'.join([
                    f'Identifier Type: {identifier_type.upper()}',
                    f'Identifier: {identifier}',
                    f'Resolved URL: {resolved_url}',
                    f'Resolver Source: {source}',
                    'Resolved Page Content:',
                    content,
                ])
            )
        except Exception as error:
            errors.append({'identifier': identifier, 'type': identifier_type, 'message': str(error)})
            print(f"[WARNING] Failed to resolve {identifier_type.upper()} {identifier}: {error}")

    if not content_sections:
        return None, {
            'message': 'Failed to resolve any DOI or CSTR identifier',
            'errors': errors,
        }

    identifier_list = ', '.join(item['id'] for item in identifiers)
    return {
        'text': '\n\n--- DOI/CSTR RESOLVED RESOURCE ---\n\n'.join(content_sections),
        'title': data.get('title') or f'DOI/CSTR identifiers: {identifier_list}',
        'url': '\n'.join(resolved_urls),
        'errors': errors,
    }, None


@app.route('/info', methods=['POST'])
def search():
    print("Received request")
    data = request.get_json() or {}
    source = data.get('source', 'text')
    mode = data.get('mode', 'common')

    if source == 'identifier':
        resolved_payload, error_payload = resolve_identifier_content(data)
        if error_payload:
            return jsonify({"status": "error", **error_payload}), 400
        text = resolved_payload['text']
        url = resolved_payload['url']
        title = resolved_payload['title']
    else:
        text = data.get('text') or data.get('html', '')
        url = data.get('url', '')
        title = data.get('title', '')

    print("Asking LLM to process text")

    try:
        merged_answer = build_metadata_response(qwen_chat(text, mode, url=url, title=title))
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print(f"LLM Error: {error}")
        return jsonify({"status": "error", "message": "Invalid bilingual JSON format from LLM"}), 400

    print("LLM processing complete")
    return jsonify(merged_answer), 200


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=4000, threaded=True)
