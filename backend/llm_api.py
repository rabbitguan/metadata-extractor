import json
import re
import unicodedata
from pathlib import Path

from openai import OpenAI
from extractors.manager import extract_metadata, list_extractors

client = OpenAI(
    api_key="sk-gyvpgktxzelhglvjcekzypyfyssbjgpivrtvbeviufzfjaxz",
    base_url="https://api.siliconflow.cn/v1",
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
    '标题': 'titles',
    'CSTR标识符': 'identifier',
    '创建者': 'creators',
    '发布机构': 'publisher',
    '发布日期': 'publish_date',
    '描述': 'descriptions',
    '关键词': 'keywords',
    '学科': 'subjects',
    '语言': 'language',
    '贡献者': 'contributors',
    '替代标识符': 'alternative_identifiers',
    '关联标识符': 'related_identifiers',
    '权限': 'rights',
    '资助者': 'funders',
    '版本': 'version',
    '资源链接': 'urls',
    '资源类型': 'ResourceType',
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
    core_fields = "titles, identifier, creators, publisher, publish_date, descriptions, keywords, subjects, language, contributors, alternative_identifiers, related_identifiers, rights, funders, version, urls, resource_type"
    
    # 使用字符串拼接避免 f-string 中的复杂格式问题
    rules = "\n".join([
        "请严格遵守以下规则:",
        "",
        "1) 返回严格 JSON，只包含 \"zh\" 和 \"en\" 两个顶层键，不要输出解释文本或多余字符。",
        "",
        "【幻觉防控 - 严格遵守】:",
        "• 你的任务是从网页中提取信息，NOT 推理、补充或编造。",
        "• 禁止任何形式的信息补完或推理。例如：",
        "  ✗ 错误：网页说\"来自山东\"，你推断出\"山东大学\"",
        "  ✗ 错误：根据网址里的id编造标识符如\"DS-2024-001\"（原文不存在）",
        "  ✗ 错误：自动补齐日期，如网页说\"2024年\"，你改为\"2024-01-01\"",
        "  ✗ 错误：根据内容推测许可证，如\"免费开放数据\"→\"CC BY 4.0\"",
        "• 对每个提取的值，你必须能在原网页文字中找到明确证据。",
        "• 完全不存在的字段必须返回 null，不要编造。",
        "• 当不确定时，选择 null 而不是猜测。",
        "",
        "2) 【最重要】核心元数据字段键名必须使用《科技资源标识核心元数据规范》中的接口参数名，不要使用中文名称或展示英文名作为 JSON key:",
        "   必须包含：" + core_fields,
        "   例如发布机构字段必须写成 publisher，发布日期字段必须写成 publish_date。",
        "   如果网页中完全没有提及这个字段，或者证据不足，使用 null。不要编造。",
        "   核心元数据的值结构必须参考规范第 6 节元数据示例：",
        "   - titles: [{\"lang\":\"zh/en\",\"name\":\"...\"}]",
        "   - creators/contributors: [{\"type\":\"Person\",\"person\":{\"names\":[{\"lang\":\"zh/en\",\"name\":\"...\"}],\"emails\":...,\"identifiers\":...,\"affiliations\":...}}] 或 {\"type\":\"Organize\",\"affiliation\":{...}}",
        "   - publisher: {\"names\":[{\"lang\":\"zh/en\",\"name\":\"...\"}],\"identifiers\":[{\"type\":\"ROR/CSTR/Other\",\"identifier\":\"...\"}]}",
        "   - descriptions: [{\"lang\":\"zh/en\",\"description\":\"...\"}]",
        "   - keywords: [{\"lang\":\"zh/en\",\"keyword\":[\"...\"]}]",
        "   - subjects: [{\"standard_gbt\":[\"...\"],\"standard_oecd\":[\"...\"]}]",
        "   - alternative_identifiers: [{\"type\":\"DOI/CSTR/URL/Other\",\"identifier\":\"...\"}]",
        "   - related_identifiers: [{\"relation\":\"...\",\"type\":\"DOI/CSTR/URL/Other\",\"identifier\":{\"type\":\"...\",\"identifier\":\"...\"}}]",
        "   - rights: [{\"license_type\":...,\"license\":...,\"type\":...,\"description\":...,\"cert_num\":...}]",
        "   - funders: [{\"name\":...,\"proj_type\":...,\"proj_num\":...,\"proj_name\":...}]",
        "",
        "3) 不要按 zh/en 分成两块返回。需要中英文的值放在同一个字段数组里，用 lang 区分，例如 [{\"lang\":\"zh\",\"name\":\"...\"},{\"lang\":\"en\",\"name\":\"...\"}]。",
        "",
        "4) 不可翻译/保留原样的内容包括但不限于：网址、DOI、arXiv ID、邮箱、UUID、日期、数值、代码片段、专有编号。",
        "",
        "5) 对于描述、摘要、引言、方法、致谢等长文本字段，只输出一到两句的短摘要，不要照搬大段原文。",
        "",
        "6) 对于作者、机构、期刊、许可、分类等字段，优先输出简短规范名称，不要展开解释。",
        "",
        "7) 对于含多值的字段，可返回数组；核心元数据字段必须优先使用上述标准对象数组，不要简化成纯字符串数组。",
        "",
        "8) 【重要】扩展信息字段：中文为\"扩展信息\"，英文为\"Extension Info\"。"
        "   请从网页中提取以上所有字段都没有覆盖到的、但你认为重要的额外信息，"
        "   例如：数据使用注意事项、相关项目信息、数据集特点、研究亮点、"
            "4) 不可翻译/保留原样的内容包括但不限于：网址、DOI、arXiv ID、邮箱、UUID、日期、数值、代码片段、专有编号。",
            "• 标识符类型要求：对于核心字段中的“CSTR标识符”，必须是 CSTR 格式（示例：12345.12.123456.123456）。如果网页中没有明确的 CSTR 标识符，请返回 null，不要用 arXiv ID、DOI 或 URL 代替。",
            "",
        "9) 必须从\"资源类型候选列表\"中判断资源类型，并将结果写入核心字段 resource_type，值使用规范英文枚举：\"Dataset\"/\"Data Paper\"/\"Other\"。",
        "",
        "10) 核心元数据对象只能包含上述 17 个字段，不要把 domain_metadata、领域判定、extension_info、扩展信息放入核心元数据对象。",
        "",
        "11) 除了核心元数据外，还要根据 resource_type 返回对应的完整领域 schema 结构：",
        "    - resource_type = \"数据论文\" / \"Data Paper\" → 额外返回\"数据论文内容信息\"、\"数据论文出版信息\"、\"数据论文服务信息\"及其子字段",
        "    - resource_type = \"数据集\" / \"Dataset\" → 额外返回\"数据集基本信息\"、\"数据集出版信息\"、\"数据集服务信息\"及其子字段",
        "    - resource_type = \"其他\" / \"Other\" → 不需要额外返回领域结构",
        "",
        "12) 如果页面来自 arXiv（URL/title/text 中出现 arXiv 线索），优先判定为\"数据论文\"。",
        "",
        "13) 最终返回的 JSON 顶层结构应该是统一对象，不要包含顶层 zh/en：",
        "    {",
        '        "核心元数据": {"metadatas": [{',
        '          "titles": [{"lang": "zh", "name": "..."}, {"lang": "en", "name": "..."}],',
        '          "identifier": ...,',
        '          "creators": [{"type": "Person", "person": {"names": [{"lang": "zh", "name": "..."}, {"lang": "en", "name": "..."}], "emails": null, "identifiers": null, "affiliations": null}}],',
        '          "publisher": {"names": [{"lang": "zh", "name": "..."}, {"lang": "en", "name": "..."}], "identifiers": null},',
        '          "publish_date": ...,',
        '          "descriptions": [{"lang": "zh", "description": "..."}, {"lang": "en", "description": "..."}],',
        '          "keywords": [{"lang": "zh", "keyword": ["..."]}, {"lang": "en", "keyword": ["..."]}],',
        '          "subjects": [{"standard_gbt": ["..."], "standard_oecd": null}],',
        '          "language": ...,',
        '          "contributors": ...,',
        '          "alternative_identifiers": ...,',
        '          "related_identifiers": ...,',
        '          "rights": ...,',
        '          "funders": ...,',
        '          "version": ...,',
        '          "urls": ...,',
        '          "resource_type": "Dataset/Data Paper/Other"',
        '        }]},',
        '        "数据论文内容信息": {...},',
        '        "数据论文出版信息": {...},',
        '        "数据论文服务信息": {...}',
        "    }"
    ])
    
    few_shot_examples = '''
示例（数据论文 - 核心元数据必须是文档第 6 节 metadatas 形态，且核心对象只有 17 个字段）：
网页文字: "Paper: Title: Climate Observations. DOI: 10.1234/abcd. Published on 2025-01-01."
期望输出:
{
  "核心元数据": {
    "metadatas": [
      {
        "titles": [{"lang": "zh", "name": "气候观测数据分析"}, {"lang": "en", "name": "Climate Observations Analysis"}],
        "identifier": null,
        "creators": [{"type": "Person", "person": {"names": [{"lang": "zh", "name": "Smith"}, {"lang": "en", "name": "Smith"}], "emails": null, "identifiers": null, "affiliations": null}}],
        "publisher": {"names": [{"lang": "zh", "name": "Journal of Climate Data"}, {"lang": "en", "name": "Journal of Climate Data"}], "identifiers": null},
        "publish_date": "2025-01-01",
        "descriptions": [{"lang": "zh", "description": "分析了气候观测数据的时间序列特征。"}, {"lang": "en", "description": "Short abstract: analyzes time-series features of climate observations."}],
        "keywords": [{"lang": "zh", "keyword": ["气候", "观测", "时间序列"]}, {"lang": "en", "keyword": ["climate", "observations", "time-series"]}],
        "subjects": [{"standard_gbt": ["大气科学"], "standard_oecd": null}],
        "language": "zh",
        "contributors": null,
        "alternative_identifiers": [{"type": "DOI", "identifier": "10.1234/abcd"}],
        "related_identifiers": null,
        "rights": null,
        "funders": null,
        "version": null,
        "urls": ["https://example.org/paper/123"],
        "resource_type": "Data Paper"
      }
    ]
  },
  "数据论文内容信息": {"标识符": {"type": "DOI", "identifier": "10.1234/abcd"}, "标题": [{"lang": "zh", "name": "气候观测数据分析"}, {"lang": "en", "name": "Climate Observations Analysis"}]},
  "数据论文出版信息": {"出版日期": "2025-01-01"},
  "数据论文服务信息": {"数据论文下载地址": "https://example.org/paper/123"}
}
'''

    prompt = f"""基于以下标准 JSON（中文/英文）以及网页文字，输出一份统一元数据 JSON，核心元数据里的中英文值使用 lang 区分，严格按照规则返回，不要多余文本。

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

请直接输出统一 JSON 对象，不要包含顶层 `zh` 和 `en`。"""

    return prompt


def _extract_json_from_text(text):
    try:
        start = text.index('{')
        end = text.rindex('}')
        candidate = text[start:end+1]
        return json.loads(candidate)
    except Exception:
        return None


def _normalize_inline_math_text(value):
    if not isinstance(value, str):
        return value

    text = value
    text = unicodedata.normalize('NFC', text)
    text = re.sub(r'\\"\{([^{}]+)\}', lambda match: _to_diacritic(match.group(1), 'diaeresis'), text)
    text = re.sub(r'\\"([A-Za-z])', lambda match: _to_diacritic(match.group(1), 'diaeresis'), text)
    text = re.sub(r"\\'\{([^{}]+)\}", lambda match: _to_diacritic(match.group(1), 'acute'), text)
    text = re.sub(r"\\'([A-Za-z])", lambda match: _to_diacritic(match.group(1), 'acute'), text)
    text = re.sub(r'\\`\{([^{}]+)\}', lambda match: _to_diacritic(match.group(1), 'grave'), text)
    text = re.sub(r'\\`([A-Za-z])', lambda match: _to_diacritic(match.group(1), 'grave'), text)
    text = re.sub(r'\\(?:left|right)\b', '', text)
    text = re.sub(r'\\(?:mathrm|mathbf|mathit|text|operatorname)\{([^{}]*)\}', r'\1', text)
    text = re.sub(r'\\frac\{([^{}]*)\}\{([^{}]*)\}', r'\1/\2', text)
    text = re.sub(r'\\sqrt\{([^{}]*)\}', r'√\1', text)
    text = re.sub(r'\$\$(.+?)\$\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'(?<!\\)\$(.+?)(?<!\\)\$', r'\1', text, flags=re.DOTALL)
    text = re.sub(r'\\([A-Za-z]+)(?![A-Za-z])', lambda match: _LATEX_COMMANDS.get(match.group(1), match.group(0)), text)
    text = re.sub(r'\^\{([^{}]+)\}', lambda match: _to_superscript(match.group(1)), text)
    text = re.sub(r'_\{([^{}]+)\}', lambda match: _to_subscript(match.group(1)), text)
    text = re.sub(r'\^([A-Za-z0-9+-])', lambda match: _to_superscript(match.group(1)), text)
    text = re.sub(r'_([A-Za-z0-9+-])', lambda match: _to_subscript(match.group(1)), text)
    text = text.replace('\\$', '$')
    text = text.replace('\\', '\\')
    return text


_LATEX_COMMANDS = {
    'alpha': 'α',
    'beta': 'β',
    'gamma': 'γ',
    'delta': 'δ',
    'epsilon': 'ε',
    'zeta': 'ζ',
    'eta': 'η',
    'theta': 'θ',
    'iota': 'ι',
    'kappa': 'κ',
    'lambda': 'λ',
    'mu': 'μ',
    'nu': 'ν',
    'xi': 'ξ',
    'pi': 'π',
    'rho': 'ρ',
    'sigma': 'σ',
    'tau': 'τ',
    'phi': 'φ',
    'chi': 'χ',
    'psi': 'ψ',
    'omega': 'ω',
    'Alpha': 'Α',
    'Beta': 'Β',
    'Gamma': 'Γ',
    'Delta': 'Δ',
    'Theta': 'Θ',
    'Lambda': 'Λ',
    'Xi': 'Ξ',
    'Pi': 'Π',
    'Sigma': 'Σ',
    'Phi': 'Φ',
    'Psi': 'Ψ',
    'Omega': 'Ω',
    'pm': '±',
    'times': '×',
    'cdot': '·',
    'le': '≤',
    'ge': '≥',
    'neq': '≠',
    'approx': '≈',
    'sim': '∼',
    'propto': '∝',
    'infty': '∞',
    'degree': '°',
}


_SUPERSCRIPTS = str.maketrans({
    '0': '⁰',
    '1': '¹',
    '2': '²',
    '3': '³',
    '4': '⁴',
    '5': '⁵',
    '6': '⁶',
    '7': '⁷',
    '8': '⁸',
    '9': '⁹',
    '+': '⁺',
    '-': '⁻',
    '=': '⁼',
    '(': '⁽',
    ')': '⁾',
    'n': 'ⁿ',
    'i': 'ⁱ',
})


_SUBSCRIPTS = str.maketrans({
    '0': '₀',
    '1': '₁',
    '2': '₂',
    '3': '₃',
    '4': '₄',
    '5': '₅',
    '6': '₆',
    '7': '₇',
    '8': '₈',
    '9': '₉',
    '+': '₊',
    '-': '₋',
    '=': '₌',
    '(': '₍',
    ')': '₎',
})


def _to_superscript(value):
    text = str(value)
    translated = text.translate(_SUPERSCRIPTS)
    return translated if translated != text else f'^{text}'


def _to_subscript(value):
    text = str(value)
    translated = text.translate(_SUBSCRIPTS)
    return translated if translated != text else f'_{text}'


_DIACRITIC_MAP = {
    'diaeresis': {
        'a': 'ä', 'o': 'ö', 'u': 'ü', 'A': 'Ä', 'O': 'Ö', 'U': 'Ü', 'e': 'ë', 'i': 'ï', 'y': 'ÿ',
    },
    'acute': {
        'a': 'á', 'e': 'é', 'i': 'í', 'o': 'ó', 'u': 'ú', 'y': 'ý', 'A': 'Á', 'E': 'É', 'I': 'Í', 'O': 'Ó', 'U': 'Ú', 'Y': 'Ý',
    },
    'grave': {
        'a': 'à', 'e': 'è', 'i': 'ì', 'o': 'ò', 'u': 'ù', 'A': 'À', 'E': 'È', 'I': 'Ì', 'O': 'Ò', 'U': 'Ù',
    },
}


def _to_diacritic(value, accent):
    text = str(value)
    mapped = ''.join(_DIACRITIC_MAP.get(accent, {}).get(char, char) for char in text)
    return mapped if mapped != text else text


def _normalize_inline_math_tree(value):
    if isinstance(value, dict):
        return {key: _normalize_inline_math_tree(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_inline_math_tree(item) for item in value]
    return _normalize_inline_math_text(value)


def _set_core_classification(answer, resource_type, domain, language='zh'):
    if not isinstance(answer, dict):
        return

    section_key = 'Core Metadata' if language == 'en' else '核心元数据'
    section = answer.get(section_key)
    if isinstance(section, dict):
        metadatas = section.get('metadatas')
        if isinstance(metadatas, list) and metadatas and isinstance(metadatas[0], dict):
            if not metadatas[0].get('resource_type'):
                metadatas[0]['resource_type'] = resource_type
            return

    resource_key = 'resource_type'

    if not answer.get(resource_key):
        answer[resource_key] = resource_type


def _map_type_to_domain_and_en(resource_type_zh):
    mapping = {
        '数据集': ('Dataset', '数据集元数据', 'Dataset Metadata'),
        '数据论文': ('Data Paper', '数据论文元数据', 'Data Paper Metadata'),
        '其他': ('Other', '核心元数据', 'Core Metadata'),
    }
    return mapping.get(resource_type_zh, ('Other', '核心元数据', 'Core Metadata'))


def qwen_chat(content, mode='核心元数据', url='', title='', raw_html='', strategy='auto'):
    standard = load_standard()
    strategy = (strategy or 'auto').lower()
    rule_content = raw_html or content
    
    # 第一步：尝试检测并处理已知网站（不调用大模型）
    if strategy in ('auto', 'rule'):
        print(f"[Extractor Debug] url={url}, title={title}, content_len={len(rule_content or '')}")
        website_result = extract_metadata(url=url, title=title, content=rule_content)
        if website_result is not None:
            return _normalize_inline_math_tree(website_result)
        if strategy == 'rule':
            return {
                "error": "rule_not_matched",
                "message": "规则模式未匹配到已知网站提取器",
                "available_extractors": list_extractors(),
            }
    
    # 第二步：如果未检测到已知网站，则调用大模型
    print("[LLM Processing] 使用大模型处理...")
    pre_type_zh = classify_resource_type(content, url=url, title=title)
    prompt = _build_prompt(content, standard, url=url, title=title, preclassified_type=pre_type_zh)

    completion = client.chat.completions.create(
        model="Qwen/Qwen3-8B",
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
            type_en, domain_zh, domain_en = _map_type_to_domain_and_en(pre_type_zh)
            if isinstance(parsed.get('zh'), dict) or isinstance(parsed.get('en'), dict):
                zh = parsed.get('zh', {})
                en = parsed.get('en', {})
                _set_core_classification(zh, pre_type_zh, domain_zh, 'zh')
                _set_core_classification(en, type_en, domain_en, 'en')
                parsed['zh'] = zh
                parsed['en'] = en
            else:
                _set_core_classification(parsed, type_en, domain_zh, 'zh')
            parsed = _normalize_inline_math_tree(parsed)
        return parsed
    except Exception:
        extracted = _extract_json_from_text(raw)
        if extracted is not None:
            if isinstance(extracted, dict):
                type_en, domain_zh, domain_en = _map_type_to_domain_and_en(pre_type_zh)
                if isinstance(extracted.get('zh'), dict) or isinstance(extracted.get('en'), dict):
                    zh = extracted.get('zh', {})
                    en = extracted.get('en', {})
                    _set_core_classification(zh, pre_type_zh, domain_zh, 'zh')
                    _set_core_classification(en, type_en, domain_en, 'en')
                    extracted['zh'] = zh
                    extracted['en'] = en
                else:
                    _set_core_classification(extracted, type_en, domain_zh, 'zh')
                extracted = _normalize_inline_math_tree(extracted)
            return extracted

    return {"error": "invalid_json", "raw": raw}
