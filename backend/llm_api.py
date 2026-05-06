import json
from pathlib import Path

from openai import OpenAI

client = OpenAI(
    api_key="sk-48c71abcf3a34104ad4870cd2c382b7a",
    base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
)

BASE_DIR = Path(__file__).resolve().parent
STANDARD_PATH = BASE_DIR / 'standard.json'

DOMAIN_CANDIDATES_ZH = ['核心元数据', '数据集元数据', '数据论文元数据']
DOMAIN_CANDIDATES_EN = ['Core Metadata', 'Dataset Metadata', 'Data Paper Metadata']

LABEL_TRANSLATIONS_EN = {
    '资源类型候选列表': 'Resource Type Candidates',
    '类型名称': 'Type Name',
    '英文类型': 'English Type',
    '领域元数据': 'Domain Metadata',
    '核心元数据': 'Core Metadata',
    '数据集元数据': 'Dataset Metadata',
    '数据论文元数据': 'Data Paper Metadata',
    '数据集基本信息': 'Dataset Basic Information',
    '数据集出版信息': 'Dataset Publication Information',
    '数据集服务信息': 'Dataset Service Information',
    '数据论文内容信息': 'Data Paper Content Information',
    '数据论文出版信息': 'Data Paper Publication Information',
    '数据论文服务信息': 'Data Paper Service Information',
    '共享方式': 'Sharing Details',
    '提供方信息': 'Provider Information',
    '服务方信息': 'Service Provider Information',
    '范围': 'Scope',
    '数据集作者': 'Dataset Authors',
    '数据论文作者': 'Data Paper Authors',
    '标识符': 'Identifier',
    '资源名称': 'Resource Name',
    '描述': 'Description',
    '关键词': 'Keywords',
    '生成日期': 'Generation Date',
    '注册日期': 'Registration Date',
    '最新发布日期': 'Latest Release Date',
    '资源类型判定': 'Resource Type Classification',
    '领域判定': 'Domain Classification',
    '学科分类': 'Discipline Classification',
    '主题分类': 'Subject Classification',
    '知识产权类别': 'Intellectual Property Type',
    '资源使用许可': 'Usage License',
    '资源访问地址': 'Resource Access URL',
    '共享途径': 'Sharing Channel',
    '共享范围': 'Sharing Scope',
    '申请流程': 'Application Process',
    '提供方名称': 'Provider Name',
    '提供方详细地址': 'Provider Address',
    '提供方邮政编码': 'Provider Postal Code',
    '提供方联系人': 'Provider Contact',
    '提供方联系电话': 'Provider Phone',
    '提供方电子邮箱': 'Provider Email',
    '提供方网站': 'Provider Website',
    '服务方名称': 'Service Provider Name',
    '服务方详细地址': 'Service Provider Address',
    '服务方邮政编码': 'Service Provider Postal Code',
    '服务方联系人': 'Service Provider Contact',
    '服务方联系电话': 'Service Provider Phone',
    '服务方电子邮箱': 'Service Provider Email',
    '服务方网站': 'Service Provider Website',
    '标题': 'Title',
    '摘要': 'Abstract',
    '时间范围': 'Time Range',
    '空间范围': 'Spatial Range',
    '语种': 'Language',
    '文件内容': 'File Content',
    '基金项目': 'Funding Project',
    '数据量': 'Data Volume',
    '数据格式': 'Data Format',
    '作者姓名': 'Author Name',
    '工作单位': 'Affiliation',
    '电子邮箱': 'Email',
    '工作贡献': 'Contribution',
    '作者简介': 'Biography',
    '发布日期': 'Publication Date',
    '出版期刊': 'Journal',
    '版本信息': 'Version Information',
    '数据集引用格式': 'Dataset Citation',
    '数据集共享许可协议': 'Dataset License',
    '数据集使用声明': 'Dataset Usage Statement',
    '数据集下载地址': 'Dataset Download URL',
    '数据论文访问地址': 'Dataset Paper URL',
    '引言': 'Introduction',
    '数据采集和处理方法': 'Data Collection and Processing Methods',
    '数据样本描述': 'Data Sample Description',
    '数据质量控制和评估': 'Data Quality Control and Evaluation',
    '数据使用方法和建议': 'Data Use Methods and Recommendations',
    '参考文献': 'References',
    '致谢': 'Acknowledgements',
    '收稿日期': 'Received Date',
    '同评日期': 'Review Date',
    '录用日期': 'Accepted Date',
    '出版日期': 'Publication Date',
    '数据论文下载地址': 'Data Paper Download URL',
    '数据论文共享许可协议': 'Data Paper License',
    '数据集访问地址': 'Dataset Access URL',
}


