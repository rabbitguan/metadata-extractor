const BACKEND_QUERY_URL = "http://127.0.0.1:4000/query";
const BACKEND_REGISTER_URL = "http://127.0.0.1:4000/register";
const DOWNLOAD_LANGUAGE = "en";
const CONVERSION_LOG_STORAGE_KEY = "metadata_web_conversion_logs_v1";
const MAX_CONVERSION_LOGS = 50;
const UPLOAD_EXAMPLE_JSON = `{
  "resource_type": "dataset",
  "core": {
    "title": "Example Dataset",
    "cstr_identifier": "31253.11.CSTR.2026.000001",
    "creators": ["Alice Zhang", "Bob Li"],
    "publisher": "Example Data Center",
    "publication_date": "2026-06-20",
    "description": "A short description of the resource.",
    "keywords": ["metadata", "dataset"],
    "subjects": ["Computer Science"],
    "language": "en",
    "alternative_identifiers": ["10.1234/example.dataset"],
    "resource_url": ["https://example.org/datasets/001"]
  },
  "domain": {
    "dataset_basic_information": {},
    "dataset_publication_information": {},
    "dataset_service_information": {}
  }
}`;

const STANDARD_SCHEMA = JSON.parse(`{
    "资源类型候选列表": [
        {
            "类型名称": "数据集",
            "英文类型": "Dataset",
            "领域元数据": "数据集元数据"
        },
        {
            "类型名称": "数据论文",
            "英文类型": "Data Paper",
            "领域元数据": "数据论文元数据"
        },
        {
            "类型名称": "标准文献",
            "英文类型": "Standard Literature",
            "领域元数据": "标准文献元数据"
        },
        {
            "类型名称": "生态科学数据",
            "英文类型": "Ecological Data",
            "领域元数据": "生态科学数据元数据"
        },
        {
            "类型名称": "其他",
            "英文类型": "Other",
            "领域元数据": "核心元数据"
        }
    ],
    "核心元数据": {
        "标题": "科技资源的正式名称，是资源发现与引用的核心信息。",
        "CSTR标识符": "依据科技资源标识标准为资源分配的全球唯一持久标识符。",
        "创建者": "直接参与资源制作并做出主要贡献的人员（如作者、开发者）。",
        "发布机构": "发布或产出该科技资源的机构。",
        "发布日期": "资源对外正式发布的日期（非注册日期）。",
        "描述": "对科技资源内容、用途、方法等的详细说明。",
        "关键词": "用于资源检索与主题分类的词汇标签。",
        "学科": "资源所属学科分类。",
        "语言": "资源内容使用的语言。",
        "贡献者": "参与创作但贡献次要，或提供辅助支持的人员。",
        "替代标识符": "资源已注册的其他标识（DOI、Handle等）。",
        "关联标识符": "与当前资源存在引用、补充、衍生等关系的其他资源标识。",
        "权限": "资源使用权限、开放协议、版权声明。",
        "资助者": "支持资源研发的基金、项目、机构。",
        "版本": "资源版本号。",
        "资源链接": "科技资源页面的URL。",
        "资源类型": "科技资源所属类型（科学数据、学术论文等）。"
    },
    "数据集元数据": {
        "数据集基本信息": {
            "标识符": "数据集的唯一标识编码",
            "标题": "数据集公开的标题",
            "摘要": "数据集的简要介绍",
            "关键词": "数据集的关键词",
            "范围": {
                "时间范围": "数据集的时间范围",
                "空间范围": "数据集的空间范围"
            },
            "语种": "数据集的描述语言",
            "文件内容": "数据集包括的文件数和具体文件内容",
            "基金项目": "数据集的项目或基金支持",
            "数据量": "数据集所占的物理存储空间大小或数量",
            "数据格式": "数据集的文件格式",
            "数据集作者": {
                "作者姓名": "数据集的作者姓名",
                "工作单位": "数据集作者所属单位",
                "电子邮箱": "数据集作者的电子邮箱地址",
                "工作贡献": "数据集作者的工作贡献",
                "作者简介": "数据集作者的简要介绍"
            }
        },
        "数据集出版信息": {
            "发布日期": "数据集公开发布的时间",
            "出版期刊": "数据集关联出版的数据期刊名称",
            "版本信息": "数据集的版本信息"
        },
        "数据集服务信息": {
            "数据集引用格式": "数据集的引用格式",
            "数据集共享许可协议": "数据集的共享许可协议",
            "数据集使用声明": "数据集使用遵循的规则",
            "数据集下载地址": "数据集在互联网的下载地址",
            "数据论文访问地址": "以数据集为核心出版的论文的访问地址"
        }
    },
    "数据论文元数据": {
        "数据论文内容信息": {
            "标识符": "数据论文的唯一标识编码",
            "标题": "数据论文的标题",
            "摘要": "数据论文的简要介绍",
            "关键词": "数据论文的关键词",
            "数据集基本信息": {
                "标识符": "数据集的唯一标识编码",
                "标题": "数据集公开的标题",
                "摘要": "数据集的简要介绍",
                "关键词": "数据集的关键词",
                "范围": {
                    "时间范围": "数据集的时间范围",
                    "空间范围": "数据集的空间范围"
                },
                "语种": "数据集的描述语言",
                "文件内容": "数据集包括的文件数和具体文件内容",
                "基金项目": "数据集的项目或基金支持",
                "数据量": "数据集所占的物理存储空间大小或数量",
                "数据格式": "数据集的文件格式",
                "数据集作者": {
                    "作者姓名": "数据集的作者姓名",
                    "工作单位": "数据集作者所属单位",
                    "电子邮箱": "数据集作者的电子邮箱地址",
                    "工作贡献": "数据集作者的工作贡献",
                    "作者简介": "数据集作者的简要介绍"
                }
            },
            "引言": "数据论文的引言部分",
            "数据采集和处理方法": "数据论文的数据采集和处理方法",
            "数据样本描述": "描述数据集的典型样本来源数据结构等",
            "数据质量控制和评估": "数据质量控制方法和验证过程",
            "数据使用方法和建议": "数据集的使用方法和建议",
            "参考文献": "数据论文引用的参考文献列表",
            "致谢": "数据论文的致谢部分",
            "数据论文作者": {
                "作者姓名": "数据论文作者的姓名",
                "工作单位": "数据论文作者所属单位",
                "电子邮箱": "数据论文作者的电子邮箱地址",
                "工作贡献": "数据论文作者的工作贡献",
                "作者简介": "数据论文作者的简要介绍"
            }
        },
        "数据论文出版信息": {
            "收稿日期": "数据论文的收稿日期",
            "同评日期": "数据论文的同行评审日期",
            "录用日期": "数据论文的录用日期",
            "出版日期": "数据论文的出版日期",
            "版本信息": "数据论文的版本信息",
            "出版期刊": "数据论文出版期刊名称"
        },
        "数据论文服务信息": {
            "数据论文引用格式": "数据论文的引用格式",
            "数据论文下载地址": "数据论文在互联网的下载地址",
            "数据论文共享许可协议": "数据论文的共享许可协议",
            "数据集访问地址": "与数据论文相关的数据集的访问地址"
        }
    },
    "标准文献元数据": {
        "记录状态": "关于标准文献数据库中记录所处的状态（修改、删除、新增）的说明",
        "记录识别符": "建立记录的单位对某一记录给定的唯一识别符号",
        "记录日期": "建立记录的日期",
        "标准号": "由有关标准化机构给定的用于唯一识别某一标准的注册号或登记号，由标准代号、顺序号、发布年份组成",
        "发布日期": "标准经有关机构批准，予以发布的日期",
        "发布机构": "公布所著录标准的单位",
        "标准状态": "标准文献所处的状态或属性，说明所著录标准是草案、试行、暂行、废止或其他状态",
        "实施或试行日期": "标准经有关机构批准后正式生效或试行的日期",
        "确认日期": "标准经重审确认继续有效的日期",
        "被代替标准": "所著录标准代替的标准，有多个时以分号相隔",
        "修改件": "修改所著录标准的文献的代号、总次和总次发布年份的说明",
        "补充件": "补充所著录标准的文献的代号、总次和总次发布年份的说明",
        "第二标准号": "所著录标准有多个标准号时，其第二个及以上的标准号",
        "批准单位": "标准的审查批准单位",
        "中文标准名称": "标准的中文名称或中文译名",
        "原文标准名称": "中、英文以外语种的标准名称",
        "英文标准名称": "标准的英文名称或英文译名",
        "发布机构代码": "公布所著录标准的单位的代码",
        "中国标准分类号": "标准的《中国标准文献分类法》分类号",
        "国际标准分类号": "标准的《国际标准分类法》分类号",
        "ISBN": "国际标准书号",
        "ISSN": "国际标准连续出版物编号",
        "版本": "标准出版的版次或其他版本形式说明",
        "有效区域": "标准文献所适用的地域",
        "废止日期": "标准作废的日期",
        "原分类号": "标准发布机构给定的分类号或其他专业分类号",
        "起草单位": "起草标准的单位名称，多个时以分号相隔",
        "截止日期": "标准发布时所规定的标准有效期限的终止日期",
        "正文语种": "标准正文所用文字的语种代码",
        "出版单位": "出版标准的单位名称",
        "稽核项": "关于标准文献的总页数、开本的说明",
        "译文": "标准译文版本说明",
        "价格": "标准文献价格或价格组别与币种标识",
        "其他载体": "标准文献实体除纸版载体以外的其他载体形态",
        "中文文摘": "标准文献的中文内容摘要",
        "英文文摘": "标准文献的英文内容摘要",
        "英文主题词": "反映标准文献主题内容的英文规范词，多个时以分号相隔",
        "附注": "对所著录标准进行的补充说明，如首次发布时间、更正及勘误情况等",
        "文献出处": "母体文献的题名与责任项及出版项等的主要信息",
        "代替标准": "代替所著录标准的标准号，多个时以分号相隔",
        "引用文件": "被著录标准所引用文件的代号，多个时以分号相隔",
        "相关法律": "对所发布标准进行授权的法律",
        "一致性程度": "所著录标准采用其他标准的标准号及一致性程度标识",
        "被修改件": "被所著录文件修改的标准号",
        "被补充件": "被所著录文件补充的标准号",
        "中文主题词": "反映标准文献主题内容的中文规范词，采用《标准文献主题词表》中的主题词",
        "中文自由词": "直接从文献中抽出的作为文献检索标识的中文词语或字符",
        "原文主题词": "除中、英文以外语种反映标准文献主题内容的原文规范词",
        "索取号": "文献收藏单位的索书号",
        "馆藏标志": "所著录标准是否有馆藏的说明（0：无馆藏，1：有馆藏）",
        "排序码": "为按标准号排序而生成的代码",
        "标准类型": "反映所著录标准的标准化对象类别的代码",
        "文献类型": "文献的种类，按GB/T 3469著录",
        "卷期号": "分卷出版的文献的卷期编号",
        "文献代号": "标准文献发布机构赋予本类标准的统一代号",
        "出版周期": "连续出版的文献的出版周期",
        "出版地": "标准出版单位所在地",
        "密级": "文献的保密等级",
        "提出单位": "提出标准的单位的名称",
        "归口单位": "标准的技术归口单位的名称",
        "国别": "标准文献的批准发布机构所属的国家或地区代码",
        "标引依据": "标引或修改当前记录的依据",
        "更新批号": "更新数据的批次号，采用YYMM格式",
        "标准历史": "标准的首次发布到本版标准的沿革信息",
        "参建单位": "标准文献数据建设单位",
        "电子文件名称": "标准文献电子版的文件名称，按标准号命名"
    },
    "生态科学数据元数据": {
        "标识信息": {
            "资源名称": "数据集的正式名称",
            "资源标识符": "数据集的唯一标识符或访问编号",
            "摘要": "数据集内容的简要介绍",
            "关键词": "描述数据集主题的关键词或短语",
            "学科分类": "所属生态学分支学科，如分子生态学、森林生态学、种群生态学等",
            "数据集创建者": "创建数据集的主要责任者（个人或单位）",
            "创建日期": "数据集的创建时间",
            "最近修改日期": "数据集的最近一次修改时间",
            "使用限制": "访问数据资源的限制和先决条件"
        },
        "数据内容信息": {
            "数据实体": {
                "实体名称": "包含数据的文件或数据库表名",
                "实体描述": "对该数据实体的简要描述",
                "实体类型": "数据实体的类型，如电子表格、关系数据库表、文本文件、栅格图像",
                "数据量": "文件大小或数据记录数",
                "数据格式": "文件的格式，如.csv、.tif、.xlsx"
            }
        },
        "数据质量与方法": {
            "数据质量描述": "关于数据质量的总体说明",
            "数据产生方法": "描述数据是如何产生的（观测、试验、模型模拟等）",
            "数据采集和处理方法": "对采样、实验、数据加工等方法的详细说明",
            "质量控制说明": "为保证或控制数据质量所采取的措施",
            "数据源": "本数据集所引用的原始数据或资料"
        },
        "空间与时间覆盖范围": {
            "空间范围": {
                "地理范围描述": "对地理范围的一般性文本描述，如'中国内蒙古自治区锡林郭勒盟'",
                "西部边界经度": "最小经度",
                "东部边界经度": "最大经度",
                "南部边界纬度": "最小纬度",
                "北部边界纬度": "最大纬度"
            },
            "时间范围": {
                "起始时间": "数据覆盖的开始时间",
                "结束时间": "数据覆盖的结束时间"
            }
        },
        "项目与资助信息": {
            "项目名称": "为产生这些数据而开展的科研项目名称",
            "项目代码": "项目的代码或批准号",
            "资金来源": "资助项目的机构或基金，如国家自然科学基金、科技部等"
        },
        "分发与引用信息": {
            "数据集的引用格式": "建议用户引用该数据集的格式",
            "数据集共享许可协议": "数据集的共享许可协议，如CC BY 4.0",
            "数据集访问或下载地址": "在线获取数据的URL"
        }
    }
}`);

