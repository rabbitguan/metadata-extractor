from flask import Flask, request, jsonify
from flask_cors import CORS
import json

from llm_api import qwen_chat
from field_filter import apply_requirement_filter


app = Flask(__name__)
CORS(app)


def normalize_llm_answer(raw_answer):
    if isinstance(raw_answer, dict):
        return raw_answer

    if isinstance(raw_answer, str):
        return json.loads(raw_answer)

    raise TypeError(f'Unsupported LLM answer type: {type(raw_answer)!r}')


@app.route('/info', methods=['POST'])
def search():
    print("Received request")
    data = request.get_json() or {}
    text = data.get('text') or data.get('html', '')
    url = data.get('url', '')
    title = data.get('title', '')
    mode = data.get('mode', 'common')
    print("Asking LLM to process text")

    try:
        llm_answer = normalize_llm_answer(qwen_chat(text, mode, url=url, title=title))
        zh_answer = llm_answer.get('zh')
        en_answer = llm_answer.get('en')
        if not isinstance(zh_answer, dict) or not isinstance(en_answer, dict):
            raise ValueError('LLM response must contain zh and en objects')
    except (json.JSONDecodeError, ValueError, TypeError) as error:
        print(f"LLM Error: {error}")
        return jsonify({"status": "error", "message": "Invalid bilingual JSON format from LLM"}), 400

    print("LLM processing complete")
    
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
    return jsonify(merged_answer), 200


if __name__ == '__main__':
    app.run(debug=True, host='127.0.0.1', port=4000, threaded=True)