def load_standard():
    with STANDARD_PATH.open('r', encoding='utf-8') as file:
        return json.load(file)


def translate_schema_for_language(schema, language='zh'):
    if language != 'en':
        return schema

    if isinstance(schema, dict):
        translated = {}
        for key, value in schema.items():
            translated[LABEL_TRANSLATIONS_EN.get(key, key)] = translate_schema_for_language(value, language)
        return translated

    return schema


def build_prompt(content, standard):
    return _build_prompt(content, standard, url='', title='', preclassified_type=None)


def classify_resource_type(content, url='', title=''):
    combined = ' '.join([str(title or ''), str(url or ''), str(content or '')]).lower()

    if 'arxiv.org/abs/' in combined or 'arxiv.org/pdf/' in combined or 'arxiv:' in combined:
        return '数据论文'

    dataset_signals = [
        'dataset',
        'data set',
        'download',
        'csv',
        'tsv',
        'parquet',
        'data repository',
        'zenodo',
        'figshare',
        'kaggle',
    ]
    paper_signals = [
        'paper',
        'article',
        'journal',
        'preprint',
        'abstract',
        'introduction',
        'references',
        'doi',
        'accepted',
        'published',
    ]
    data_paper_signals = [
        'data paper',
        'data descriptor',
        'data availability',
        'metadata paper',
    ]

    dataset_score = sum(1 for s in dataset_signals if s in combined)
    paper_score = sum(1 for s in paper_signals if s in combined)
    data_paper_score = sum(1 for s in data_paper_signals if s in combined)

    if data_paper_score >= 1:
        return '数据论文'
    if dataset_score >= 2 and paper_score == 0:
        return '数据集'
    if paper_score >= 2:
        return '数据论文'
    if dataset_score >= 2:
        return '数据集'
    return '其他'