const LABEL_TRANSLATIONS_EN = {
    "资源类型候选列表": "Resource Type Candidates",
    "类型名称": "Type Name",
    "英文类型": "English Type",
    "领域元数据": "Domain Metadata",
    "核心元数据": "Core Metadata",
    "数据集元数据": "Dataset Metadata",
    "数据论文元数据": "Data Paper Metadata",
    "标准文献元数据": "Standard Literature Metadata",
    "生态科学数据元数据": "Ecological Science Data Metadata",
    "数据集基本信息": "Dataset Basic Information",
    "数据集出版信息": "Dataset Publication Information",
    "数据集服务信息": "Dataset Service Information",
    "数据论文内容信息": "Data Paper Content Information",
    "数据论文出版信息": "Data Paper Publication Information",
    "数据论文服务信息": "Data Paper Service Information",
    "标题": "Title",
    "CSTR标识符": "Identifier",
    "创建者": "Creators",
    "发布机构": "Publisher",
    "发布日期": "Publication Date",
    "描述": "Description",
    "关键词": "Keywords",
    "学科": "Subjects",
    "语言": "Language",
    "贡献者": "Contributors",
    "替代标识符": "Alternative Identifiers",
    "关联标识符": "Related Identifiers",
    "权限": "Rights",
    "资助者": "Funders",
    "版本": "Version",
    "资源链接": "Resource URL",
    "资源类型": "ResourceType",
    "领域判定": "Domain Classification",
    "扩展信息": "Extension Info",
    "标识符": "Identifier",
    "摘要": "Abstract",
    "范围": "Scope",
    "时间范围": "Time Range",
    "空间范围": "Spatial Range",
    "语种": "Language",
    "文件内容": "File Content",
    "基金项目": "Funding Project",
    "数据量": "Data Volume",
    "数据格式": "Data Format",
    "数据集作者": "Dataset Authors",
    "数据论文作者": "Data Paper Authors",
    "作者姓名": "Author Name",
    "工作单位": "Affiliation",
    "电子邮箱": "Email",
    "工作贡献": "Contribution",
    "作者简介": "Biography",
    "引言": "Introduction",
    "数据采集和处理方法": "Data Collection and Processing Methods",
    "数据样本描述": "Data Sample Description",
    "数据质量控制和评估": "Data Quality Control and Evaluation",
    "数据使用方法和建议": "Data Use Methods and Recommendations",
    "参考文献": "References",
    "致谢": "Acknowledgements",
    "收稿日期": "Received Date",
    "同评日期": "Review Date",
    "录用日期": "Accepted Date",
    "出版日期": "Publication Date",
    "版本信息": "Version Information",
    "出版期刊": "Journal",
    "数据集引用格式": "Dataset Citation",
    "数据集共享许可协议": "Dataset License",
    "数据集使用声明": "Dataset Usage Statement",
    "数据集下载地址": "Dataset Download URL",
    "数据论文访问地址": "Dataset Paper URL",
    "数据论文引用格式": "Data Paper Citation",
    "数据论文下载地址": "Data Paper Download URL",
    "数据论文共享许可协议": "Data Paper License",
    "数据集访问地址": "Dataset Access URL",
    "资源名称": "Resource Name",
    "资源标识符": "Resource Identifier",
    "学科分类": "Subject Classification",
    "数据集创建者": "Dataset Creators",
    "创建日期": "Creation Date",
    "最近修改日期": "Last Modified Date",
    "使用限制": "Use Restrictions",
    "标识信息": "Identification Information",
    "数据内容信息": "Data Content Information",
    "数据实体": "Data Entity",
    "实体名称": "Entity Name",
    "实体描述": "Entity Description",
    "实体类型": "Entity Type",
    "数据质量与方法": "Data Quality and Methods",
    "数据质量描述": "Data Quality Description",
    "数据产生方法": "Data Generation Method",
    "质量控制说明": "Quality Control Description",
    "数据源": "Data Source",
    "空间与时间覆盖范围": "Spatial and Temporal Coverage",
    "地理范围描述": "Geographic Description",
    "西部边界经度": "West Bounding Longitude",
    "东部边界经度": "East Bounding Longitude",
    "南部边界纬度": "South Bounding Latitude",
    "北部边界纬度": "North Bounding Latitude",
    "起始时间": "Start Time",
    "结束时间": "End Time",
    "项目与资助信息": "Project and Funding Information",
    "项目名称": "Project Name",
    "项目代码": "Project Code",
    "资金来源": "Funding Source",
    "分发与引用信息": "Distribution and Citation Information",
    "数据集访问或下载地址": "Dataset Access or Download URL"
};

const MODE_LABELS = {
    common: { zh: "核心元数据项目表", en: "Core Metadata" },
    domain: { zh: "领域专用元数据项目表", en: "Domain Metadata" }
};

const UI_TEXT = {
    zh: {
        startTitle: "元数据双向映射工具",
        startDescription: "请选择分析方式：领域元数据到核心元数据 / 核心元数据到领域元数据",
        domainToCoreTitle: "领域元数据到核心元数据",
        domainToCoreHint: "从 URL 或文件内容抽取并映射为核心元数据",
        coreToDomainTitle: "核心元数据到领域元数据",
        coreToDomainHint: "通过标识符解析资源并补全领域元数据",
        homeTitle: "返回主页",
        openApiDocsTitle: "接口文档",
        apiDocsTitle: "接口文档",
        apiDocsSubtitle: "后端主服务地址：http://127.0.0.1:4000",
        openLogsTitle: "转换日志",
        logTitle: "转换日志",
        logSubtitle: "查看最近的转换任务和完整结果",
        logDetailTitle: "转换详情",
        logEmpty: "暂无转换日志",
        logDetailEmpty: "请选择一条转换日志",
        logTaskInfoTitle: "任务信息",
        logInputPreviewTitle: "输入预览",
        logResultTitle: "转换结果",
        clearLogsTitle: "清空",
        closeLogsTitle: "返回主页",
        chooseUrlLabel: "输入 URL",
        chooseUrlHint: "输入网页地址后由后端直接抓取分析",
        chooseUploadLabel: "上传数据",
        chooseUploadHint: "上传符合格式要求的 JSON / XML 文件",
        chooseIdentifierLabel: "输入 DOI/CSTR",
        chooseIdentifierHint: "通过编号解析资源并整理元数据",
        uploadTitle: "上传数据文件",
        uploadExampleButton: "查看 JSON 示例格式",
        uploadExampleButtonHide: "收起 JSON 示例格式",
        uploadButton: "选择文件",
        confirmUploadButton: "确认并分析",
        reselectUploadButton: "重新选择",
        urlTitle: "输入 URL",
        urlDescription: "输入一个网页地址，后端会直接抓取并分析",
        urlPlaceholder: "https://example.com",
        confirmUrlButton: "确认并分析",
        clearUrlButton: "清空",
        identifierTitle: "输入 DOI/CSTR",
        identifierDescription: "支持单个或多个 DOI / CSTR，多个编号可用换行、空格或逗号分隔",
        identifierPlaceholder: "10.xxxx/example 或 12345.12.123456.123456",
        confirmIdentifierButton: "确认并分析",
        clearIdentifierButton: "清空",
        identifierSelectLabel: "选择标识符",
        identifierErrorPrefix: "解析失败: ",
        selectedFileEmpty: "尚未选择文件",
        selectedFilePrefix: "已选择：",
        modeSwitcherLabel: "元数据模式切换",
        extensionTitle: "扩展信息",
        waiting: "等待提取结果",
        noContent: "未提取到内容",
        updatedAt: "更新于 ",
        loadingFile: "正在读取文件内容...",
        loadingIdentifier: "正在解析 DOI/CSTR...",
        loadingSend: "正在分析...",
        loadingUrl: "正在抓取 URL 页面...",
        success: "分析完成",
        downloadBlocked: "当前语言尚未完成提取，无法下载。",
        refreshTitle: "刷新",
        downloadTitle: "下载",
        languageZh: "中",
        languageEn: "EN",
        errorPrefix: "提取失败: ",
        initErrorPrefix: "初始化失败: "
    },
    en: {
        startTitle: "Metadata Bidirectional Mapping Tool",
        startDescription: "Choose a mapping direction: domain metadata to core metadata / core metadata to domain metadata",
        domainToCoreTitle: "Domain Metadata to Core Metadata",
        domainToCoreHint: "Extract URL or file content and map it to core metadata",
        coreToDomainTitle: "Core Metadata to Domain Metadata",
        coreToDomainHint: "Resolve identifiers and enrich domain metadata",
        homeTitle: "Back To Home",
        openApiDocsTitle: "API Docs",
        apiDocsTitle: "API Docs",
        apiDocsSubtitle: "Backend base URL: http://127.0.0.1:4000",
        openLogsTitle: "Conversion Logs",
        logTitle: "Conversion Logs",
        logSubtitle: "Review recent conversion tasks and complete results",
        logDetailTitle: "Conversion Detail",
        logEmpty: "No conversion logs yet",
        logDetailEmpty: "Select a conversion log",
        logTaskInfoTitle: "Task Info",
        logInputPreviewTitle: "Input Preview",
        logResultTitle: "Conversion Result",
        clearLogsTitle: "Clear",
        closeLogsTitle: "Back To Home",
        chooseUrlLabel: "Enter URL",
        chooseUrlHint: "Submit a web address and let the backend fetch it",
        chooseUploadLabel: "Upload data",
        chooseUploadHint: "Upload a formatted JSON / XML file",
        chooseIdentifierLabel: "Enter DOI/CSTR",
        chooseIdentifierHint: "Resolve identifiers and organize metadata",
        uploadTitle: "Upload data file",
        uploadExampleButton: "View JSON example",
        uploadExampleButtonHide: "Hide JSON example",
        uploadButton: "Choose file",
        confirmUploadButton: "Confirm and analyze",
        reselectUploadButton: "Choose again",
        urlTitle: "Enter URL",
        urlDescription: "Enter a web address and let the backend fetch and analyze it",
        urlPlaceholder: "https://example.com",
        confirmUrlButton: "Confirm and analyze",
        clearUrlButton: "Clear",
        identifierTitle: "Enter DOI/CSTR",
        identifierDescription: "Supports one or more DOI/CSTR identifiers separated by new lines, spaces, or commas",
        identifierPlaceholder: "10.xxxx/example or 12345.12.123456.123456",
        confirmIdentifierButton: "Confirm and analyze",
        clearIdentifierButton: "Clear",
        identifierSelectLabel: "Identifier",
        identifierErrorPrefix: "Error: ",
        selectedFileEmpty: "No file selected yet",
        selectedFilePrefix: "Selected: ",
        modeSwitcherLabel: "Metadata mode switcher",
        extensionTitle: "Extension Info",
        waiting: "Waiting for results",
        noContent: "No content extracted",
        updatedAt: "Updated at ",
        loadingFile: "Reading file content...",
        loadingIdentifier: "Resolving DOI/CSTR...",
        loadingSend: "Analyzing...",
        loadingUrl: "Fetching URL page...",
        success: "Analysis completed",
        downloadBlocked: "Nothing is ready to download yet.",
        refreshTitle: "Refresh",
        downloadTitle: "Download",
        languageZh: "中",
        languageEn: "EN",
        errorPrefix: "Extraction failed: ",
        initErrorPrefix: "Initialization failed: "
    }
};

const API_DOCS_TEXT = {
    zh: {
        descriptionLabel: "接口说明",
        requestLabel: "请求体",
        successLabel: "成功响应（200）",
        errorLabel: "失败响应",
        responseNote: "说明：后端固定返回 zh/en 双语结构，中文字段位于 zh，英文字段位于 en。",
        endpoints: [
            {
                method: "POST",
                path: "/register",
                description: "用于 URL、网页文本、普通文本和上传 JSON/XML 内容的元数据提取。",
                request: {
                    source: "url",
                    mode: "common",
                    strategy: "auto",
                    force_reanalyze: false,
                    url: "https://example.com/paper",
                    text: "页面文本内容",
                    html: "<html>...</html>",
                    title: "页面标题"
                },
                success: {
                    zh: {
                        "核心元数据": {
                            "标题": "示例标题",
                            "资源类型": "数据论文",
                            "领域判定": "数据论文元数据",
                            "扩展信息": "未提取到"
                        },
                        "数据论文元数据": {
                            "数据论文内容信息": {
                                "摘要": "..."
                            }
                        }
                    },
                    en: {
                        "Core Metadata": {
                            Title: "Example Title",
                            ResourceType: "Data Paper",
                            "Domain Classification": "Data Paper Metadata",
                            "Extension Info": "Not extracted"
                        },
                        "Data Paper Metadata": {
                            "Data Paper Content Information": {
                                Abstract: "..."
                            }
                        }
                    }
                },
                error: {
                    status: "error",
                    message: "Missing text"
                }
            },
            {
                method: "POST",
                path: "/query",
                description: "用于从 DOI/CSTR 标识符解析资源页面，再进行元数据提取。",
                request: {
                    source: "identifier",
                    mode: "common",
                    identifiers: [
                        "10.1000/xyz123",
                        "12345.12.ABCD-2024"
                    ]
                },
                success: {
                    items: [
                        {
                            identifier: "10.1000/xyz123",
                            type: "doi",
                            resolved_url: "https://doi.org/10.1000/xyz123",
                            source: "doi.org",
                            status: "ok",
                            payload: {
                                zh: {
                                    "核心元数据": {}
                                },
                                en: {
                                    "Core Metadata": {}
                                }
                            },
                            updated_at: "2026-06-21T00:00:00Z"
                        }
                    ]
                },
                error: {
                    status: "error",
                    message: "No DOI or CSTR identifier found"
                }
            }
        ]
    },
    en: {
        descriptionLabel: "Description",
        requestLabel: "Request Body",
        successLabel: "Success Response (200)",
        errorLabel: "Error Response",
        responseNote: "Note: the backend always returns a bilingual zh/en payload. Chinese fields live under zh, and English fields live under en.",
        endpoints: [
            {
                method: "POST",
                path: "/register",
                description: "Extract metadata from URLs, web text, plain text, or uploaded JSON/XML content.",
                request: {
                    source: "url",
                    mode: "common",
                    strategy: "auto",
                    force_reanalyze: false,
                    url: "https://example.com/paper",
                    text: "Page text content",
                    html: "<html>...</html>",
                    title: "Page title"
                },
                success: {
                    zh: {
                        "核心元数据": {
                            "标题": "中文标题示例",
                            "资源类型": "数据论文",
                            "领域判定": "数据论文元数据",
                            "扩展信息": "未提取到"
                        },
                        "数据论文元数据": {
                            "数据论文内容信息": {
                                "摘要": "中文摘要示例"
                            }
                        }
                    },
                    en: {
                        "Core Metadata": {
                            Title: "Example Title",
                            ResourceType: "Data Paper",
                            "Domain Classification": "Data Paper Metadata",
                            "Extension Info": "Not extracted"
                        },
                        "Data Paper Metadata": {
                            "Data Paper Content Information": {
                                Abstract: "..."
                            }
                        }
                    }
                },
                error: {
                    status: "error",
                    message: "Missing text"
                }
            },
            {
                method: "POST",
                path: "/query",
                description: "Resolve DOI/CSTR identifiers to resource pages and extract metadata.",
                request: {
                    source: "identifier",
                    mode: "common",
                    identifiers: [
                        "10.1000/xyz123",
                        "12345.12.ABCD-2024"
                    ]
                },
                success: {
                    items: [
                        {
                            identifier: "10.1000/xyz123",
                            type: "doi",
                            resolved_url: "https://doi.org/10.1000/xyz123",
                            source: "doi.org",
                            status: "ok",
                            payload: {
                                zh: {
                                    "核心元数据": {}
                                },
                                en: {
                                    "Core Metadata": {}
                                }
                            },
                            updated_at: "2026-06-21T00:00:00Z"
                        }
                    ]
                },
                error: {
                    status: "error",
                    message: "No DOI or CSTR identifier found"
                }
            }
        ]
    }
};