def _build_prompt(content, standard, url='', title='', preclassified_type=None):
    type_candidates = standard.get('资源类型候选列表', [])
    standard_zh = json.dumps(standard, ensure_ascii=False, separators=(',', ':'))
    standard_en = json.dumps(translate_schema_for_language(standard, 'en'), ensure_ascii=False, separators=(',', ':'))
    type_candidates_zh = json.dumps(type_candidates, ensure_ascii=False, separators=(',', ':'))
    type_candidates_en = json.dumps(
        translate_schema_for_language({'资源类型候选列表': type_candidates}, 'en').get('Resource Type Candidates', []),
        ensure_ascii=False,
        separators=(',', ':'),
    )
    
    # 核心元数据字段列表（强制要求）
    core_fields_zh = "标识符、资源名称、描述、关键词、生成日期、注册日期、最新发布日期、学科分类、主题分类、知识产权类别、资源使用许可、资源访问地址、共享方式、提供方信息、服务方信息"
    
    core_fields_en = "Identifier, Resource Name, Description, Keywords, Generation Date, Registration Date, Latest Release Date, Discipline Classification, Subject Classification, Intellectual Property Type, Usage License, Resource Access URL, Sharing Details, Provider Information, Service Provider Information"
    
    # 使用字符串拼接避免 f-string 中的复杂格式问题
    rules = "\n".join([
        "请严格遵守以下规则:",
        "",
        "1) 返回严格 JSON，只包含 \"zh\" 和 \"en\" 两个顶层键，不要输出解释文本或多余字符。",
        "",
        "2) 【最重要】必须在顶层返回以下核心元数据字段（zh 和 en 都要有）:",
        "   中文必须包含：" + core_fields_zh,
        "   英文必须包含：" + core_fields_en,
        "   如果无法从网页中提取到某个字段的值，使用 null。",
        "",
        "3) 中文版本：所有键名和可翻译字段值必须是中文；英文版本：所有键名和可翻译字段值必须是英文。",
        "",
        "4) 不可翻译/保留原样的内容包括但不限于：网址、DOI、arXiv ID、邮箱、UUID、日期、数值、代码片段、专有编号。",
        "",
        "5) 对于描述、摘要、引言、方法、致谢等长文本字段，只输出一到两句的短摘要，不要照搬大段原文。",
        "",
        "6) 对于作者、机构、期刊、许可、分类等字段，优先输出简短规范名称，不要展开解释。",
        "",
        "7) 对于含多值的字段，可返回数组。",
        "",
        "8) 【重要】扩展信息字段：中文为\"扩展信息\"，英文为\"Extension Info\"。"
        "   请从网页中提取以上所有字段都没有覆盖到的、但你认为重要的额外信息，"
        "   例如：数据使用注意事项、相关项目信息、数据集特点、研究亮点、"
        "   数据缺失说明、引用建议、版本更新记录、相关链接等。"
        "   如果没有额外重要信息，返回空字符串。",   
        "9) 必须从\"资源类型候选列表\"中判断资源类型，并将结果写入顶层：",
        "   - 中文键：\"资源类型判定\"（值只能是：\"数据集\"/\"数据论文\"/\"其他\"）",
        "   - 英文键：\"Resource Type Classification\"（值只能是：\"Dataset\"/\"Data Paper\"/\"Other\"）",
        "",
        "10) 必须同时写入领域切换字段（也在顶层）：",
        "   - 中文键：\"领域判定\"（值严格对应：数据集→\"数据集元数据\" / 数据论文→\"数据论文元数据\" / 其他→\"核心元数据\"）",
        "   - 英文键：\"Domain Classification\"（值：\"Dataset Metadata\" / \"Data Paper Metadata\" / \"Core Metadata\"）",
        "",
        "11) 除了上述核心元数据字段外，还要根据领域判定值返回对应的完整领域 schema 结构：",
        "    - 领域判定 = \"数据论文元数据\" → 额外返回\"数据论文内容信息\"、\"数据论文出版信息\"、\"数据论文服务信息\"及其子字段",
        "    - 领域判定 = \"数据集元数据\" → 额外返回\"数据集基本信息\"、\"数据集出版信息\"、\"数据集服务信息\"及其子字段",
        "    - 领域判定 = \"核心元数据\" → 不需要额外返回领域结构",
        "",
        "12) 如果页面来自 arXiv（URL/title/text 中出现 arXiv 线索），优先判定为\"数据论文\"。",
        "",
        "13) 最终返回的 JSON 顶层结构应该是：",
        "    {",
        '        "zh": {',
        '            "资源类型判定": "...",',
        '            "领域判定": "...",',
        '            "标识符": ...,',
        '            "资源名称": ...,',
        '            "描述": ...,',
        '            "关键词": ...,',
        '            "生成日期": ...,',
        '            "注册日期": ...,',
        '            "最新发布日期": ...,',
        '            "学科分类": ...,',
        '            "主题分类": ...,',
        '            "知识产权类别": ...,',
        '            "资源使用许可": ...,',
        '            "资源访问地址": ...,',
        '            "共享方式": ...,',
        '            "提供方信息": ...,',
        '            "服务方信息": ...,',
        '            "数据论文内容信息": {...},',
        '            "数据论文出版信息": {...},',
        '            "数据论文服务信息": {...},',
        '            "扩展信息": "..."',
        "        },",
        '        "en": {...}',
        "    }"
    ])
    
    few_shot_examples = '''
示例（数据论文 - 必须包含核心元数据 + 领域元数据）：
网页文字: "Paper: Title: Climate Observations. DOI: 10.1234/abcd. Published on 2025-01-01."
期望输出:
{
    "zh": {
        "资源类型判定": "数据论文",
        "领域判定": "数据论文元数据",
        "标识符": "10.1234/abcd",
        "资源名称": "气候观测数据分析",
        "描述": "分析了气候观测数据的时间序列特征。",
        "关键词": ["气候", "观测", "时间序列"],
        "生成日期": "2025-01-01",
        "注册日期": null,
        "最新发布日期": null,
        "学科分类": "大气科学",
        "主题分类": "气候变化",
        "知识产权类别": null,
        "资源使用许可": null,
        "资源访问地址": "https://example.org/paper/123",
        "共享方式": null,
        "提供方信息": null,
        "服务方信息": null,
        "数据论文内容信息": {
            "标识符": "10.1234/abcd",
            "标题": "气候观测数据分析",
            "摘要": "短摘要：分析了气候观测数据的时间序列特征。",
            "关键词": ["气候", "观测", "时间序列"],
            "数据论文作者": {"作者姓名": "Smith"},
            "数据采集和处理方法": "采集自地面站，使用标准化质量控制和插值方法。"
        },
        "数据论文出版信息": {
            "收稿日期": "2025-01-01",
            "出版期刊": "Journal of Climate Data"
        },
        "数据论文服务信息": {
            "数据论文下载地址": "https://example.org/paper/123",
            "数据论文共享许可协议": "CC BY 4.0"
        },
        "扩展信息": ""
    },
    "en": {
        "Resource Type Classification": "Data Paper",
        "Domain Classification": "Data Paper Metadata",
        "Identifier": "10.1234/abcd",
        "Resource Name": "Climate Observations Analysis",
        "Description": "Short abstract: analyzes time-series features of climate observations.",
        "Keywords": ["climate", "observations", "time-series"],
        "Generation Date": "2025-01-01",
        "Registration Date": null,
        "Latest Release Date": null,
        "Discipline Classification": "Atmospheric Science",
        "Subject Classification": "Climate Change",
        "Intellectual Property Type": null,
        "Usage License": null,
        "Resource Access URL": "https://example.org/paper/123",
        "Sharing Details": null,
        "Provider Information": null,
        "Service Provider Information": null,
        "Data Paper Content Information": {
            "Identifier": "10.1234/abcd",
            "Title": "Climate Observations Analysis",
            "Abstract": "Short abstract: analyzes time-series features of climate observations.",
            "Keywords": ["climate", "observations", "time-series"],
            "Data Paper Authors": {"Author Name": "Smith"},
            "Data Collection and Processing Methods": "Collected from ground stations with QC and interpolation."
        },
        "Data Paper Publication Information": {
            "Received Date": "2025-01-01",
            "Journal": "Journal of Climate Data"
        },
        "Data Paper Service Information": {
            "Data Paper Download URL": "https://example.org/paper/123",
            "Data Paper License": "CC BY 4.0"
        },
        "Extension Info": ""
    }
}
'''

    prompt = f"""基于以下标准 JSON（中文/英文）以及网页文字，一次性输出中文与英文两个版本的元数据 JSON，严格按照规则返回，不要多余文本。

{rules}

资源类型候选列表（中文）:
{type_candidates_zh}

Resource type candidates (English):
{type_candidates_en}

示例参考：
{few_shot_examples}

中文标准 JSON（供参考字段名）:
{standard_zh}

英文标准 JSON（供参考字段名）:
{standard_en}

网页文字:
{content}

网页标题:
{title}

网页地址:
{url}

规则预判资源类型（可作为强参考）:
{preclassified_type or '未预判'}

请直接输出仅包含顶层键 `zh` 和 `en` 的 JSON 对象。"""

    return prompt