const DOMAIN_SCHEMA_KEY_MAP = {
    "数据论文元数据": ["数据论文内容信息", "数据论文出版信息", "数据论文服务信息"],
    "数据集元数据": ["数据集基本信息", "数据集出版信息", "数据集服务信息"],
    "标准文献元数据": ["标准文献信息", "标准文献内容信息", "标准文献出版信息", "标准文献服务信息"],
    "生态科学数据元数据": ["生态科学数据基本信息", "生态科学数据出版信息", "生态科学数据服务信息"]
};

const FIELD_VALUE_ALIASES = {
    "titles": ["Title", "Resource Name", "标题"],
    "identifier": ["Identifier", "CSTR标识符", "标识符"],
    "creators": ["Creators", "Author Name", "Data Paper Authors", "Dataset Authors", "创建者", "作者姓名"],
    "publisher": ["Publisher", "发布机构", "出版机构", "出版单位"],
    "publish_date": ["Publication Date", "Generation Date", "Received Date", "发布日期", "生成日期"],
    "descriptions": ["Description", "Abstract", "摘要", "描述"],
    "keywords": ["Keywords", "关键词"],
    "subjects": ["Subjects", "Discipline Classification", "Subject Classification", "学科", "学科分类"],
    "language": ["Language", "语种", "语言"],
    "contributors": ["Contributors", "贡献者"],
    "alternative_identifiers": ["Alternative Identifiers", "替代标识符"],
    "related_identifiers": ["Related Identifiers", "关联标识符"],
    "rights": ["Rights", "Usage License", "资源使用许可"],
    "funders": ["Funders", "Funding Project", "基金项目", "资助者"],
    "version": ["Version", "Version Information", "版本", "版本信息"],
    "urls": ["Resource URL", "Resource Access URL", "Dataset Download URL", "Data Paper Download URL", "资源链接"],
    "ResourceType": ["ResourceType", "Resource Type Classification", "资源类型"],
    "Domain Classification": ["领域判定"],
    "Extension Info": ["扩展信息"]
};

const state = {
    sourceMode: "url",
    mode: "common",
    language: "zh",
    schemaCache: {},
    resultCacheBySource: { url: {}, upload: {}, identifier: {} },
    resultCache: {},
    lastFetchedAt: null,
    uploadedFile: null,
    uploadedText: "",
    uploadedTitle: "",
    uploadResultReady: false,
    identifierInput: "",
    identifierResultReady: false,
    identifierResults: [],
    currentIdentifierIndex: 0,
    urlInput: "",
    urlResultReady: false,
    isRefreshing: false,
    conversionLogs: [],
    selectedLogId: null,
    logResultLanguage: "zh",
    previousWorkspace: "analysis"
};

function isObject(value) {
    return typeof value === "object" && value !== null && !Array.isArray(value);
}

function normalizeWhitespace(value) {
    return String(value || "").replace(/\s+/g, " ").replace(/\n{3,}/g, "\n\n").trim();
}

function normalizeUrlInput(value) {
    const text = String(value || "").trim();
    if (!text) return "";
    if (/^https?:\/\//i.test(text)) return text;
    if (text.startsWith("//")) return `https:${text}`;
    return `https://${text}`;
}

function getUIText(language = state.language) {
    return UI_TEXT[language] || UI_TEXT.zh;
}

function getSourceKey() {
    return state.sourceMode || "url";
}

function getSourceResultCache() {
    const sourceKey = getSourceKey();
    if (!state.resultCacheBySource[sourceKey]) state.resultCacheBySource[sourceKey] = {};
    return state.resultCacheBySource[sourceKey];
}

function activateSourceMode(sourceMode) {
    state.sourceMode = sourceMode;
    state.resultCache = getSourceResultCache();
}

function loadConversionLogs() {
    try {
        const parsed = JSON.parse(localStorage.getItem(CONVERSION_LOG_STORAGE_KEY) || "[]");
        state.conversionLogs = Array.isArray(parsed) ? parsed : [];
    } catch (error) {
        state.conversionLogs = [];
    }
}

function saveConversionLogs() {
    localStorage.setItem(CONVERSION_LOG_STORAGE_KEY, JSON.stringify(state.conversionLogs));
}

function getSourceLabel(source) {
    return {
        url: "URL",
        upload: "上传 JSON/XML",
        identifier: "DOI/CSTR",
        text: "文本"
    }[source] || source || "未知来源";
}

function getTaskSummary(entry) {
    if (!entry) return "";
    const isEnglish = state.language === "en";
    if (entry.source === "identifier") {
        return isEnglish ? "Core Metadata to Domain Metadata: Identifier Query" : "核心元数据到领域元数据：标识符查询";
    }
    if (entry.source === "upload") {
        return isEnglish ? "Domain Metadata to Core Metadata: JSON/XML Upload" : "领域元数据到核心元数据：JSON/XML上传";
    }
    if (entry.source === "url") {
        return isEnglish ? "Domain Metadata to Core Metadata: URL Query" : "领域元数据到核心元数据：URL查询";
    }
    return isEnglish ? `Conversion: ${getSourceLabel(entry.source)}` : `转换任务：${getSourceLabel(entry.source)}`;
}

function createApiDocSection(title, payload) {
    const fragment = document.createDocumentFragment();
    const heading = document.createElement("h4");
    heading.textContent = title;
    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(payload, null, 2);
    fragment.append(heading, pre);
    return fragment;
}

function createApiDocNote(text) {
    const note = document.createElement("p");
    note.className = "api-doc-note";
    note.textContent = text;
    return note;
}

function renderApiDocs() {
    const docs = API_DOCS_TEXT[state.language] || API_DOCS_TEXT.zh;
    const ui = getUIText();
    document.getElementById("apiDocsTitle").textContent = ui.apiDocsTitle;
    document.getElementById("apiDocsSubtitle").textContent = ui.apiDocsSubtitle;
    document.getElementById("closeApiDocsButton").textContent = ui.closeLogsTitle;

    const root = document.getElementById("apiDocsContent");
    root.innerHTML = "";
    docs.endpoints.forEach((endpoint) => {
        const card = document.createElement("article");
        card.className = "api-doc-card";

        const head = document.createElement("div");
        head.className = "api-doc-head";
        const method = document.createElement("span");
        method.className = "api-method";
        method.textContent = endpoint.method;
        const path = document.createElement("h3");
        path.textContent = endpoint.path;
        head.append(method, path);

        const descriptionTitle = document.createElement("h4");
        descriptionTitle.textContent = docs.descriptionLabel;
        const description = document.createElement("p");
        description.textContent = endpoint.description;

        card.append(
            head,
            descriptionTitle,
            description,
            createApiDocSection(docs.requestLabel, endpoint.request),
            createApiDocSection(docs.successLabel, endpoint.success),
            createApiDocNote(docs.responseNote),
            createApiDocSection(docs.errorLabel, endpoint.error)
        );
        root.appendChild(card);
    });
}

function getLogDisplayTitle(entry) {
    if (!entry) return "";
    if (entry.source === "upload") return entry.title || "未命名上传文件";
    if (entry.source === "identifier") return entry.title || entry.identifierInput || "DOI/CSTR 查询";
    return entry.url || entry.title || "未命名转换任务";
}

function recordConversionLog({ source, mode, strategy, title, url, inputText, payload, identifierInput }) {
    const entry = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        createdAt: new Date().toISOString(),
        source,
        mode,
        strategy,
        title: title || "",
        url: url || "",
        identifierInput: identifierInput || "",
        inputPreview: String(inputText || "").slice(0, 1000),
        payload
    };
    state.conversionLogs = [entry, ...state.conversionLogs].slice(0, MAX_CONVERSION_LOGS);
    state.selectedLogId = entry.id;
    saveConversionLogs();
}

function showLogs() {
    state.previousWorkspace = document.getElementById("analysisWorkspace").hidden ? "start" : "analysis";
    state.logResultLanguage = state.language === "en" ? "en" : "zh";
    document.getElementById("pageHero").hidden = true;
    document.getElementById("startScreen").hidden = true;
    document.getElementById("analysisWorkspace").hidden = true;
    document.getElementById("apiDocsWorkspace").hidden = true;
    document.getElementById("logWorkspace").hidden = false;
    renderLogs();
}

function showApiDocs() {
    window.location.hash = "api-docs";
    updateStaticText();
    document.getElementById("pageHero").hidden = true;
    document.getElementById("startScreen").hidden = true;
    document.getElementById("analysisWorkspace").hidden = true;
    document.getElementById("logWorkspace").hidden = true;
    document.getElementById("apiDocsWorkspace").hidden = false;
    renderApiDocs();
    requestAnimationFrame(() => {
        document.getElementById("apiDocsWorkspace").scrollIntoView({ block: "start" });
    });
}

function goHome() {
    if (window.location.hash === "#api-docs") {
        window.history.replaceState(null, "", `${window.location.pathname}${window.location.search}`);
    }
    document.getElementById("pageHero").hidden = false;
    document.getElementById("logWorkspace").hidden = true;
    document.getElementById("apiDocsWorkspace").hidden = true;
    document.getElementById("analysisWorkspace").hidden = true;
    document.getElementById("startScreen").hidden = false;
    state.previousWorkspace = "start";
    updateStatus("", "info");
}

function appendLogDetailSection(container, title, value) {
    const section = document.createElement("section");
    section.className = "log-detail-section";
    const heading = document.createElement("h3");
    heading.textContent = title;
    const pre = document.createElement("pre");
    pre.textContent = typeof value === "string" ? value : JSON.stringify(value, null, 2);
    section.append(heading, pre);
    container.appendChild(section);
}

function pickLanguagePayload(payload, language) {
    if (!isObject(payload)) return payload || {};
    if (isObject(payload[language])) return payload[language];
    if (Array.isArray(payload.items)) {
        return {
            ...payload,
            items: payload.items.map((item) => {
                if (!isObject(item) || !isObject(item.payload)) return item;
                const localizedPayload = isObject(item.payload[language]) ? item.payload[language] : item.payload;
                return { ...item, payload: localizedPayload };
            })
        };
    }
    return payload;
}

function appendLogResultSection(container, entry) {
    const ui = getUIText();
    const section = document.createElement("section");
    section.className = "log-detail-section";

    const head = document.createElement("div");
    head.className = "log-result-head";

    const heading = document.createElement("h3");
    heading.textContent = ui.logResultTitle;

    const toggle = document.createElement("div");
    toggle.className = "log-result-toggle";
    [
        { language: "zh", label: ui.languageZh },
        { language: "en", label: ui.languageEn }
    ].forEach((option) => {
        const button = document.createElement("button");
        button.type = "button";
        button.textContent = option.label;
        button.className = option.language === state.logResultLanguage ? "active" : "";
        button.addEventListener("click", () => {
            state.logResultLanguage = option.language;
            renderLogDetail(entry);
        });
        toggle.appendChild(button);
    });

    const pre = document.createElement("pre");
    pre.textContent = JSON.stringify(pickLanguagePayload(entry.payload, state.logResultLanguage), null, 2);
    head.append(heading, toggle);
    section.append(head, pre);
    container.appendChild(section);
}

function renderLogDetail(entry) {
    const detail = document.getElementById("logDetail");
    detail.innerHTML = "";
    if (!entry) {
        detail.className = "log-detail empty";
        detail.textContent = getUIText().logDetailEmpty;
        return;
    }
    detail.className = "log-detail";
    const ui = getUIText();
    appendLogDetailSection(detail, ui.logTaskInfoTitle, getTaskSummary(entry));
    appendLogDetailSection(detail, ui.logInputPreviewTitle, entry.inputPreview || (state.language === "en" ? "None" : "无"));
    appendLogResultSection(detail, entry);
}

function renderLogs() {
    const ui = getUIText();
    const list = document.getElementById("logList");
    document.getElementById("logTitle").textContent = ui.logTitle;
    document.getElementById("logSubtitle").textContent = ui.logSubtitle;
    document.getElementById("logDetailTitle").textContent = ui.logDetailTitle;
    document.getElementById("clearLogsButton").textContent = ui.clearLogsTitle;
    document.getElementById("closeLogsButton").textContent = ui.closeLogsTitle;

    list.innerHTML = "";
    if (!state.conversionLogs.length) {
        const empty = document.createElement("div");
        empty.className = "log-item-meta";
        empty.style.padding = "14px";
        empty.textContent = ui.logEmpty;
        list.appendChild(empty);
        renderLogDetail(null);
        return;
    }

    if (!state.selectedLogId || !state.conversionLogs.some((entry) => entry.id === state.selectedLogId)) {
        state.selectedLogId = state.conversionLogs[0].id;
    }

    state.conversionLogs.forEach((entry) => {
        const button = document.createElement("button");
        button.type = "button";
        button.className = `log-item${entry.id === state.selectedLogId ? " active" : ""}`;
        button.addEventListener("click", () => {
            state.selectedLogId = entry.id;
            renderLogs();
        });

        const title = document.createElement("div");
        title.className = "log-item-title";
        title.textContent = getLogDisplayTitle(entry);

        const meta = document.createElement("div");
        meta.className = "log-item-meta";
        meta.textContent = `${getTaskSummary(entry)} · ${new Date(entry.createdAt).toLocaleString("zh-CN", { hour12: false })}`;
        button.append(title, meta);
        list.appendChild(button);
    });

    renderLogDetail(state.conversionLogs.find((entry) => entry.id === state.selectedLogId));
}

function setUploadPanelState() {
    const ui = getUIText();
    const hasSelectedFile = Boolean(state.uploadedFile);
    document.getElementById("uploadIdleState").hidden = hasSelectedFile;
    document.getElementById("uploadSelectedState").hidden = !hasSelectedFile;
    document.getElementById("uploadButton").textContent = ui.uploadButton;
    document.getElementById("confirmUploadButton").textContent = ui.confirmUploadButton;
    document.getElementById("reselectUploadButton").textContent = ui.reselectUploadButton;
}

function setAnalysisVisibility() {
    const modeSwitcher = document.querySelector(".mode-switcher");
    const analysisContent = document.getElementById("analysisContent");
    const uploadPanel = document.getElementById("uploadPanel");
    const identifierPanel = document.getElementById("identifierPanel");
    const identifierSelector = document.getElementById("identifierSelector");
    const urlPanel = document.getElementById("urlPanel");

    uploadPanel.hidden = state.sourceMode !== "upload";
    identifierPanel.hidden = state.sourceMode !== "identifier";
    urlPanel.hidden = state.sourceMode !== "url";

    if (state.sourceMode === "upload") {
        modeSwitcher.hidden = !state.uploadResultReady;
        analysisContent.hidden = !state.uploadResultReady;
        identifierSelector.hidden = true;
        return;
    }
    if (state.sourceMode === "identifier") {
        modeSwitcher.hidden = !state.identifierResultReady;
        analysisContent.hidden = !state.identifierResultReady;
        identifierSelector.hidden = !state.identifierResultReady || state.identifierResults.length === 0;
        return;
    }
    if (state.sourceMode === "url") {
        modeSwitcher.hidden = !state.urlResultReady;
        analysisContent.hidden = !state.urlResultReady;
        identifierSelector.hidden = true;
        return;
    }

    modeSwitcher.hidden = true;
    analysisContent.hidden = true;
    identifierSelector.hidden = true;
}

function getTranslatedLabel(label, language = state.language) {
    if (language === "en") return LABEL_TRANSLATIONS_EN[label] || label;
    const reverseMap = Object.fromEntries(
        Object.entries(LABEL_TRANSLATIONS_EN).map(([zhLabel, enLabel]) => [enLabel, zhLabel])
    );
    return reverseMap[label] || label;
}

function getFieldLookupKeys(fieldKey) {
    const keys = [fieldKey];
    const alias = FIELD_VALUE_ALIASES[fieldKey];
    if (Array.isArray(alias)) keys.push(...alias);
    if (state.language === "en" && LABEL_TRANSLATIONS_EN[fieldKey]) keys.push(LABEL_TRANSLATIONS_EN[fieldKey]);
    if (state.language === "zh") {
        const reverse = Object.fromEntries(Object.entries(LABEL_TRANSLATIONS_EN).map(([k, v]) => [v, k]));
        if (reverse[fieldKey]) keys.push(reverse[fieldKey]);
    }
    return [...new Set(keys)];
}

function findValueByKeyOrAlias(payload, key) {
    if (!isObject(payload)) return undefined;
    if (Object.prototype.hasOwnProperty.call(payload, key)) return payload[key];
    for (const alias of getFieldLookupKeys(key)) {
        if (Object.prototype.hasOwnProperty.call(payload, alias)) return payload[alias];
    }
    for (const value of Object.values(payload)) {
        if (isObject(value)) {
            const found = findValueByKeyOrAlias(value, key);
            if (typeof found !== "undefined") return found;
        }
    }
    return undefined;
}

function translateTree(node, language = state.language) {
    if (Array.isArray(node)) return node.map((item) => translateTree(item, language));
    if (!isObject(node)) return node;
    const entries = Object.entries(node).map(([key, value]) => {
        const translatedKey = getTranslatedLabel(key, language);
        return [translatedKey, translateTree(value, language)];
    });
    return Object.fromEntries(entries);
}

function getSchemaKeyForMode(mode, payload, language = state.language) {
    if (mode === "domain") {
        const coreKey = language === "en" ? "Core Metadata" : "核心元数据";
        const coreData = isObject(payload) ? (payload[coreKey] || payload) : null;
        const domainSectionMap = language === "en"
            ? {
                "Dataset Metadata": DOMAIN_SCHEMA_KEY_MAP["数据集元数据"],
                "Data Paper Metadata": DOMAIN_SCHEMA_KEY_MAP["数据论文元数据"],
                "Standard Literature Metadata": DOMAIN_SCHEMA_KEY_MAP["标准文献元数据"],
                "Ecological Science Data Metadata": DOMAIN_SCHEMA_KEY_MAP["生态科学数据元数据"]
            }
            : DOMAIN_SCHEMA_KEY_MAP;
        if (isObject(coreData)) {
            const classificationKey = language === "en" ? "Domain Classification" : "领域判定";
            const classification = findValueByKeyOrAlias(coreData, classificationKey);
            if (typeof classification === "string" && Object.prototype.hasOwnProperty.call(domainSectionMap, classification)) {
                return language === "en" ? {
                    "Dataset Metadata": "数据集元数据",
                    "Data Paper Metadata": "数据论文元数据",
                    "Standard Literature Metadata": "标准文献元数据",
                    "Ecological Science Data Metadata": "生态科学数据元数据"
                }[classification] : classification;
            }
            for (const [schemaKey, sectionKeys] of Object.entries(DOMAIN_SCHEMA_KEY_MAP)) {
                if (sectionKeys.some((sectionKey) => Object.prototype.hasOwnProperty.call(coreData, sectionKey))) return schemaKey;
            }
        }
    }
    return "核心元数据";
}

function getEffectiveSectionPayload(payload, schemaKey) {
    if (!isObject(payload)) return {};
    const directSection = payload[schemaKey];
    if (isObject(directSection)) return directSection;
    const coreSectionKey = schemaKey === "核心元数据" ? "核心元数据" : schemaKey;
    if (isObject(payload[coreSectionKey])) return payload[coreSectionKey];
    return payload;
}

function updateStatus(message, type = "info") {
    const status = document.getElementById("status");
    status.textContent = message;
    status.className = `status-tag ${type}`;
    status.hidden = !message;
}

async function loadSchema(mode) {
    if (state.schemaCache[mode]) return state.schemaCache[mode];
    state.schemaCache[mode] = STANDARD_SCHEMA;
    return state.schemaCache[mode];
}

async function loadModeSchema(mode) {
    const schema = await loadSchema(mode);
    const schemaRoot = schema["核心元数据"];
    if (!schemaRoot) throw new Error("标准 JSON 中未找到核心元数据");
    return schemaRoot;
}

async function requestBackend(url, payload, loadingText) {
    updateStatus(loadingText, "loading");
    const response = await fetch(url, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload)
    });

    const responseBody = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(responseBody.message || `HTTP ${response.status}`);
    if (responseBody && responseBody.status === "error") throw new Error(responseBody.message || "Unknown error");
    return responseBody;
}