def _extract_json_from_text(text):
    try:
        start = text.index('{')
        end = text.rindex('}')
        candidate = text[start:end+1]
        return json.loads(candidate)
    except Exception:
        return None


def _set_core_classification(answer, resource_type, domain, language='zh'):
    if not isinstance(answer, dict):
        return

    resource_key = 'Resource Type Classification' if language == 'en' else '资源类型判定'
    domain_key = 'Domain Classification' if language == 'en' else '领域判定'

    if not answer.get(resource_key):
        answer[resource_key] = resource_type
    if not answer.get(domain_key):
        answer[domain_key] = domain


def _map_type_to_domain_and_en(resource_type_zh):
    mapping = {
        '数据集': ('Dataset', '数据集元数据', 'Dataset Metadata'),
        '数据论文': ('Data Paper', '数据论文元数据', 'Data Paper Metadata'),
        '其他': ('Other', '核心元数据', 'Core Metadata'),
    }
    return mapping.get(resource_type_zh, ('Other', '核心元数据', 'Core Metadata'))


def qwen_chat(content, mode='核心元数据', url='', title=''):
    standard = load_standard()
    pre_type_zh = classify_resource_type(content, url=url, title=title)
    prompt = _build_prompt(content, standard, url=url, title=title, preclassified_type=pre_type_zh)

    completion = client.chat.completions.create(
        model="qwen3-8b",
        messages=[
            {"role": "system", "content": "You are a strict JSON-output assistant. Only output the requested JSON."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.0,
        top_p=1.0,
        max_tokens=8192,
        response_format={"type": "json_object"},
        extra_body={"enable_thinking": False},
    )

    try:
        raw = json.loads(completion.model_dump_json())['choices'][0]['message']['content']
    except Exception:
        raw = str(completion)

    print("[LLM RAW REPLY START]")
    print(raw)
    print("[LLM RAW REPLY END]")

    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            zh = parsed.get('zh', {})
            en = parsed.get('en', {})
            type_en, domain_zh, domain_en = _map_type_to_domain_and_en(pre_type_zh)
            _set_core_classification(zh, pre_type_zh, domain_zh, 'zh')
            _set_core_classification(en, type_en, domain_en, 'en')
            parsed['zh'] = zh
            parsed['en'] = en
        return parsed
    except Exception:
        extracted = _extract_json_from_text(raw)
        if extracted is not None:
            if isinstance(extracted, dict):
                zh = extracted.get('zh', {})
                en = extracted.get('en', {})
                type_en, domain_zh, domain_en = _map_type_to_domain_and_en(pre_type_zh)
                _set_core_classification(zh, pre_type_zh, domain_zh, 'zh')
                _set_core_classification(en, type_en, domain_en, 'en')
                extracted['zh'] = zh
                extracted['en'] = en
            return extracted

    return {"error": "invalid_json", "raw": raw}