async function requestMetadataFromText(mode, text, { title = "", url = "", html = "", strategy = "auto", source = "text" } = {}) {
    if (!text) throw new Error(state.language === "zh" ? "没有可分析的内容" : "No text to analyze");
    const payload = await requestBackend(BACKEND_REGISTER_URL, {
        source,
        text,
        html,
        url,
        title,
        mode,
        strategy
    }, getUIText().loadingSend);

    state.resultCache.common = payload;
    state.resultCache.domain = payload;
    state.resultCache[state.mode] = payload;
    state.lastFetchedAt = new Date();
    recordConversionLog({
        source,
        mode,
        strategy,
        title,
        url,
        inputText: text,
        payload
    });
    return payload;
}

async function requestMetadataFromUrl(mode) {
    const url = normalizeUrlInput(state.urlInput || "");
    if (!url) throw new Error(state.language === "zh" ? "请输入网页 URL" : "Please enter a URL");

    const payload = await requestBackend(BACKEND_REGISTER_URL, {
        source: "url",
        url,
        mode
    }, getUIText().loadingUrl);

    state.resultCache.common = payload;
    state.resultCache.domain = payload;
    state.resultCache[state.mode] = payload;
    state.lastFetchedAt = new Date();
    recordConversionLog({
        source: "url",
        mode,
        strategy: "url",
        title: url,
        url,
        inputText: url,
        payload
    });
    return payload;
}

async function requestMetadataFromIdentifiers(mode) {
    const identifiers = normalizeWhitespace(state.identifierInput || "");
    if (!identifiers) throw new Error(state.language === "zh" ? "请输入 DOI 或 CSTR 编号" : "Please input DOI or CSTR");

    const payload = await requestBackend(BACKEND_QUERY_URL, {
        source: "identifier",
        identifiers,
        mode
    }, getUIText().loadingIdentifier);

    const items = Array.isArray(payload.items) ? payload.items : [];
    state.identifierResults = items;
    state.currentIdentifierIndex = 0;
    applyIdentifierItemToCache();
    renderIdentifierSelector();
    state.lastFetchedAt = new Date();
    recordConversionLog({
        source: "identifier",
        mode,
        strategy: "identifier",
        title: `DOI/CSTR: ${identifiers.slice(0, 80)}`,
        identifierInput: identifiers,
        inputText: identifiers,
        payload
    });
    return payload;
}

function flattenStructuredValue(value, path = "") {
    if (value === null || typeof value === "undefined") return [];
    if (typeof value === "string" || typeof value === "number" || typeof value === "boolean") {
        return [path ? `${path}: ${String(value)}` : String(value)];
    }
    if (Array.isArray(value)) return value.flatMap((item, index) => flattenStructuredValue(item, `${path}[${index}]`));
    if (isObject(value)) {
        return Object.entries(value).flatMap(([key, item]) => flattenStructuredValue(item, path ? `${path}.${key}` : key));
    }
    return [];
}

function readFileAsText(file) {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => {
            const rawText = String(reader.result || "");
            const lowerName = String(file.name || "").toLowerCase();
            const trimmedText = rawText.trim();
            if (!trimmedText) {
                resolve("");
                return;
            }
            if (!lowerName.endsWith(".json") && !lowerName.endsWith(".xml")) {
                reject(new Error(state.language === "zh" ? "仅支持 JSON / XML 文件" : "Only JSON / XML files are supported"));
                return;
            }
            if (lowerName.endsWith(".json")) {
                try {
                    JSON.parse(rawText);
                } catch (error) {
                    reject(new Error(state.language === "zh" ? "JSON 格式不合法，请按页面提示的 core/domain 结构上传" : "Invalid JSON. Use the core/domain structure shown on the page"));
                    return;
                }
            }
            resolve(rawText);
        };
        reader.onerror = () => reject(new Error("读取文件失败"));
        reader.readAsText(file, "utf-8");
    });
}

async function requestMetadataForUploadedFile(mode) {
    const file = state.uploadedFile;
    if (!file) throw new Error(state.language === "zh" ? "请先选择一个文件" : "Please choose a file first");

    updateStatus(getUIText().loadingFile, "loading");
    const normalizedText = await readFileAsText(file);
    if (!normalizedText) throw new Error(state.language === "zh" ? "文件内容为空" : "File content is empty");
    state.uploadedText = normalizedText;
    state.uploadedTitle = file.name;
    return requestMetadataFromText(mode, normalizedText, { title: file.name, url: "", strategy: "upload_rule", source: "upload" });
}

function renderFieldValue(data) {
    const ui = getUIText();
    if (data === null || typeof data === "undefined" || data === "") return { text: ui.noContent, isEmpty: true };
    if (isObject(data) && Object.prototype.hasOwnProperty.call(data, "value")) {
        const rawValue = data.value;
        if (rawValue === null || typeof rawValue === "undefined" || rawValue === "") return { text: ui.noContent, isEmpty: true };
        if (Array.isArray(rawValue)) return { text: rawValue.map((item) => (isObject(item) ? JSON.stringify(item) : String(item))).join("；"), isEmpty: false };
        return { text: String(rawValue), isEmpty: false };
    }
    if (Array.isArray(data)) return { text: data.map((item) => (isObject(item) ? JSON.stringify(item) : String(item))).join("；"), isEmpty: false };
    if (isObject(data)) return { text: JSON.stringify(data), isEmpty: false };
    return { text: String(data), isEmpty: false };
}

function createFieldRow(label, data) {
    const row = document.createElement("div");
    row.className = "field-row";
    const labelElement = document.createElement("div");
    labelElement.className = "field-label";
    labelElement.textContent = label;

    const valueState = renderFieldValue(data);
    const valueElement = document.createElement("div");
    valueElement.className = `field-value${valueState.isEmpty ? " empty" : ""}`;
    valueElement.textContent = valueState.text;

    row.appendChild(labelElement);
    row.appendChild(valueElement);
    return row;
}

function renderSchemaNode(container, schemaNode, valueNode) {
    Object.entries(schemaNode).forEach(([key, description]) => {
        let currentValue = isObject(valueNode) ? valueNode[key] : undefined;
        if (typeof currentValue === "undefined") {
            for (const lookupKey of getFieldLookupKeys(key)) {
                currentValue = findValueByKeyOrAlias(valueNode, lookupKey);
                if (typeof currentValue !== "undefined") break;
            }
        }
        if (isObject(description)) {
            const group = document.createElement("section");
            group.className = "subgroup";
            const title = document.createElement("div");
            title.className = "group-title";
            const titleText = document.createElement("h3");
            titleText.textContent = key;
            title.appendChild(titleText);
            const fieldList = document.createElement("div");
            fieldList.className = "field-list";
            renderSchemaNode(fieldList, description, currentValue || {});
            group.appendChild(title);
            group.appendChild(fieldList);
            container.appendChild(group);
            return;
        }
        container.appendChild(createFieldRow(key, currentValue));
    });
}

function extractExtensionText(payload, language = state.language) {
    if (!isObject(payload)) return "";
    const extensionKey = language === "en" ? "Extension Info" : "扩展信息";
    const fallbackKey = language === "en" ? "扩展信息" : "Extension Info";
    const extensionValue = payload[extensionKey] ?? payload[fallbackKey];
    if (typeof extensionValue === "string") return extensionValue.trim();
    if (isObject(extensionValue) && typeof extensionValue.value === "string") return extensionValue.value.trim();
    return "";
}

function getCurrentIdentifierItem() {
    const items = Array.isArray(state.identifierResults) ? state.identifierResults : [];
    return items[state.currentIdentifierIndex] || null;
}

function applyIdentifierItemToCache() {
    const item = getCurrentIdentifierItem();
    if (item && item.status === "ok" && isObject(item.payload)) {
        state.resultCache.common = item.payload;
        state.resultCache.domain = item.payload;
        state.resultCache[state.mode] = item.payload;
        return;
    }
    delete state.resultCache.common;
    delete state.resultCache.domain;
    delete state.resultCache[state.mode];
}

function updateIdentifierError() {
    const error = document.getElementById("identifierError");
    const item = getCurrentIdentifierItem();
    if (item && item.status !== "ok") {
        error.textContent = `${getUIText().identifierErrorPrefix}${item.message || getUIText().noContent}`;
        error.hidden = false;
        return;
    }
    error.textContent = "";
    error.hidden = true;
}

function renderIdentifierSelector() {
    const selector = document.getElementById("identifierSelector");
    const select = document.getElementById("identifierSelect");
    const items = Array.isArray(state.identifierResults) ? state.identifierResults : [];
    const shouldShow = state.sourceMode === "identifier" && items.length > 0 && state.identifierResultReady;
    selector.hidden = !shouldShow;
    if (!shouldShow) return;

    select.innerHTML = "";
    items.forEach((item, index) => {
        const option = document.createElement("option");
        option.value = String(index);
        option.textContent = item && item.identifier ? String(item.identifier) : `#${index + 1}`;
        select.appendChild(option);
    });
    select.value = String(state.currentIdentifierIndex);
    updateIdentifierError();
}

function renderMode(mode) {
    const language = state.language;
    if (state.sourceMode === "identifier" && state.identifierResults.length > 0) applyIdentifierItemToCache();

    const payloadBundle = state.resultCache[mode] || {};
    const payload = isObject(payloadBundle[language]) ? payloadBundle[language] : {};
    const schema = state.schemaCache[mode];
    const schemaKey = getSchemaKeyForMode(mode, payload, language);
    const rawSchemaRoot = schema ? (schema[schemaKey] || schema["核心元数据"]) : null;
    const schemaRoot = rawSchemaRoot ? translateTree(rawSchemaRoot, language) : null;
    const sectionPayload = getEffectiveSectionPayload(payload, schemaKey);

    const metadataRoot = document.getElementById("metadataRoot");
    const extensionInfo = document.getElementById("extensionInfo");
    const modeTitle = document.getElementById("modeTitle");
    const lastUpdated = document.getElementById("lastUpdated");
    const ui = getUIText(language);

    modeTitle.textContent = mode === "domain" ? getTranslatedLabel(schemaKey, language) : MODE_LABELS.common[language];
    metadataRoot.innerHTML = "";
    if (schemaRoot) renderSchemaNode(metadataRoot, schemaRoot, sectionPayload);

    const extensionText = extractExtensionText(payload, language);
    extensionInfo.textContent = extensionText || ui.waiting;
    extensionInfo.classList.toggle("empty", !extensionText);

    let lastUpdatedValue = state.lastFetchedAt;
    const currentItem = getCurrentIdentifierItem();
    if (state.sourceMode === "identifier" && currentItem && currentItem.updated_at) {
        const parsed = new Date(currentItem.updated_at);
        if (!Number.isNaN(parsed.getTime())) lastUpdatedValue = parsed;
    }
    lastUpdated.textContent = lastUpdatedValue ? `${ui.updatedAt}${lastUpdatedValue.toLocaleTimeString("zh-CN", { hour12: false })}` : "";

    updateIdentifierError();
    updateStaticText();
}

function stripMetadataForDownload(schemaNode, valueNode) {
    const result = {};
    Object.entries(schemaNode).forEach(([key, description]) => {
        const currentValue = isObject(valueNode) ? valueNode[key] : undefined;
        if (isObject(description)) {
            result[key] = stripMetadataForDownload(description, currentValue || {});
            return;
        }
        if (isObject(currentValue) && Object.prototype.hasOwnProperty.call(currentValue, "value")) {
            result[key] = currentValue.value ?? null;
            return;
        }
        result[key] = Array.isArray(currentValue) ? currentValue : (currentValue ?? null);
    });
    return result;
}

function normalizeIdentifierToken(value) {
    const raw = String(value || "")
        .trim()
        .replace(/^doi:\s*/i, "")
        .replace(/^cstr:\s*/i, "")
        .replace(/^[<(\[]+/, "")
        .replace(/[>\])]+$/, "")
        .replace(/[.,;，；、]+$/, "");
    const doiMatch = raw.match(/10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i);
    if (doiMatch) return doiMatch[0].toLowerCase();
    const cstrMatch = raw.match(/\d{5}\.\d{2}\.[-._;()/:A-Z0-9]+/i);
    if (cstrMatch) return cstrMatch[0].toLowerCase();
    return raw.toLowerCase();
}

function parseIdentifierTokens(input) {
    if (!input) return [];
    return String(input).split(/[\s,，;；、]+/).map((item) => item.trim()).filter(Boolean);
}

function getPayloadSectionKey(schemaKey, language) {
    if (language !== "en") return schemaKey;
    return {
        核心元数据: "Core Metadata",
        数据集元数据: "Dataset Metadata",
        数据论文元数据: "Data Paper Metadata",
        标准文献元数据: "Standard Literature Metadata",
        生态科学数据元数据: "Ecological Science Data Metadata"
    }[schemaKey] || schemaKey;
}

function buildDownloadPayloadForItem(mode, payloadBundle, schema, language) {
    const payload = payloadBundle && payloadBundle[language];
    if (!payload) return null;
    const schemaKey = getSchemaKeyForMode(mode, payloadBundle[language], language);
    const schemaRoot = schema[schemaKey] || schema["核心元数据"];
    const localizedSchemaRoot = translateTree(schemaRoot, language);
    const sectionPayload = getEffectiveSectionPayload(payload, getPayloadSectionKey(schemaKey, language));
    return stripMetadataForDownload(localizedSchemaRoot, sectionPayload);
}

async function downloadJsonFile(mode) {
    const language = state.language;
    const downloadLanguage = DOWNLOAD_LANGUAGE;
    const schema = state.schemaCache[mode] || await loadSchema(mode);
    if (!schema) return updateStatus(getUIText(language).downloadBlocked, "error");

    if (state.sourceMode === "identifier") {
        const tokens = parseIdentifierTokens(state.identifierInput);
        const items = Array.isArray(state.identifierResults) ? state.identifierResults : [];
        if (tokens.length > 1) {
            if (items.length === 0) return updateStatus(getUIText(language).downloadBlocked, "error");
            const buckets = new Map();
            items.forEach((item) => {
                const key = normalizeIdentifierToken(item && item.identifier);
                if (!key) return;
                if (!buckets.has(key)) buckets.set(key, []);
                buckets.get(key).push(item);
            });

            const lines = tokens.map((token) => {
                const key = normalizeIdentifierToken(token);
                const bucket = key ? buckets.get(key) : null;
                const item = bucket && bucket.length > 0 ? bucket.shift() : null;
                if (!item || item.status !== "ok" || !isObject(item.payload)) return "";
                const downloadPayload = buildDownloadPayloadForItem(mode, item.payload, schema, downloadLanguage);
                if (!downloadPayload) return "";
                return JSON.stringify({
                    identifier: item.identifier ?? null,
                    type: item.type ?? null,
                    resolved_url: item.resolved_url ?? null,
                    source: item.source ?? null,
                    payload: downloadPayload,
                    updated_at: item.updated_at ?? null
                });
            });
            const blob = new Blob([lines.join("\n")], { type: "application/jsonl;charset=utf-8" });
            const link = document.createElement("a");
            link.href = URL.createObjectURL(blob);
            link.download = `identifiers-${mode}-${downloadLanguage}.jsonl`;
            link.click();
            URL.revokeObjectURL(link.href);
            return;
        }
    }

    const payloadBundle = state.resultCache[mode];
    const downloadPayload = buildDownloadPayloadForItem(mode, payloadBundle, schema, downloadLanguage);
    if (!downloadPayload) return updateStatus(getUIText(language).downloadBlocked, "error");

    const blob = new Blob([JSON.stringify(downloadPayload, null, 2)], { type: "application/json;charset=utf-8" });
    const link = document.createElement("a");
    link.href = URL.createObjectURL(blob);
    link.download = `${mode}-${downloadLanguage}-metadata.json`;
    link.click();
    URL.revokeObjectURL(link.href);
}

function updateStaticText() {
    const language = state.language;
    const ui = getUIText(language);

    document.getElementById("startTitle").textContent = ui.startTitle;
    document.getElementById("startDescription").textContent = ui.startDescription;
    document.getElementById("brandHomeButton").textContent = ui.startTitle;
    document.getElementById("domainToCoreTitle").textContent = ui.domainToCoreTitle;
    document.getElementById("domainToCoreHint").textContent = ui.domainToCoreHint;
    document.getElementById("coreToDomainTitle").textContent = ui.coreToDomainTitle;
    document.getElementById("coreToDomainHint").textContent = ui.coreToDomainHint;
    document.getElementById("chooseUrlLabel").textContent = ui.chooseUrlLabel;
    document.getElementById("chooseUrlHint").textContent = ui.chooseUrlHint;
    document.getElementById("chooseUploadLabel").textContent = ui.chooseUploadLabel;
    document.getElementById("chooseUploadHint").textContent = ui.chooseUploadHint;
    document.getElementById("chooseIdentifierLabel").textContent = ui.chooseIdentifierLabel;
    document.getElementById("chooseIdentifierHint").textContent = ui.chooseIdentifierHint;
    document.getElementById("extensionTitle").textContent = ui.extensionTitle;
    document.getElementById("uploadTitle").textContent = ui.uploadTitle;
    const uploadExampleJson = document.getElementById("uploadExampleJson");
    const uploadExampleButton = document.getElementById("uploadExampleButton");
    uploadExampleJson.textContent = UPLOAD_EXAMPLE_JSON;
    uploadExampleButton.textContent = uploadExampleJson.hidden ? ui.uploadExampleButton : ui.uploadExampleButtonHide;
    document.getElementById("urlTitle").textContent = ui.urlTitle;
    document.getElementById("urlDescription").textContent = ui.urlDescription;
    document.getElementById("urlInput").setAttribute("placeholder", ui.urlPlaceholder);
    document.getElementById("confirmUrlButton").textContent = ui.confirmUrlButton;
    document.getElementById("clearUrlButton").textContent = ui.clearUrlButton;
    document.getElementById("identifierTitle").textContent = ui.identifierTitle;
    document.getElementById("identifierDescription").textContent = ui.identifierDescription;
    document.getElementById("identifierInput").setAttribute("placeholder", ui.identifierPlaceholder);
    document.getElementById("confirmIdentifierButton").textContent = ui.confirmIdentifierButton;
    document.getElementById("clearIdentifierButton").textContent = ui.clearIdentifierButton;
    document.getElementById("identifierSelectLabel").textContent = ui.identifierSelectLabel;
    document.getElementById("refreshButton").textContent = ui.refreshTitle;
    document.getElementById("downloadButton").textContent = ui.downloadTitle;
    document.getElementById("analysisHomeButton").textContent = ui.homeTitle;
    document.getElementById("openApiDocsButton").textContent = ui.openApiDocsTitle;
    document.getElementById("apiDocsTitle").textContent = ui.apiDocsTitle;
    document.getElementById("apiDocsSubtitle").textContent = ui.apiDocsSubtitle;
    document.getElementById("closeApiDocsButton").textContent = ui.closeLogsTitle;
    document.getElementById("openLogsButton").textContent = ui.openLogsTitle;
    document.getElementById("closeLogsButton").textContent = ui.closeLogsTitle;
    document.getElementById("homeButton").setAttribute("aria-label", ui.homeTitle);
    document.getElementById("homeButton").setAttribute("title", ui.homeTitle);
    document.getElementById("brandHomeButton").setAttribute("aria-label", ui.homeTitle);
    document.getElementById("brandHomeButton").setAttribute("title", ui.homeTitle);
    document.querySelector(".mode-switcher").setAttribute("aria-label", ui.modeSwitcherLabel);

    const selectedFileName = document.getElementById("selectedFileName");
    selectedFileName.textContent = state.uploadedFile ? `${ui.selectedFilePrefix}${state.uploadedFile.name}` : ui.selectedFileEmpty;

    const chooseUrlButton = document.getElementById("chooseUrlButton");
    const chooseUploadButton = document.getElementById("chooseUploadButton");
    const chooseIdentifierButton = document.getElementById("chooseIdentifierButton");
    chooseUrlButton.classList.toggle("primary", state.sourceMode === "url");
    chooseUrlButton.classList.toggle("secondary", state.sourceMode !== "url");
    chooseUploadButton.classList.toggle("primary", state.sourceMode === "upload");
    chooseUploadButton.classList.toggle("secondary", state.sourceMode !== "upload");
    chooseIdentifierButton.classList.toggle("primary", state.sourceMode === "identifier");
    chooseIdentifierButton.classList.toggle("secondary", state.sourceMode !== "identifier");

    setUploadPanelState();
    setAnalysisVisibility();
    renderIdentifierSelector();

    const commonButton = document.querySelector('.mode-button[data-mode="common"]');
    const domainButton = document.querySelector('.mode-button[data-mode="domain"]');
    commonButton.textContent = MODE_LABELS.common[language];
    domainButton.textContent = MODE_LABELS.domain[language];

    const langZhButton = document.getElementById("langZhButton");
    const langEnButton = document.getElementById("langEnButton");
    langZhButton.classList.toggle("active", language === "zh");
    langZhButton.textContent = ui.languageZh;
    langEnButton.classList.toggle("active", language === "en");
    langEnButton.textContent = ui.languageEn;
    if (!document.getElementById("apiDocsWorkspace").hidden) renderApiDocs();
    if (!document.getElementById("logWorkspace").hidden) renderLogs();
}

function clearAnalysisView() {
    document.getElementById("metadataRoot").innerHTML = "";
    document.getElementById("extensionInfo").textContent = getUIText().waiting;
    document.getElementById("extensionInfo").classList.add("empty");
    document.getElementById("modeTitle").textContent = MODE_LABELS.common[state.language];
    document.getElementById("lastUpdated").textContent = "";
}

async function refreshCurrentMode() {
    if (state.isRefreshing) {
        return;
    }
    state.isRefreshing = true;
    const mode = state.mode;
    try {
        await loadModeSchema(mode);
        if (state.sourceMode === "upload") {
            await requestMetadataForUploadedFile(mode);
            state.uploadResultReady = true;
        } else if (state.sourceMode === "identifier") {
            await requestMetadataFromIdentifiers(mode);
            state.identifierResultReady = true;
        } else if (state.sourceMode === "url") {
            await requestMetadataFromUrl(mode);
            state.urlResultReady = true;
        } else {
            return;
        }
        setAnalysisVisibility();
        renderMode(mode);
        updateStatus(getUIText().success, "success");
        setTimeout(() => updateStatus("", "info"), 1200);
    } catch (error) {
        console.error(error);
        updateStatus(`${getUIText().errorPrefix}${error.message}`, "error");
    } finally {
        state.isRefreshing = false;
    }
}

function setMode(mode) {
    if (mode === state.mode) return;
    state.mode = mode;
    document.querySelectorAll(".mode-button").forEach((item) => {
        item.classList.toggle("active", item.dataset.mode === mode);
    });
    if (state.resultCache.common || state.resultCache.domain) {
        renderMode(mode);
        return;
    }
    refreshCurrentMode();
}

function selectSourceMode(sourceMode) {
    activateSourceMode(sourceMode);
    document.getElementById("pageHero").hidden = true;
    document.getElementById("startScreen").hidden = true;
    document.getElementById("logWorkspace").hidden = true;
    document.getElementById("apiDocsWorkspace").hidden = true;
    document.getElementById("analysisWorkspace").hidden = false;
    state.uploadResultReady = false;
    state.identifierResultReady = false;
    state.identifierResults = [];
    state.currentIdentifierIndex = 0;
    state.urlResultReady = false;
    state.uploadedFile = null;
    state.uploadedText = "";
    state.uploadedTitle = "";

    updateStaticText();
    clearAnalysisView();

    if (state.resultCache.common || state.resultCache.domain) renderMode(state.mode);
    updateStatus("", "info");
}

function handleUploadSelection(file) {
    if (!file) return;
    state.uploadedFile = file;
    state.uploadedText = "";
    state.uploadedTitle = file.name;
    state.uploadResultReady = false;
    updateStaticText();
}

function clearUrlInput() {
    state.urlInput = "";
    state.urlResultReady = false;
    state.resultCache = getSourceResultCache();
    delete state.resultCache.common;
    delete state.resultCache.domain;
    document.getElementById("urlInput").value = "";
    clearAnalysisView();
    updateStaticText();
    updateStatus("", "info");
}

async function confirmUrlAndAnalyze() {
    state.urlInput = document.getElementById("urlInput").value.trim();
    state.resultCache = getSourceResultCache();
    delete state.resultCache.common;
    delete state.resultCache.domain;
    state.urlResultReady = false;
    await refreshCurrentMode();
}

async function confirmUploadAndAnalyze() {
    if (!state.uploadedFile) return;
    await refreshCurrentMode();
}

async function confirmIdentifierAndAnalyze() {
    state.identifierInput = document.getElementById("identifierInput").value.trim();
    state.identifierResultReady = false;
    updateStaticText();
    await refreshCurrentMode();
}

function clearIdentifierInput() {
    state.identifierInput = "";
    state.identifierResultReady = false;
    state.identifierResults = [];
    state.currentIdentifierIndex = 0;
    state.resultCache = getSourceResultCache();
    delete state.resultCache.common;
    delete state.resultCache.domain;
    document.getElementById("identifierInput").value = "";
    clearAnalysisView();
    updateStaticText();
    updateStatus("", "info");
}

function reselectUploadFile() {
    state.uploadedFile = null;
    state.uploadedText = "";
    state.uploadedTitle = "";
    state.uploadResultReady = false;
    updateStaticText();
    document.getElementById("fileInput").click();
}

function setLanguage(language) {
    if (language === state.language) {
        updateStaticText();
        return;
    }
    state.language = language;
    state.logResultLanguage = language === "en" ? "en" : "zh";
    updateStaticText();
    if (state.resultCache.common || state.resultCache.domain) renderMode(state.mode);
}

function bindEvents() {
    document.getElementById("homeButton").addEventListener("click", goHome);
    document.getElementById("brandHomeButton").addEventListener("click", goHome);
    document.getElementById("analysisHomeButton").addEventListener("click", goHome);
    document.getElementById("chooseUrlButton").addEventListener("click", () => selectSourceMode("url"));
    document.getElementById("chooseUploadButton").addEventListener("click", () => selectSourceMode("upload"));
    document.getElementById("chooseIdentifierButton").addEventListener("click", () => selectSourceMode("identifier"));

    document.querySelectorAll(".mode-button").forEach((button) => {
        button.addEventListener("click", () => setMode(button.dataset.mode));
    });
    document.querySelectorAll(".lang-button").forEach((button) => {
        button.addEventListener("click", () => setLanguage(button.dataset.language));
    });

    document.getElementById("refreshButton").addEventListener("click", refreshCurrentMode);
    document.getElementById("downloadButton").addEventListener("click", async () => downloadJsonFile(state.mode));
    document.getElementById("openApiDocsButton").addEventListener("click", showApiDocs);
    document.getElementById("closeApiDocsButton").addEventListener("click", goHome);
    document.getElementById("openLogsButton").addEventListener("click", showLogs);
    document.getElementById("closeLogsButton").addEventListener("click", goHome);
    document.getElementById("clearLogsButton").addEventListener("click", () => {
        state.conversionLogs = [];
        state.selectedLogId = null;
        saveConversionLogs();
        renderLogs();
    });
    document.getElementById("uploadButton").addEventListener("click", () => {
        if (state.sourceMode !== "upload") selectSourceMode("upload");
        document.getElementById("fileInput").click();
    });
    document.getElementById("uploadExampleButton").addEventListener("click", () => {
        const example = document.getElementById("uploadExampleJson");
        example.hidden = !example.hidden;
        updateStaticText();
    });
    document.getElementById("confirmUploadButton").addEventListener("click", confirmUploadAndAnalyze);
    document.getElementById("reselectUploadButton").addEventListener("click", reselectUploadFile);
    document.getElementById("confirmUrlButton").addEventListener("click", confirmUrlAndAnalyze);
    document.getElementById("clearUrlButton").addEventListener("click", clearUrlInput);
    document.getElementById("confirmIdentifierButton").addEventListener("click", confirmIdentifierAndAnalyze);
    document.getElementById("clearIdentifierButton").addEventListener("click", clearIdentifierInput);
    document.getElementById("identifierSelect").addEventListener("change", (event) => {
        const nextIndex = Number(event.target.value);
        state.currentIdentifierIndex = Number.isNaN(nextIndex) ? 0 : nextIndex;
        applyIdentifierItemToCache();
        renderMode(state.mode);
    });
    document.getElementById("urlInput").addEventListener("input", (event) => {
        state.urlInput = event.target.value;
        state.urlResultReady = false;
    });
    document.getElementById("identifierInput").addEventListener("input", (event) => {
        state.identifierInput = event.target.value;
        state.identifierResultReady = false;
        state.identifierResults = [];
        state.currentIdentifierIndex = 0;
        state.resultCache = getSourceResultCache();
        delete state.resultCache.common;
        delete state.resultCache.domain;
        clearAnalysisView();
        setAnalysisVisibility();
        renderIdentifierSelector();
    });
    document.getElementById("fileInput").addEventListener("change", (event) => {
        const file = (event.target.files || [])[0];
        handleUploadSelection(file);
        event.target.value = "";
    });
}

document.addEventListener("DOMContentLoaded", async () => {
    loadConversionLogs();
    bindEvents();
    updateStaticText();
    try {
        await loadModeSchema("common");
        await loadModeSchema("domain");
        activateSourceMode("url");
        state.sourceMode = "url";
        setAnalysisVisibility();
        if (window.location.hash === "#api-docs") {
            showApiDocs();
        } else {
            goHome();
        }
    } catch (error) {
        console.error(error);
        updateStatus(`${getUIText(state.language).initErrorPrefix}${error.message}`, "error");
    }
});
