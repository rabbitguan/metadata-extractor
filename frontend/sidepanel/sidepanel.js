const BACKEND_QUERY_URL = 'http://127.0.0.1:4000/query';
const BACKEND_REGISTER_URL = 'http://127.0.0.1:4000/register';
const HISTORY_LOOKUP_URL = 'http://127.0.0.1:4000/history/lookup';
const DOWNLOAD_LANGUAGE = 'en';
const CONVERSION_LOG_STORAGE_KEY = 'metadata_conversion_logs_v1';
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

const LABEL_TRANSLATIONS_EN = {
    资源类型候选列表: 'Resource Type Candidates',
    类型名称: 'Type Name',
    英文类型: 'English Type',
    领域元数据: 'Domain Metadata',
    核心元数据: 'Core Metadata',
    数据集元数据: 'Dataset Metadata',
    数据论文元数据: 'Data Paper Metadata',
    标准文献元数据: 'Standard Literature Metadata',
    生态科学数据元数据: 'Ecological Science Data Metadata',
    数据集基本信息: 'Dataset Basic Information',
    数据集出版信息: 'Dataset Publication Information',
    数据集服务信息: 'Dataset Service Information',
    数据论文内容信息: 'Data Paper Content Information',
    数据论文出版信息: 'Data Paper Publication Information',
    数据论文服务信息: 'Data Paper Service Information',
    共享方式: 'Sharing Details',
    提供方信息: 'Provider Information',
    服务方信息: 'Service Provider Information',
    范围: 'Scope',
    数据集作者: 'Dataset Authors',
    数据论文作者: 'Data Paper Authors',
    标识符: 'Identifier',
    标题: 'titles',
    CSTR标识符: 'identifier',
    创建者: 'creators',
    发布机构: 'publisher',
    发布日期: 'publish_date',
    描述: 'descriptions',
    关键词: 'keywords',
    学科: 'subjects',
    语言: 'language',
    贡献者: 'contributors',
    替代标识符: 'alternative_identifiers',
    关联标识符: 'related_identifiers',
    权限: 'rights',
    资助者: 'funders',
    版本: 'version',
    资源链接: 'urls',
    资源类型: 'ResourceType',
    资源名称: 'Resource Name',
    生成日期: 'Generation Date',
    注册日期: 'Registration Date',
    最新发布日期: 'Latest Release Date',
    资源类型判定: 'Resource Type Classification',
    领域判定: 'Domain Classification',
    学科分类: 'Discipline Classification',
    主题分类: 'Subject Classification',
    知识产权类别: 'Intellectual Property Type',
    资源使用许可: 'Usage License',
    资源访问地址: 'Resource Access URL',
    共享途径: 'Sharing Channel',
    共享范围: 'Sharing Scope',
    申请流程: 'Application Process',
    提供方名称: 'Provider Name',
    提供方详细地址: 'Provider Address',
    提供方邮政编码: 'Provider Postal Code',
    提供方联系人: 'Provider Contact',
    提供方联系电话: 'Provider Phone',
    提供方电子邮箱: 'Provider Email',
    提供方网站: 'Provider Website',
    服务方名称: 'Service Provider Name',
    服务方详细地址: 'Service Provider Address',
    服务方邮政编码: 'Service Provider Postal Code',
    服务方联系人: 'Service Provider Contact',
    服务方联系电话: 'Service Provider Phone',
    服务方电子邮箱: 'Service Provider Email',
    服务方网站: 'Service Provider Website',
    摘要: 'Abstract',
    时间范围: 'Time Range',
    空间范围: 'Spatial Range',
    语种: 'Language',
    文件内容: 'File Content',
    基金项目: 'Funding Project',
    数据量: 'Data Volume',
    数据格式: 'Data Format',
    作者姓名: 'Author Name',
    工作单位: 'Affiliation',
    电子邮箱: 'Email',
    工作贡献: 'Contribution',
    作者简介: 'Biography',
    出版期刊: 'Journal',
    版本信息: 'Version Information',
    数据集引用格式: 'Dataset Citation',
    数据集共享许可协议: 'Dataset License',
    数据集使用声明: 'Dataset Usage Statement',
    数据集下载地址: 'Dataset Download URL',
    数据论文访问地址: 'Dataset Paper URL',
    引言: 'Introduction',
    数据采集和处理方法: 'Data Collection and Processing Methods',
    数据样本描述: 'Data Sample Description',
    数据质量控制和评估: 'Data Quality Control and Evaluation',
    数据使用方法和建议: 'Data Use Methods and Recommendations',
    参考文献: 'References',
    致谢: 'Acknowledgements',
    收稿日期: 'Received Date',
    同评日期: 'Review Date',
    录用日期: 'Accepted Date',
    数据论文下载地址: 'Data Paper Download URL',
    数据论文共享许可协议: 'Data Paper License',
    数据集访问地址: 'Dataset Access URL',
};

const MODE_LABELS = {
    common: {
        zh: '核心元数据项目表',
        en: 'Core Metadata',
    },
    domain: {
        zh: '领域专用元数据项目表',
        en: 'Domain Metadata',
    },
};

const UI_TEXT = {
    zh: {
        appTitle: '元数据双向映射工具',
        startTitle: '元数据双向映射工具',
        startDescription: '请选择分析方式：领域元数据到核心元数据 / 核心元数据到领域元数据',
        domainToCoreTitle: '领域元数据到核心元数据',
        domainToCoreHint: '从网页内容抽取并映射为核心元数据',
        coreToDomainTitle: '核心元数据到领域元数据',
        coreToDomainHint: '通过标识符解析资源并补全领域元数据',
        openLogsTitle: '转换日志',
        logTitle: '转换日志',
        logSubtitle: '查看最近的转换任务和完整结果',
        logDetailTitle: '转换详情',
        logEmpty: '暂无转换日志',
        logDetailEmpty: '请选择一条转换日志',
        clearLogsTitle: '清空',
        chooseWebLabel: '当前网页',
        chooseWebHint: '提取当前标签页并整理元数据',
        chooseUrlLabel: '输入 URL',
        chooseUrlHint: '输入网页地址后由后端直接抓取分析',
        chooseUploadLabel: '上传数据',
        chooseUploadHint: '上传符合格式要求的 JSON / XML 文件',
        chooseIdentifierLabel: '输入 DOI/CSTR',
        chooseIdentifierHint: '通过编号解析资源并整理元数据',
        uploadTitle: '上传数据文件',
        uploadExampleButton: '查看 JSON 示例格式',
        uploadExampleButtonHide: '收起 JSON 示例格式',
        uploadButton: '选择文件',
        confirmUploadButton: '确认并分析',
        reselectUploadButton: '重新选择',
        urlTitle: '输入 URL',
        urlDescription: '输入一个网页地址，后端会直接抓取并分析',
        urlPlaceholder: 'https://example.com',
        confirmUrlButton: '确认并分析',
        clearUrlButton: '清空',
        reanalyzeUrlButton: '重新分析',
        urlHistoryNote: '本结果来自历史查询数据库。若需基于当前页面重新分析，请点击“重新分析”。',
        uploadHistoryNote: '本结果基于上传文件中的 URL 从历史库加载。如需把上传内容发送给模型并重新分析，请点击“重新分析”。',
        identifierTitle: '输入 DOI/CSTR',
        identifierDescription: '支持单个或多个 DOI / CSTR，多个编号可用换行、空格或逗号分隔',
        identifierPlaceholder: '10.xxxx/example 或 12345.12.123456.123456',
        confirmIdentifierButton: '确认并分析',
        clearIdentifierButton: '清空',
        identifierSelectLabel: '选择标识符',
        identifierErrorPrefix: '解析失败: ',
        selectedFileEmpty: '尚未选择文件',
        selectedFilePrefix: '已选择：',
        modeSwitcherLabel: '元数据模式切换',
        extensionTitle: '扩展信息',
        waiting: '等待提取结果',
        noContent: '未提取到',
        updatedAt: '更新于 ',
        loadingExtract: '正在提取当前页面文字...',
        loadingFile: '正在读取文件内容...',
        loadingIdentifier: '正在解析 DOI/CSTR...',
        loadingSend: '正在分析...',
        downloadBlocked: '当前语言尚未完成提取，无法下载。',
        refreshTitle: '重新加载',
        downloadTitle: '下载',
        languageZh: '中',
        languageEn: 'EN',
        errorPrefix: '提取失败: ',
        initErrorPrefix: '初始化失败: ',
        loadingUrl: '正在抓取 URL 页面...',
    },
    en: {
        appTitle: 'Metadata Bidirectional Mapping Tool',
        startTitle: 'Metadata Bidirectional Mapping Tool',
        startDescription: 'Choose a mapping direction: domain metadata to core metadata / core metadata to domain metadata',
        domainToCoreTitle: 'Domain Metadata to Core Metadata',
        domainToCoreHint: 'Extract page content and map it to core metadata',
        coreToDomainTitle: 'Core Metadata to Domain Metadata',
        coreToDomainHint: 'Resolve identifiers and enrich domain metadata',
        openLogsTitle: 'Conversion Logs',
        logTitle: 'Conversion Logs',
        logSubtitle: 'Review recent conversion tasks and complete results',
        logDetailTitle: 'Conversion Detail',
        logEmpty: 'No conversion logs yet',
        logDetailEmpty: 'Select a conversion log',
        clearLogsTitle: 'Clear',
        chooseWebLabel: 'Current page',
        chooseWebHint: 'Extract the current tab and organize metadata',
        chooseUrlLabel: 'Enter URL',
        chooseUrlHint: 'Submit a web address and let the backend fetch it',
        chooseUploadLabel: 'Upload data',
        chooseUploadHint: 'Upload a formatted JSON / XML file',
        chooseIdentifierLabel: 'Enter DOI/CSTR',
        chooseIdentifierHint: 'Resolve identifiers and organize metadata',
        uploadTitle: 'Upload data file',
        uploadExampleButton: 'View JSON example',
        uploadExampleButtonHide: 'Hide JSON example',
        uploadButton: 'Choose file',
        confirmUploadButton: 'Confirm and analyze',
        reselectUploadButton: 'Choose again',
        urlTitle: 'Enter URL',
        urlDescription: 'Enter a web address and let the backend fetch and analyze it',
        urlPlaceholder: 'https://example.com',
        confirmUrlButton: 'Confirm and analyze',
        clearUrlButton: 'Clear',
        reanalyzeUrlButton: 'Reanalyze',
        urlHistoryNote: 'This result was loaded from history. Click "Reanalyze" to run a fresh analysis on the actual page.',
        uploadHistoryNote: 'This result was loaded from history based on a URL found inside the uploaded file. Click "Reanalyze" to send the uploaded content to the model for a fresh analysis.',
        identifierTitle: 'Enter DOI/CSTR',
        identifierDescription: 'Supports one or more DOI / CSTR identifiers separated by new lines, spaces, or commas',
        identifierPlaceholder: '10.xxxx/example or 12345.12.123456.123456',
        confirmIdentifierButton: 'Confirm and analyze',
        clearIdentifierButton: 'Clear',
        identifierSelectLabel: 'Identifier',
        identifierErrorPrefix: 'Error: ',
        selectedFileEmpty: 'No file selected yet',
        selectedFilePrefix: 'Selected: ',
        modeSwitcherLabel: 'Metadata mode switcher',
        extensionTitle: 'Extension Info',
        waiting: 'Waiting for results',
        noContent: 'Not extracted',
        updatedAt: 'Updated at ',
        loadingExtract: 'Extracting page text...',
        loadingFile: 'Reading file content...',
        loadingIdentifier: 'Resolving DOI/CSTR...',
        loadingSend: 'Sending to the model...',
        downloadBlocked: 'Nothing is ready to download yet.',
        refreshTitle: 'Reload',
        downloadTitle: 'Download',
        languageZh: '中',
        languageEn: 'EN',
        errorPrefix: 'Extraction failed: ',
        initErrorPrefix: 'Initialization failed: ',
        loadingUrl: 'Fetching URL page...',
    },
};

const state = {
    sourceMode: null,
    mode: 'common',
    language: 'zh',
    schemaCache: {},
    resultCacheBySource: {
        web: {},
        url: {},
        upload: {},
        identifier: {},
    },
    resultCache: {},
    lastFetchedAt: null,
    uploadedFile: null,
    uploadedText: '',
    uploadedTitle: '',
    uploadStage: 'idle',
    uploadResultReady: false,
    uploadHistoryUsed: false,
    identifierInput: '',
    identifierResultReady: false,
    identifierResults: [],
    currentIdentifierIndex: 0,
    urlInput: '',
    urlResultReady: false,
    urlHistoryUsed: false,
    currentPageData: null,  // 存储当前提取的页面数据
    conversionLogs: [],
    selectedLogId: null,
    previousWorkspace: 'start',
};

function isObject(value) {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeWhitespace(value) {
    return value.replace(/\s+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
}

function normalizeUrlInput(value) {
    const text = String(value || '').trim();
    if (!text) {
        return '';
    }

    if (/^https?:\/\//i.test(text)) {
        return text;
    }

    if (text.startsWith('//')) {
        return `https:${text}`;
    }

    return `https://${text}`;
}

function getUIText(language = state.language) {
    return UI_TEXT[language] || UI_TEXT.zh;
}

function getSourceKey() {
    return state.sourceMode || 'web';
}

function getSourceResultCache() {
    const sourceKey = getSourceKey();
    if (!state.resultCacheBySource[sourceKey]) {
        state.resultCacheBySource[sourceKey] = {};
    }
    return state.resultCacheBySource[sourceKey];
}

function activateSourceMode(sourceMode) {
    state.sourceMode = sourceMode;
    state.resultCache = getSourceResultCache();
}

function setActiveView(isAnalysisVisible) {
    document.getElementById('startScreen').hidden = isAnalysisVisible;
    document.getElementById('analysisWorkspace').hidden = !isAnalysisVisible;
    document.getElementById('logWorkspace').hidden = true;
}

function loadConversionLogs() {
    try {
        const raw = localStorage.getItem(CONVERSION_LOG_STORAGE_KEY);
        const parsed = JSON.parse(raw || '[]');
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
        web: '当前网页',
        url: 'URL',
        upload: '上传 JSON/XML',
        identifier: 'DOI/CSTR',
        text: '文本',
    }[source] || source || '未知来源';
}

function getLogDisplayTitle(entry) {
    if (!entry) {
        return '';
    }
    if (entry.source === 'upload') {
        return entry.title || '未命名上传文件';
    }
    if (entry.source === 'identifier') {
        return entry.title || entry.identifierInput || 'DOI/CSTR 查询';
    }
    return entry.url || entry.title || '未命名转换任务';
}

function recordConversionLog({ source, mode, strategy, title, url, inputText, payload, identifierInput }) {
    const entry = {
        id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
        createdAt: new Date().toISOString(),
        source,
        mode,
        strategy,
        title: title || '',
        url: url || '',
        identifierInput: identifierInput || '',
        inputPreview: String(inputText || '').slice(0, 1000),
        payload,
    };
    state.conversionLogs = [entry, ...state.conversionLogs].slice(0, MAX_CONVERSION_LOGS);
    state.selectedLogId = entry.id;
    saveConversionLogs();
}

function showLogs() {
    state.previousWorkspace = document.getElementById('analysisWorkspace').hidden ? 'start' : 'analysis';
    document.getElementById('startScreen').hidden = true;
    document.getElementById('analysisWorkspace').hidden = true;
    document.getElementById('logWorkspace').hidden = false;
    renderLogs();
}

function closeLogs() {
    resetToStartScreen();
}

function renderLogs() {
    const ui = getUIText();
    const list = document.getElementById('logList');
    const detail = document.getElementById('logDetail');
    document.getElementById('logTitle').textContent = ui.logTitle;
    document.getElementById('logSubtitle').textContent = ui.logSubtitle;
    document.getElementById('logDetailTitle').textContent = ui.logDetailTitle;
    document.getElementById('clearLogsButton').textContent = ui.clearLogsTitle;

    list.innerHTML = '';
    if (!state.conversionLogs.length) {
        const empty = document.createElement('div');
        empty.className = 'log-item-meta';
        empty.style.padding = '14px';
        empty.textContent = ui.logEmpty;
        list.appendChild(empty);
        detail.className = 'log-detail empty';
        detail.textContent = ui.logDetailEmpty;
        return;
    }

    if (!state.selectedLogId || !state.conversionLogs.some((entry) => entry.id === state.selectedLogId)) {
        state.selectedLogId = state.conversionLogs[0].id;
    }

    state.conversionLogs.forEach((entry) => {
        const button = document.createElement('button');
        button.type = 'button';
        button.className = `log-item${entry.id === state.selectedLogId ? ' active' : ''}`;
        button.addEventListener('click', () => {
            state.selectedLogId = entry.id;
            renderLogs();
        });

        const title = document.createElement('div');
        title.className = 'log-item-title';
        title.textContent = getLogDisplayTitle(entry);

        const meta = document.createElement('div');
        meta.className = 'log-item-meta';
        meta.textContent = `${getSourceLabel(entry.source)} · ${entry.mode || 'common'} · ${new Date(entry.createdAt).toLocaleString('zh-CN', { hour12: false })}`;

        button.append(title, meta);
        list.appendChild(button);
    });

    const selected = state.conversionLogs.find((entry) => entry.id === state.selectedLogId);
    renderLogDetail(selected);
}

function appendLogDetailSection(container, title, value) {
    const section = document.createElement('section');
    section.className = 'log-detail-section';
    const heading = document.createElement('h3');
    heading.textContent = title;
    const pre = document.createElement('pre');
    pre.textContent = typeof value === 'string' ? value : JSON.stringify(value, null, 2);
    section.append(heading, pre);
    container.appendChild(section);
}

function pickLanguagePayload(payload, language) {
    if (!isObject(payload)) {
        return payload || {};
    }
    if (isObject(payload[language])) {
        return filterLocalizedTree(payload[language], language) || {};
    }
    if (Array.isArray(payload.items)) {
        return {
            ...payload,
            items: payload.items.map((item) => {
                if (!isObject(item) || !isObject(item.payload)) {
                    return item;
                }
                const rawPayload = isObject(item.payload[language]) ? item.payload[language] : item.payload;
                return { ...item, payload: filterLocalizedTree(rawPayload, language) || {} };
            }),
        };
    }
    return filterLocalizedTree(payload, language) || {};
}

function renderLogDetail(entry) {
    const ui = getUIText();
    const detail = document.getElementById('logDetail');
    detail.innerHTML = '';
    if (!entry) {
        detail.className = 'log-detail empty';
        detail.textContent = ui.logDetailEmpty;
        return;
    }

    detail.className = 'log-detail';
    appendLogDetailSection(detail, '任务信息', {
        source: getSourceLabel(entry.source),
        mode: entry.mode,
        strategy: entry.strategy,
        title: entry.title,
        url: entry.url,
        identifierInput: entry.identifierInput,
        createdAt: entry.createdAt,
    });
    appendLogDetailSection(detail, '输入预览', entry.inputPreview || '无');
    appendLogDetailSection(detail, '转换结果', pickLanguagePayload(entry.payload || {}, state.language));
}

function setUploadPanelState() {
    const ui = getUIText();
    const uploadIdleState = document.getElementById('uploadIdleState');
    const uploadSelectedState = document.getElementById('uploadSelectedState');
    const uploadButton = document.getElementById('uploadButton');
    const confirmUploadButton = document.getElementById('confirmUploadButton');
    const reselectUploadButton = document.getElementById('reselectUploadButton');

    const hasSelectedFile = Boolean(state.uploadedFile);
    uploadIdleState.hidden = hasSelectedFile;
    uploadSelectedState.hidden = !hasSelectedFile;

    if (uploadButton) {
        uploadButton.hidden = hasSelectedFile;
        uploadButton.textContent = ui.uploadButton;
    }
    if (confirmUploadButton) {
        confirmUploadButton.hidden = !hasSelectedFile;
        confirmUploadButton.textContent = ui.confirmUploadButton;
    }
    if (reselectUploadButton) {
        reselectUploadButton.hidden = !hasSelectedFile;
        reselectUploadButton.textContent = ui.reselectUploadButton;
    }
    const reanalyzeUploadButton = document.getElementById('reanalyzeUploadButton');
    const uploadHistoryNote = document.getElementById('uploadHistoryNote');
    if (reanalyzeUploadButton) {
        reanalyzeUploadButton.hidden = true;
        reanalyzeUploadButton.textContent = ui.reanalyzeUploadButton || ui.reanalyzeUrlButton;
    }
    if (uploadHistoryNote) {
        uploadHistoryNote.hidden = true;
    }
}

function setAnalysisVisibility() {
    const modeSwitcher = document.querySelector('.mode-switcher');
    const analysisContent = document.getElementById('analysisContent');
    const llmRow = document.querySelector('.llm-row');
    const uploadPanel = document.getElementById('uploadPanel');
    const identifierPanel = document.getElementById('identifierPanel');
    const identifierSelector = document.getElementById('identifierSelector');
    const urlPanel = document.getElementById('urlPanel');
    const reanalyzeUrlButton = document.getElementById('reanalyzeUrlButton');

    if (state.sourceMode === 'upload') {
        llmRow.hidden = true;
        uploadPanel.hidden = false;
        identifierPanel.hidden = true;
        urlPanel.hidden = true;
        modeSwitcher.hidden = !state.uploadResultReady;
        analysisContent.hidden = !state.uploadResultReady;
        return;
    }

    if (state.sourceMode === 'identifier') {
        llmRow.hidden = true;
        uploadPanel.hidden = true;
        identifierPanel.hidden = false;
        urlPanel.hidden = true;
        modeSwitcher.hidden = !state.identifierResultReady;
        analysisContent.hidden = !state.identifierResultReady;
        if (identifierSelector) {
            identifierSelector.hidden = !state.identifierResultReady || state.identifierResults.length === 0;
        }
        return;
    }

    if (state.sourceMode === 'url') {
        llmRow.hidden = true;
        uploadPanel.hidden = true;
        identifierPanel.hidden = true;
        urlPanel.hidden = false;
        modeSwitcher.hidden = !state.urlResultReady;
        analysisContent.hidden = !state.urlResultReady;
        if (reanalyzeUrlButton) {
            reanalyzeUrlButton.hidden = true;
        }
        return;
    }

    llmRow.hidden = false;
    uploadPanel.hidden = true;
    identifierPanel.hidden = true;
    urlPanel.hidden = true;
    if (reanalyzeUrlButton) {
        reanalyzeUrlButton.hidden = true;
    }
    modeSwitcher.hidden = false;
    analysisContent.hidden = false;
    if (identifierSelector) {
        identifierSelector.hidden = true;
    }
}

function setUrlReanalyzeButtonVisibility() {
    const button = document.getElementById('reanalyzeUrlButton');
    if (!button) {
        return;
    }
    const note = document.getElementById('urlHistoryNote');
    const shouldShow = state.sourceMode === 'url' && state.urlResultReady && state.urlHistoryUsed;
    button.hidden = !shouldShow;
    if (note) {
        const ui = getUIText();
        note.textContent = shouldShow ? ui.urlHistoryNote : '';
        note.hidden = !shouldShow;
    }
}

function setUploadReanalyzeButtonVisibility() {
    const button = document.getElementById('reanalyzeUploadButton');
    const note = document.getElementById('uploadHistoryNote');
    if (!button || !note) {
        return;
    }

    const shouldShow = state.sourceMode === 'upload' && state.uploadResultReady && state.uploadHistoryUsed;
    button.hidden = !shouldShow;
    const ui = getUIText();
    note.textContent = shouldShow ? ui.uploadHistoryNote : '';
    note.hidden = !shouldShow;
}

function getTranslatedLabel(label, language = state.language) {
    if (language === 'en') {
        return LABEL_TRANSLATIONS_EN[label] || label;
    }

    const reverseMap = Object.fromEntries(
        Object.entries(LABEL_TRANSLATIONS_EN).map(([zhLabel, enLabel]) => [enLabel, zhLabel]),
    );
    return reverseMap[label] || label;
}

const FIELD_VALUE_ALIASES = {
    titles: ['Title', 'Resource Name', '标题'],
    identifier: ['Identifier', 'CSTR标识符', '标识符'],
    creators: ['Creators', 'Author Name', 'Data Paper Authors', 'Dataset Authors', '创建者', '作者姓名'],
    publisher: ['Publisher', '发布机构', '出版机构', '出版单位'],
    publish_date: ['Publication Date', 'Generation Date', 'Received Date', '发布日期', '生成日期'],
    descriptions: ['Description', 'Abstract', '摘要', '描述'],
    keywords: ['Keywords', '关键词'],
    subjects: ['Subjects', 'Discipline Classification', 'Subject Classification', '学科', '学科分类'],
    language: ['Language', '语种', '语言'],
    contributors: ['Contributors', '贡献者'],
    alternative_identifiers: ['Alternative Identifiers', '替代标识符'],
    related_identifiers: ['Related Identifiers', '关联标识符'],
    rights: ['Rights', 'Usage License', '资源使用许可'],
    funders: ['Funders', 'Funding Project', '基金项目', '资助者'],
    version: ['Version', 'Version Information', '版本', '版本信息'],
    urls: ['Resource URL', 'Resource Access URL', 'Dataset Download URL', 'Data Paper Download URL', '资源链接'],
    resource_type: ['ResourceType', 'Resource Type Classification', '资源类型', '资源类型判定'],
    ResourceType: ['resource_type', 'Resource Type Classification', '资源类型'],
    domain_metadata: ['Domain Classification', '领域判定'],
    'Domain Classification': ['domain_metadata', '领域判定'],
    extension_info: ['Extension Info', '扩展信息'],
    'Extension Info': ['extension_info', '扩展信息'],
    标题: ['资源名称', 'Title', 'Resource Name'],
    CSTR标识符: ['标识符', 'Identifier'],
    创建者: ['作者姓名', 'Data Paper Authors', 'Author Name', 'creators'],
    发布机构: ['发布机构', 'Publisher', 'publisher'],
    发布日期: ['发布日期', '生成日期', 'Registration Date', 'Received Date', 'publish_date'],
    描述: ['摘要', 'Abstract', 'descriptions'],
    关键词: ['关键词', 'Keywords', 'keywords'],
    学科: ['学科分类', 'Discipline Classification', 'subjects'],
    语言: ['语种', 'Language', 'language'],
    贡献者: ['contributors'],
    替代标识符: ['alternative_identifiers'],
    关联标识符: ['related_identifiers'],
    权限: ['资源使用许可', 'Usage License', 'rights'],
    资助者: ['funders', '基金项目'],
    版本: ['版本信息', 'version'],
    资源链接: ['资源访问地址', '数据论文下载地址', 'Dataset Download URL', 'Data Paper Download URL', 'urls'],
    资源类型: ['resource_type', '资源类型判定', 'Resource Type Classification', 'ResourceType'],
    Title: ['titles', 'Resource Name', '资源名称'],
    Identifier: ['identifier', 'CSTR标识符', '标识符'],
    Creators: ['creators', 'Authors', 'Author Name', 'Data Paper Authors', 'Dataset Authors', '创建者'],
    Publisher: ['publisher', '发布机构', '出版机构', '出版单位'],
    'Publication Date': ['publish_date', 'Generated Date', 'Received Date', '出版日期', '发布日期'],
    Description: ['descriptions', 'Abstract', '摘要', '描述'],
    Keywords: ['keywords', '关键词'],
    Subjects: ['subjects', 'Discipline Classification', 'Subject Classification', '学科', '学科分类'],
    Language: ['language', '语种', '语言'],
    Contributors: ['contributors', '贡献者'],
    'Alternative Identifiers': ['alternative_identifiers', '替代标识符'],
    'Related Identifiers': ['related_identifiers', '关联标识符'],
    Rights: ['rights', 'Usage License', '资源使用许可'],
    Funders: ['funders', 'Funding Project', '基金项目', '资助者'],
    Version: ['version', 'Version Information', '版本', '版本信息'],
    'Resource URL': ['urls', 'Resource Access URL', 'Dataset Download URL', 'Data Paper Download URL', '资源链接'],
    ResourceType: ['resource_type', 'Resource Type Classification', '资源类型'],
    'Domain Classification': ['domain_metadata', '领域判定'],
    'Extension Info': ['extension_info', '扩展信息'],
    作者姓名: ['Author Name'],
    工作单位: ['Affiliation'],
    电子邮箱: ['Email'],
    工作贡献: ['Contribution'],
    作者简介: ['Biography'],
    数据采集和处理方法: ['Data Collection and Processing Methods'],
    数据论文下载地址: ['Data Paper Download URL', '资源访问地址'],
    数据论文共享许可协议: ['Data Paper License', '资源使用许可'],
    数据论文访问地址: ['数据论文访问地址', 'Data Paper URL'],
    收稿日期: ['Received Date'],
    同评日期: ['Review Date'],
    录用日期: ['Accepted Date'],
    出版期刊: ['Journal'],
};

const DOMAIN_SCHEMA_KEY_MAP = {
    数据论文元数据: ['数据论文内容信息', '数据论文出版信息', '数据论文服务信息'],
    数据集元数据: ['数据集基本信息', '数据集出版信息', '数据集服务信息'],
    标准文献元数据: ['标准文献信息', '标准文献内容信息', '标准文献出版信息', '标准文献服务信息'],
    生态科学数据元数据: ['生态科学数据基本信息', '生态科学数据出版信息', '生态科学数据服务信息'],
};

function findValueByKeyOrAlias(payload, key) {
    if (!isObject(payload)) {
        return undefined;
    }

    if (Object.prototype.hasOwnProperty.call(payload, key)) {
        return payload[key];
    }

    const aliases = FIELD_VALUE_ALIASES[key] || [];
    for (const alias of aliases) {
        if (Object.prototype.hasOwnProperty.call(payload, alias)) {
            return payload[alias];
        }
    }

    for (const value of Object.values(payload)) {
        if (isObject(value)) {
            const nested = findValueByKeyOrAlias(value, key);
            if (typeof nested !== 'undefined') {
                return nested;
            }
        } else if (Array.isArray(value)) {
            for (const item of value) {
                if (isObject(item)) {
                    const nested = findValueByKeyOrAlias(item, key);
                    if (typeof nested !== 'undefined') {
                        return nested;
                    }
                }
            }
        }
    }

    return undefined;
}

function getFieldLookupKeys(key) {
    const aliases = FIELD_VALUE_ALIASES[key] || [];
    return [key, ...aliases];
}

function translateTree(node, language = state.language) {
    if (!isObject(node)) {
        return node;
    }

    const translated = {};
    Object.entries(node).forEach(([key, value]) => {
        const translatedKey = getTranslatedLabel(key, language);
        translated[translatedKey] = isObject(value) ? translateTree(value, language) : value;
    });
    return translated;
}

function normalizeObjectKeys(value, language = state.language) {
    if (Array.isArray(value)) {
        return value.map((item) => normalizeObjectKeys(item, language));
    }

    if (!isObject(value)) {
        return value;
    }

    const normalized = {};
    Object.entries(value).forEach(([key, nestedValue]) => {
        const translatedKey = getTranslatedLabel(key, language);
        normalized[translatedKey] = normalizeObjectKeys(nestedValue, language);
    });
    return normalized;
}

function flattenStructuredValue(value, prefix = '', lines = []) {
    if (value === null || typeof value === 'undefined') {
        return lines;
    }

    if (Array.isArray(value)) {
        if (prefix) {
            lines.push(`${prefix}:`);
        }
        value.forEach((item, index) => {
            const nextPrefix = prefix ? `${prefix}[${index}]` : `[${index}]`;
            flattenStructuredValue(item, nextPrefix, lines);
        });
        return lines;
    }

    if (isObject(value)) {
        const entries = Object.entries(value);
        if (prefix && entries.length === 0) {
            lines.push(`${prefix}: {}`);
            return lines;
        }

        entries.forEach(([key, nestedValue]) => {
            const nextPrefix = prefix ? `${prefix}.${key}` : key;
            flattenStructuredValue(nestedValue, nextPrefix, lines);
        });
        return lines;
    }

    const scalarText = String(value).replace(/\s+/g, ' ').trim();
    if (scalarText) {
        lines.push(prefix ? `${prefix}: ${scalarText}` : scalarText);
    }
    return lines;
}

async function readFileAsText(file) {
    const rawText = await file.text();
    const trimmedText = rawText.trim();
    const lowerName = String(file.name || '').toLowerCase();

    if (!trimmedText) {
        return '';
    }

    if (!lowerName.endsWith('.json') && !lowerName.endsWith('.xml')) {
        throw new Error('仅支持 JSON / XML 文件');
    }

    if (lowerName.endsWith('.json')) {
        try {
            JSON.parse(rawText);
        } catch (error) {
            throw new Error('JSON 格式不合法，请按页面提示的 core/domain 结构上传');
        }
    }

    return rawText;
}

function getModeSchemaKey(mode, payload = null) {
    if (mode !== 'domain') {
        return '核心元数据';
    }

    const coreKey = payload && typeof payload === 'object'
        ? (payload['核心元数据'] || payload['Core Metadata'] || payload)
        : null;

    if (isObject(coreKey)) {
        for (const [schemaKey, sectionKeys] of Object.entries(DOMAIN_SCHEMA_KEY_MAP)) {
            if (sectionKeys.some((sectionKey) => Object.prototype.hasOwnProperty.call(coreKey, sectionKey))) {
                return schemaKey;
            }
        }
    }

    return '核心元数据';
}

function getLocalizedModeTitle(mode, language = state.language) {
    return (MODE_LABELS[mode] && MODE_LABELS[mode][language]) || MODE_LABELS.common[language] || mode;
}

function getCacheKey(mode = state.mode) {
    return mode;
}

function getExtensionKey(language = state.language) {
    return 'extension_info';
}

function getDomainClassificationKey(language = state.language) {
    return 'domain_metadata';
}

function getResourceTypeClassificationKey(language = state.language) {
    return 'resource_type';
}

function getFieldValue(field) {
    if (field === null || typeof field === 'undefined') {
        return '';
    }

    if (isObject(field) && Object.prototype.hasOwnProperty.call(field, 'value')) {
        return field.value;
    }

    return field;
}

function getSchemaKeyFromClassification(classification, language = state.language) {
    const normalized = String(classification || '').trim();
    if (!normalized) {
        return '核心元数据';
    }

    if (language === 'en') {
        return {
            'Core Metadata': '核心元数据',
            'Dataset Metadata': '数据集元数据',
            'Data Paper Metadata': '数据论文元数据',
        }[normalized] || '核心元数据';
    }

    return {
        '核心元数据': '核心元数据',
        '数据集元数据': '数据集元数据',
        '数据论文元数据': '数据论文元数据',
    }[normalized] || '核心元数据';
}

function getSchemaKeyFromResourceType(resourceType, language = state.language) {
    const normalized = String(resourceType || '').trim();
    if (!normalized) {
        return null;
    }

    if (language === 'en') {
        return {
            Dataset: '数据集元数据',
            'Data Paper': '数据论文元数据',
            Other: '核心元数据',
        }[normalized] || null;
    }

    return {
        数据集: '数据集元数据',
        数据论文: '数据论文元数据',
        其他: '核心元数据',
    }[normalized] || null;
}

function getSchemaKeyForMode(mode, payload, language = state.language) {
    if (mode === 'domain') {
        const coreKey = language === 'en' ? 'Core Metadata' : '核心元数据';
        const coreData = isObject(payload)
            ? unwrapMetadataSection(payload[coreKey] || payload['核心元数据'] || payload['Core Metadata'] || payload)
            : null;
        const domainSectionMap = language === 'en'
            ? {
                'Dataset Metadata': DOMAIN_SCHEMA_KEY_MAP['数据集元数据'],
                'Data Paper Metadata': DOMAIN_SCHEMA_KEY_MAP['数据论文元数据'],
                'Standard Literature Metadata': DOMAIN_SCHEMA_KEY_MAP['标准文献元数据'],
                'Ecological Science Data Metadata': DOMAIN_SCHEMA_KEY_MAP['生态科学数据元数据'],
            }
            : DOMAIN_SCHEMA_KEY_MAP;

        if (isObject(coreData)) {
            const classificationKey = 'domain_metadata';
            const classification = findValueByKeyOrAlias(coreData, classificationKey);
            if (typeof classification === 'string' && classification.trim()) {
                if (Object.prototype.hasOwnProperty.call(domainSectionMap, classification)) {
                    return language === 'en' ? {
                        'Dataset Metadata': '数据集元数据',
                        'Data Paper Metadata': '数据论文元数据',
                        'Standard Literature Metadata': '标准文献元数据',
                        'Ecological Science Data Metadata': '生态科学数据元数据',
                    }[classification] : classification;
                }
            }

            const schemaKeyFromResourceType = getSchemaKeyFromResourceType(findValueByKeyOrAlias(coreData, 'resource_type'), language);
            if (schemaKeyFromResourceType) {
                return schemaKeyFromResourceType;
            }

            for (const [schemaKey, sectionKeys] of Object.entries(DOMAIN_SCHEMA_KEY_MAP)) {
                if (sectionKeys.some((sectionKey) => Object.prototype.hasOwnProperty.call(coreData, sectionKey))) {
                    return schemaKey;
                }
            }
        }
    }

    return '核心元数据';
}

function getEffectiveSectionPayload(payload, schemaKey) {
    if (!isObject(payload)) {
        return {};
    }

    const directSection = payload[schemaKey];
    if (isObject(directSection)) {
        return unwrapMetadataSection(directSection);
    }

    const sectionAliases = {
        '核心元数据': ['核心元数据', 'Core Metadata'],
        'Core Metadata': ['Core Metadata', '核心元数据'],
        '数据集元数据': ['数据集元数据', 'Dataset Metadata'],
        'Dataset Metadata': ['Dataset Metadata', '数据集元数据'],
        '数据论文元数据': ['数据论文元数据', 'Data Paper Metadata'],
        'Data Paper Metadata': ['Data Paper Metadata', '数据论文元数据'],
        '标准文献元数据': ['标准文献元数据', 'Standard Literature Metadata'],
        'Standard Literature Metadata': ['Standard Literature Metadata', '标准文献元数据'],
        '生态科学数据元数据': ['生态科学数据元数据', 'Ecological Science Data Metadata'],
        'Ecological Science Data Metadata': ['Ecological Science Data Metadata', '生态科学数据元数据'],
    }[schemaKey] || [schemaKey];
    for (const sectionKey of sectionAliases) {
        if (isObject(payload[sectionKey])) {
            return unwrapMetadataSection(payload[sectionKey]);
        }
    }

    return payload;
}

function unwrapMetadataSection(section) {
    if (isObject(section) && Array.isArray(section.metadatas) && isObject(section.metadatas[0])) {
        return section.metadatas[0];
    }
    return section;
}

function findValueInPayload(payload, targetKey) {
    if (!isObject(payload)) return undefined;

    if (Object.prototype.hasOwnProperty.call(payload, targetKey)) {
        return payload[targetKey];
    }

    for (const [k, v] of Object.entries(payload)) {
        if (isObject(v)) {
            const found = findValueInPayload(v, targetKey);
            if (typeof found !== 'undefined') return found;
        } else if (Array.isArray(v)) {
            for (const item of v) {
                if (isObject(item)) {
                    const found = findValueInPayload(item, targetKey);
                    if (typeof found !== 'undefined') return found;
                }
            }
        }
    }

    return undefined;
}

function getSchemaRoot(mode) {
    const schema = state.schemaCache[mode];
    if (!schema) {
        return null;
    }

    return schema[getModeSchemaKey(mode)] || schema['核心元数据'];
}

function updateStatus(message, type = 'idle') {
    const status = document.getElementById('status');
    status.textContent = message;
    status.className = `status ${type}`;
    status.hidden = !message;
}

async function loadSchema(mode) {
    if (state.schemaCache[mode]) {
        return state.schemaCache[mode];
    }

    const response = await fetch(chrome.runtime.getURL('standard.json'));
    if (!response.ok) {
        throw new Error(`无法加载标准 JSON: ${response.status}`);
    }

    const schema = await response.json();
    state.schemaCache[mode] = schema;
    return schema;
}

async function loadModeSchema(mode) {
    const schema = await loadSchema(mode);
    const schemaRoot = schema[getModeSchemaKey(mode)] || schema['核心元数据'];
    if (!schemaRoot) {
        throw new Error(`标准 JSON 中未找到 ${getModeSchemaKey(mode)}`);
    }
    return schemaRoot;
}

async function collectPageTextFromTab(tabId) {
    const [result] = await chrome.scripting.executeScript({
        target: { tabId },
        func: () => {
            const chunks = [];
            const append = (value) => {
                if (!value) {
                    return;
                }
                const text = String(value).replace(/\s+/g, ' ').trim();
                if (text) {
                    chunks.push(text);
                }
            };

            append(document.title);
            append(document.body ? document.body.innerText : '');

            document.querySelectorAll('meta[name="description"], meta[property="og:description"]').forEach((element) => {
                append(element.getAttribute('content'));
            });

            document.querySelectorAll('[alt], [title], [aria-label], [placeholder]').forEach((element) => {
                append(element.getAttribute('alt'));
                append(element.getAttribute('title'));
                append(element.getAttribute('aria-label'));
                append(element.getAttribute('placeholder'));
            });

            document.querySelectorAll('input, textarea, select').forEach((element) => {
                if (element.value) {
                    append(element.value);
                }
                if (element.placeholder) {
                    append(element.placeholder);
                }
            });

            return {
                text: chunks.join('\n'),
                html: document.documentElement ? document.documentElement.outerHTML : '',
                title: document.title || '',
                url: location.href,
            };
        },
    });

    if (!result || !result.result) {
        throw new Error('未能提取页面文本');
    }

    const pageData = result.result;
    return {
        text: normalizeWhitespace(pageData.text || ''),
        html: pageData.html || '',
        title: pageData.title || '',
        url: pageData.url || '',
    };
}

async function extractPageText() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs.length || !tabs[0].id) {
        throw new Error('未找到当前活动标签页');
    }

    return collectPageTextFromTab(tabs[0].id);
}

async function waitForTabComplete(tabId, timeoutMs = 20000) {
    return new Promise((resolve, reject) => {
        let settled = false;

        const cleanup = () => {
            if (settled) {
                return;
            }
            settled = true;
            clearTimeout(timeoutHandle);
            chrome.tabs.onUpdated.removeListener(listener);
        };

        const listener = (updatedTabId, changeInfo) => {
            if (updatedTabId === tabId && changeInfo.status === 'complete') {
                cleanup();
                resolve();
            }
        };

        const timeoutHandle = setTimeout(() => {
            cleanup();
            reject(new Error('URL 页面加载超时'));
        }, timeoutMs);

        chrome.tabs.onUpdated.addListener(listener);

        chrome.tabs.get(tabId)
            .then((tab) => {
                if (tab && tab.status === 'complete') {
                    cleanup();
                    resolve();
                }
            })
            .catch(() => {});
    });
}

async function requestMetadataFromText(mode, text, { title = '', url = '', html = '', strategy = 'auto', source = 'text', forceReanalyze = false } = {}) {
    const language = state.language;
    if (!text) {
        throw new Error('没有可分析的内容');
    }

    updateStatus(getUIText(language).loadingSend, 'loading');
    const response = await fetch(BACKEND_REGISTER_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            text,
            html,
            url,
            title,
            source,
            mode,
            strategy,
            force_reanalyze: forceReanalyze,
        }),
    });

    if (!response.ok) {
        throw new Error(`HTTP 错误: ${response.status}`);
    }

    const payload = await response.json();
    applyMetadataResponse(payload, mode);
    recordConversionLog({
        source,
        mode,
        strategy,
        title,
        url,
        inputText: text,
        payload,
    });
    return payload;
}

function applyMetadataResponse(payload, mode) {
    const nextPayload = isObject(payload) ? payload : {};
    state.resultCache.common = nextPayload;
    state.resultCache.domain = nextPayload;
    state.resultCache[getCacheKey(mode)] = nextPayload;
    state.lastFetchedAt = new Date();
    // mark both URL and upload history flags depending on payload origin
    const fromHistory = Boolean(nextPayload.from_history);
    state.urlHistoryUsed = fromHistory;
    state.uploadHistoryUsed = fromHistory;
    // ensure upload reanalyze button visibility updates when payload origin changes
    try {
        setUploadReanalyzeButtonVisibility();
    } catch (e) {}
    return nextPayload;
}

async function lookupHistoryByUrl(url, text = '') {
    const lookupUrl = new URL(HISTORY_LOOKUP_URL);
    lookupUrl.searchParams.set('url', url || '');
    if (text) {
        lookupUrl.searchParams.set('text', text);
    }

    const response = await fetch(lookupUrl.toString(), {
        method: 'GET',
    });

    if (!response.ok) {
        throw new Error(`历史查询失败: ${response.status}`);
    }

    return response.json();
}

async function requestMetadataFromUrl(mode, { forceReanalyze = false } = {}) {
    const language = state.language;
    const url = normalizeUrlInput(state.urlInput || '');
    if (!url) {
        throw new Error('请输入网页 URL');
    }

    updateStatus(getUIText(language).loadingUrl, 'loading');
    const cachedResult = forceReanalyze ? null : await lookupHistoryByUrl(url);
    if (cachedResult && cachedResult.found) {
        state.urlResultReady = true;
        applyMetadataResponse(cachedResult, mode);
        recordConversionLog({
            source: 'url',
            mode,
            strategy: 'history',
            title: cachedResult.history_page_title || '',
            url,
            inputText: '',
            payload: cachedResult,
        });
        setAnalysisVisibility();
        setUrlReanalyzeButtonVisibility();
        renderMode(mode);
        updateStatus('', 'idle');
        return cachedResult;
    }

    const tempTab = await chrome.tabs.create({
        url,
        active: false,
    });

    try {
        if (!tempTab || !tempTab.id) {
            throw new Error('无法打开 URL');
        }

        await waitForTabComplete(tempTab.id);
        const pageData = await collectPageTextFromTab(tempTab.id);
        return requestMetadataFromText(mode, pageData.text, {
            html: pageData.html,
            url: pageData.url,
            title: pageData.title,
            source: 'url',
            forceReanalyze,
        });
    } finally {
        if (tempTab && tempTab.id) {
            chrome.tabs.remove(tempTab.id).catch(() => {});
        }
    }
}

async function requestMetadataFromIdentifiers(mode) {
    const language = state.language;
    const identifiers = normalizeWhitespace(state.identifierInput || '');
    if (!identifiers) {
        throw new Error('请输入 DOI 或 CSTR 编号');
    }

    updateStatus(getUIText(language).loadingIdentifier, 'loading');
    const response = await fetch(BACKEND_QUERY_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            source: 'identifier',
            identifiers,
            mode,
        }),
    });

    if (!response.ok) {
        const errorPayload = await response.json().catch(() => ({}));
        throw new Error(errorPayload.message || `HTTP 错误: ${response.status}`);
    }

    const payload = await response.json();
    const items = Array.isArray(payload.items) ? payload.items : [];
    state.identifierResults = items;
    state.currentIdentifierIndex = 0;
    applyIdentifierItemToCache();
    renderIdentifierSelector();
    state.lastFetchedAt = new Date();
    recordConversionLog({
        source: 'identifier',
        mode,
        strategy: 'identifier',
        title: `DOI/CSTR: ${identifiers.slice(0, 80)}`,
        identifierInput: identifiers,
        inputText: identifiers,
        payload,
    });
    return payload;
}

function getCurrentIdentifierItem() {
    const items = Array.isArray(state.identifierResults) ? state.identifierResults : [];
    return items[state.currentIdentifierIndex] || null;
}

function applyIdentifierItemToCache() {
    const item = getCurrentIdentifierItem();
    if (item && item.status === 'ok' && isObject(item.payload)) {
        state.resultCache.common = item.payload;
        state.resultCache.domain = item.payload;
        state.resultCache[getCacheKey(state.mode)] = item.payload;
        return;
    }

    delete state.resultCache.common;
    delete state.resultCache.domain;
    delete state.resultCache[getCacheKey(state.mode)];
}

function renderIdentifierSelector() {
    const selector = document.getElementById('identifierSelector');
    const select = document.getElementById('identifierSelect');
    if (!selector || !select) {
        return;
    }

    const items = Array.isArray(state.identifierResults) ? state.identifierResults : [];
    const shouldShow = state.sourceMode === 'identifier' && items.length > 0 && state.identifierResultReady;
    selector.hidden = !shouldShow;
    if (!shouldShow) {
        return;
    }

    select.innerHTML = '';
    items.forEach((item, index) => {
        const option = document.createElement('option');
        option.value = String(index);
        option.textContent = item && item.identifier ? String(item.identifier) : `#${index + 1}`;
        select.appendChild(option);
    });
    select.value = String(state.currentIdentifierIndex);
    updateIdentifierError();
}

function updateIdentifierError() {
    const error = document.getElementById('identifierError');
    if (!error) {
        return;
    }

    const item = getCurrentIdentifierItem();
    if (item && item.status !== 'ok') {
        const prefix = getUIText().identifierErrorPrefix;
        const message = item.message || getUIText().noContent;
        error.textContent = `${prefix}${message}`;
        error.hidden = false;
        return;
    }

    error.textContent = '';
    error.hidden = true;
}

async function requestMetadataForMode(mode) {
    const language = state.language;
    updateStatus(getUIText(language).loadingExtract, 'loading');

    const pageData = await extractPageText();
    if (!pageData.text) {
        throw new Error('当前页面没有可提取的文本');
    }

    // Save page data for potential re-extraction with LLM
    state.currentPageData = pageData;
    showReextractButton();

    return requestMetadataFromText(mode, pageData.text, {
        html: pageData.html,
        url: pageData.url,
        title: pageData.title,
        source: 'web',
    });
}

async function requestMetadataForUploadedFile(mode) {
    const language = state.language;
    const file = state.uploadedFile;
    if (!file) {
        throw new Error('请先选择一个文件');
    }

    updateStatus(getUIText(language).loadingFile, 'loading');
    const normalizedText = await readFileAsText(file);
    if (!normalizedText) {
        throw new Error('文件内容为空');
    }

    state.uploadedText = normalizedText;
    state.uploadedTitle = file.name;
    return requestMetadataFromText(mode, normalizedText, {
        title: file.name,
        url: '',
        source: 'upload',
        strategy: 'upload_rule',
    });
}

function pickLocalizedItem(items, language = state.language) {
    const list = Array.isArray(items) ? items : [];
    return list.find((item) => isObject(item) && item.lang === language) || null;
}

function filterLocalizedTree(data, language = state.language) {
    if (Array.isArray(data)) {
        if (data.every((item) => isObject(item) && Object.prototype.hasOwnProperty.call(item, 'lang'))) {
            const localized = pickLocalizedItem(data, language);
            return localized ? filterLocalizedTree(localized, language) : null;
        }
        const items = data
            .map((item) => filterLocalizedTree(item, language))
            .filter((item) => !isMissingDisplayValue(item));
        return items.length ? items : null;
    }
    if (!isObject(data)) return data;
    const result = {};
    Object.entries(data).forEach(([key, value]) => {
        if (key === 'lang') return;
        const localized = filterLocalizedTree(value, language);
        if (!isMissingDisplayValue(localized)) result[key] = localized;
    });
    return Object.keys(result).length ? result : null;
}

function normalizeDisplayValue(data, language = state.language) {
    if (Array.isArray(data)) {
        if (data.every((item) => isObject(item) && Object.prototype.hasOwnProperty.call(item, 'lang'))) {
            const localized = pickLocalizedItem(data, language);
            if (!localized) return '';
            if (Object.prototype.hasOwnProperty.call(localized, 'name')) return localized.name;
            if (Object.prototype.hasOwnProperty.call(localized, 'description')) return localized.description;
            if (Object.prototype.hasOwnProperty.call(localized, 'keyword')) {
                return Array.isArray(localized.keyword) ? localized.keyword.join('；') : localized.keyword;
            }
        }
        return data.map((item) => normalizeDisplayValue(item, language)).filter(Boolean).join('；');
    }

    if (!isObject(data)) return data;

    if (Array.isArray(data.names)) return normalizeDisplayValue(data.names, language);
    if (Array.isArray(data.keyword)) return data.keyword.join('；');
    if (data.identifier && data.type) return `${data.type}: ${data.identifier}`;
    if (data.person) {
        const name = normalizeDisplayValue(data.person.names, language);
        const affiliation = normalizeDisplayValue(data.person.affiliations, language);
        return [name, affiliation].filter(Boolean).join(' / ');
    }
    if (data.affiliation) return normalizeDisplayValue(data.affiliation, language);
    if (Array.isArray(data.standard_gbt) || Array.isArray(data.standard_oecd)) {
        return [
            ...(Array.isArray(data.standard_gbt) ? data.standard_gbt : []),
            ...(Array.isArray(data.standard_oecd) ? data.standard_oecd : []),
        ].join('；');
    }
    if (data.license || data.description || data.cert_num) {
        return [data.license, data.description, data.cert_num].filter(Boolean).join('；');
    }
    if (data.name || data.proj_name || data.proj_num) {
        return [data.name, data.proj_type, data.proj_num, data.proj_name].filter(Boolean).join('；');
    }
    return filterLocalizedTree(data, language);
}

function isMissingDisplayValue(value) {
    if (value === null || typeof value === 'undefined') {
        return true;
    }
    if (typeof value === 'string') {
        const normalized = value.trim().toLowerCase();
        return normalized === ''
            || normalized === '未提取到'
            || normalized === '未提取到内容'
            || normalized === 'not extracted'
            || normalized === 'no content extracted';
    }
    if (Array.isArray(value)) {
        return value.length === 0 || value.every((item) => isMissingDisplayValue(item));
    }
    if (isObject(value)) {
        return Object.keys(value).length === 0;
    }
    return false;
}

function renderFieldValue(data) {
    const ui = getUIText();
    const displayValue = normalizeDisplayValue(data);
    if (displayValue !== data) {
        data = displayValue;
    }
    if (isMissingDisplayValue(data)) {
        return {
            text: ui.noContent,
            isEmpty: true,
        };
    }

    if (isObject(data) && Object.prototype.hasOwnProperty.call(data, 'value')) {
        const rawValue = data.value;
        if (isMissingDisplayValue(rawValue)) {
            return {
                text: ui.noContent,
                isEmpty: true,
            };
        }

        if (Array.isArray(rawValue)) {
            return {
                text: rawValue.map((item) => (isObject(item) ? JSON.stringify(item) : String(item))).join('；'),
                isEmpty: false,
            };
        }

        return {
            text: String(rawValue),
            isEmpty: false,
        };
    }

    if (Array.isArray(data)) {
        return {
            text: data.map((item) => (isObject(item) ? JSON.stringify(item) : String(item))).join('；'),
            isEmpty: false,
        };
    }

    if (isObject(data)) {
        return {
            text: JSON.stringify(data),
            isEmpty: false,
        };
    }

    return {
        text: String(data),
        isEmpty: false,
    };
}

function createFieldRow(label, data) {
    const row = document.createElement('div');
    row.className = 'field-row';

    const labelElement = document.createElement('div');
    labelElement.className = 'field-label';
    labelElement.textContent = label;

    const valueState = renderFieldValue(data);
    const valueElement = document.createElement('div');
    valueElement.className = `field-value${valueState.isEmpty ? ' empty' : ''}`;
    valueElement.textContent = valueState.text;

    row.appendChild(labelElement);
    row.appendChild(valueElement);
    return row;
}

function renderSchemaNode(container, schemaNode, valueNode, language = state.language) {
    Object.entries(schemaNode).forEach(([key, description]) => {
        let currentValue = isObject(valueNode) ? valueNode[key] : undefined;
        if (typeof currentValue === 'undefined') {
            // 回退：按标准字段别名在整个 payload 中查找，解决模型字段名不一致的问题
            for (const lookupKey of getFieldLookupKeys(key)) {
                currentValue = findValueByKeyOrAlias(valueNode, lookupKey);
                if (typeof currentValue !== 'undefined') {
                    break;
                }
            }
        }
        if (isObject(description)) {
            const group = document.createElement('section');
            group.className = 'subgroup';

            const title = document.createElement('div');
            title.className = 'group-title';
            const titleText = document.createElement('h3');
            titleText.textContent = key;
            title.appendChild(titleText);

            const fieldList = document.createElement('div');
            fieldList.className = 'field-list';
            renderSchemaNode(fieldList, description, currentValue || {}, language);

            group.appendChild(title);
            group.appendChild(fieldList);
            container.appendChild(group);
            return;
        }

        container.appendChild(createFieldRow(key, currentValue));
    });
}

function renderPayloadSections(container, payload, schema, language = state.language) {
    container.innerHTML = '';

    if (!isObject(payload)) {
        return;
    }

    Object.entries(payload).forEach(([sectionKey, sectionValue]) => {
        const sectionSchema = schema && schema[sectionKey];
        const sectionGroup = document.createElement('section');
        sectionGroup.className = 'metadata-group';

        const title = document.createElement('div');
        title.className = 'group-title';

        const titleText = document.createElement('h3');
        titleText.textContent = getTranslatedLabel(sectionKey, language);
        title.appendChild(titleText);

        sectionGroup.appendChild(title);

        if (isObject(sectionSchema) && isObject(sectionValue)) {
            const fieldList = document.createElement('div');
            fieldList.className = 'field-list';
            renderSchemaNode(fieldList, sectionSchema, sectionValue, language);
            sectionGroup.appendChild(fieldList);
        } else {
            const fieldList = document.createElement('div');
            fieldList.className = 'field-list';
            fieldList.appendChild(createFieldRow(sectionKey, sectionValue));
            sectionGroup.appendChild(fieldList);
        }

        container.appendChild(sectionGroup);
    });
}

function extractExtensionText(payload, language = state.language) {
    if (!isObject(payload)) {
        return '';
    }

    const extensionValue = payload[getExtensionKey(language)]
        ?? payload[language === 'en' ? 'Extension Info' : '扩展信息']
        ?? payload[language === 'en' ? '扩展信息' : 'Extension Info'];
    if (typeof extensionValue === 'string') {
        return extensionValue.trim();
    }

    if (isObject(extensionValue) && typeof extensionValue.value === 'string') {
        return extensionValue.value.trim();
    }

    return '';
}

function renderMode(mode) {
    const language = state.language;
    if (state.sourceMode === 'identifier' && state.identifierResults.length > 0) {
        applyIdentifierItemToCache();
    }
    const payloadBundle = state.resultCache[getCacheKey(mode)] || {};
    const payload = getDisplayPayload(payloadBundle, language);
    const schema = state.schemaCache[mode];
    const schemaKey = getSchemaKeyForMode(mode, payload, language);
    const rawSchemaRoot = schema ? (schema[schemaKey] || schema['核心元数据']) : null;
    const schemaRoot = rawSchemaRoot ? translateTree(rawSchemaRoot, language) : null;
    const sectionPayload = getEffectiveSectionPayload(payload, schemaKey);
    const metadataRoot = document.getElementById('metadataRoot');
    const extensionInfo = document.getElementById('extensionInfo');
    const modeTitle = document.getElementById('modeTitle');
    const lastUpdated = document.getElementById('lastUpdated');
    const ui = getUIText(language);

    modeTitle.textContent = mode === 'domain' ? getTranslatedLabel(schemaKey, language) : MODE_LABELS.common[language];

    metadataRoot.innerHTML = '';
    if (schemaRoot) {
        renderSchemaNode(metadataRoot, schemaRoot, sectionPayload, language);
    }

    const extensionText = extractExtensionText(payload, language);
    extensionInfo.textContent = extensionText || ui.waiting;
    extensionInfo.classList.toggle('empty', !extensionText);

    let lastUpdatedValue = state.lastFetchedAt;
    const currentItem = getCurrentIdentifierItem();
    if (state.sourceMode === 'identifier' && currentItem && currentItem.updated_at) {
        const parsed = new Date(currentItem.updated_at);
        if (!Number.isNaN(parsed.getTime())) {
            lastUpdatedValue = parsed;
        }
    }
    lastUpdated.textContent = lastUpdatedValue
        ? `${ui.updatedAt}${lastUpdatedValue.toLocaleTimeString('zh-CN', { hour12: false })}`
        : '';

    updateIdentifierError();

    updateStaticText();
    setUrlReanalyzeButtonVisibility();
    setUploadReanalyzeButtonVisibility();
}

function stripMetadataForDownload(schemaNode, valueNode, language = DOWNLOAD_LANGUAGE) {
    const result = {};
    Object.entries(schemaNode).forEach(([key, description]) => {
        let currentValue = isObject(valueNode) ? valueNode[key] : undefined;
        if (typeof currentValue === 'undefined') {
            for (const lookupKey of getFieldLookupKeys(key)) {
                currentValue = findValueByKeyOrAlias(valueNode, lookupKey);
                if (typeof currentValue !== 'undefined') {
                    break;
                }
            }
        }
        const outputKey = standardInterfaceKeyForLabel(key);
        if (isObject(description)) {
            result[outputKey] = stripMetadataForDownload(description, currentValue || {}, language);
            return;
        }

        if (isObject(currentValue) && Object.prototype.hasOwnProperty.call(currentValue, 'value')) {
            result[outputKey] = filterLocalizedTree(currentValue.value, language) ?? null;
            return;
        }

        result[outputKey] = filterLocalizedTree(currentValue, language) ?? null;
    });
    return result;
}

function standardInterfaceKeyForLabel(key) {
    const directInterfaceKeys = new Set([
        'titles', 'identifier', 'creators', 'publisher', 'publish_date', 'descriptions',
        'keywords', 'subjects', 'language', 'contributors', 'alternative_identifiers',
        'related_identifiers', 'rights', 'funders', 'version', 'urls', 'resource_type',
    ]);
    if (directInterfaceKeys.has(key)) {
        return key;
    }
    const aliases = FIELD_VALUE_ALIASES[key] || [];
    return aliases.find((alias) => directInterfaceKeys.has(alias)) || key;
}

function normalizeIdentifierToken(value) {
    const raw = String(value || '')
        .trim()
        .replace(/^doi:\s*/i, '')
        .replace(/^cstr:\s*/i, '')
        .replace(/^[<(\[]+/, '')
        .replace(/[>\])]+$/, '')
        .replace(/[.,;，；、]+$/, '');
    const doiMatch = raw.match(/10\.\d{4,9}\/[-._;()/:A-Z0-9]+/i);
    if (doiMatch) {
        return doiMatch[0].toLowerCase();
    }
    const cstrMatch = raw.match(/\d{5}\.\d{2}\.[-._;()/:A-Z0-9]+/i);
    if (cstrMatch) {
        return cstrMatch[0].toLowerCase();
    }
    return raw.toLowerCase();
}

function parseIdentifierTokens(input) {
    if (!input) {
        return [];
    }
    return String(input)
        .split(/[\s,，;；、]+/)
        .map((item) => item.trim())
        .filter(Boolean);
}

function getPayloadSectionKey(schemaKey, language) {
    if (language !== 'en') {
        return schemaKey;
    }

    return {
        核心元数据: 'Core Metadata',
        数据集元数据: 'Dataset Metadata',
        数据论文元数据: 'Data Paper Metadata',
        标准文献元数据: 'Standard Literature Metadata',
        生态科学数据元数据: 'Ecological Science Data Metadata',
    }[schemaKey] || schemaKey;
}

function getDisplayPayload(payloadBundle, language = state.language) {
    if (!isObject(payloadBundle)) {
        return {};
    }
    if (isObject(payloadBundle[language])) {
        return payloadBundle[language];
    }
    return payloadBundle;
}

function buildDownloadPayloadForItem(mode, payloadBundle, schema, language) {
    const payload = getDisplayPayload(payloadBundle, language);
    if (!isObject(payload)) {
        return null;
    }
    const schemaKey = getSchemaKeyForMode(mode, payload, language);
    const schemaRoot = schema[schemaKey] || schema['核心元数据'];
    const localizedSchemaRoot = translateTree(schemaRoot, language);
    const sectionPayload = getEffectiveSectionPayload(payload, getPayloadSectionKey(schemaKey, language));
    const stripped = stripMetadataForDownload(localizedSchemaRoot, sectionPayload, language);
    return schemaKey === '核心元数据' ? { metadatas: [stripped] } : stripped;
}

async function downloadJsonFile(mode) {
    const language = state.language;
    const downloadLanguage = DOWNLOAD_LANGUAGE;
    const schema = state.schemaCache[mode] || await loadSchema(mode);
    if (!schema) {
        updateStatus(getUIText(language).downloadBlocked, 'error');
        return;
    }

    if (state.sourceMode === 'identifier') {
        const tokens = parseIdentifierTokens(state.identifierInput);
        const items = Array.isArray(state.identifierResults) ? state.identifierResults : [];
        if (tokens.length > 1) {
            if (items.length === 0) {
                updateStatus(getUIText(language).downloadBlocked, 'error');
                return;
            }
            const buckets = new Map();
            items.forEach((item) => {
                const key = normalizeIdentifierToken(item && item.identifier);
                if (!key) {
                    return;
                }
                if (!buckets.has(key)) {
                    buckets.set(key, []);
                }
                buckets.get(key).push(item);
            });
            const lines = tokens.map((token) => {
                const key = normalizeIdentifierToken(token);
                const bucket = key ? buckets.get(key) : null;
                const item = bucket && bucket.length > 0 ? bucket.shift() : null;
                if (!item || item.status !== 'ok' || !isObject(item.payload)) {
                    return '';
                }
                const downloadPayload = buildDownloadPayloadForItem(mode, item.payload, schema, downloadLanguage);
                if (!downloadPayload) {
                    return '';
                }
                return JSON.stringify({
                    identifier: item.identifier ?? null,
                    type: item.type ?? null,
                    resolved_url: item.resolved_url ?? null,
                    source: item.source ?? null,
                    payload: downloadPayload,
                    updated_at: item.updated_at ?? null,
                });
            });
            const blob = new Blob([lines.join('\n')], { type: 'application/jsonl;charset=utf-8' });
            const link = document.createElement('a');
            link.href = URL.createObjectURL(blob);
            link.download = `identifiers-${mode}-${downloadLanguage}.jsonl`;
            link.click();
            URL.revokeObjectURL(link.href);
            return;
        }
    }

    const payloadBundle = state.resultCache[getCacheKey(mode)];
    const downloadPayload = buildDownloadPayloadForItem(mode, payloadBundle, schema, downloadLanguage);
    if (!downloadPayload) {
        updateStatus(getUIText(language).downloadBlocked, 'error');
        return;
    }
    const blob = new Blob([JSON.stringify(downloadPayload, null, 2)], { type: 'application/json;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${mode}-${downloadLanguage}-metadata.json`;
    link.click();
    URL.revokeObjectURL(link.href);
}

function updateStaticText() {
    const language = state.language;
    const ui = getUIText(language);

    document.getElementById('startTitle').textContent = ui.startTitle;
    document.getElementById('startDescription').textContent = ui.startDescription;
    document.getElementById('openLogsStartButton').textContent = ui.openLogsTitle;
    document.getElementById('domainToCoreTitle').textContent = ui.domainToCoreTitle;
    document.getElementById('domainToCoreHint').textContent = ui.domainToCoreHint;
    document.getElementById('coreToDomainTitle').textContent = ui.coreToDomainTitle;
    document.getElementById('coreToDomainHint').textContent = ui.coreToDomainHint;
    document.getElementById('chooseWebLabel').textContent = ui.chooseWebLabel;
    document.getElementById('chooseWebHint').textContent = ui.chooseWebHint;
    document.getElementById('chooseUrlLabel').textContent = ui.chooseUrlLabel;
    document.getElementById('chooseUrlHint').textContent = ui.chooseUrlHint;
    document.getElementById('chooseUploadLabel').textContent = ui.chooseUploadLabel;
    document.getElementById('chooseUploadHint').textContent = ui.chooseUploadHint;
    document.getElementById('chooseIdentifierLabel').textContent = ui.chooseIdentifierLabel;
    document.getElementById('chooseIdentifierHint').textContent = ui.chooseIdentifierHint;
    document.getElementById('appTitle').textContent = ui.appTitle;
    document.getElementById('extensionTitle').textContent = ui.extensionTitle;
    document.getElementById('uploadTitle').textContent = ui.uploadTitle;
    const uploadExampleJson = document.getElementById('uploadExampleJson');
    const uploadExampleButton = document.getElementById('uploadExampleButton');
    if (uploadExampleJson && uploadExampleButton) {
        uploadExampleJson.textContent = UPLOAD_EXAMPLE_JSON;
        uploadExampleButton.textContent = uploadExampleJson.hidden ? ui.uploadExampleButton : ui.uploadExampleButtonHide;
    }
    document.getElementById('urlTitle').textContent = ui.urlTitle;
    document.getElementById('urlDescription').textContent = ui.urlDescription;
    document.getElementById('urlInput').setAttribute('placeholder', ui.urlPlaceholder);
    document.getElementById('confirmUrlButton').textContent = ui.confirmUrlButton;
    document.getElementById('clearUrlButton').textContent = ui.clearUrlButton;
    document.getElementById('identifierTitle').textContent = ui.identifierTitle;
    document.getElementById('identifierDescription').textContent = ui.identifierDescription;
    document.getElementById('identifierInput').setAttribute('placeholder', ui.identifierPlaceholder);
    document.getElementById('confirmIdentifierButton').textContent = ui.confirmIdentifierButton;
    document.getElementById('clearIdentifierButton').textContent = ui.clearIdentifierButton;
    const identifierSelectLabel = document.getElementById('identifierSelectLabel');
    if (identifierSelectLabel) {
        identifierSelectLabel.textContent = ui.identifierSelectLabel;
    }
    document.getElementById('homeButton').setAttribute('aria-label', '返回初始页');
    document.getElementById('homeButton').setAttribute('title', '返回初始页');
    document.getElementById('refreshButton').setAttribute('aria-label', ui.refreshTitle);
    document.getElementById('refreshButton').setAttribute('title', ui.refreshTitle);
    document.getElementById('downloadButton').setAttribute('aria-label', ui.downloadTitle);
    document.getElementById('downloadButton').setAttribute('title', ui.downloadTitle);
    document.getElementById('openLogsButton').setAttribute('aria-label', ui.openLogsTitle);
    document.getElementById('openLogsButton').setAttribute('title', ui.openLogsTitle);
    document.getElementById('closeLogsButton').setAttribute('aria-label', '返回主页');
    document.getElementById('closeLogsButton').setAttribute('title', '返回主页');
    document.querySelector('.mode-switcher').setAttribute('aria-label', ui.modeSwitcherLabel);

    const selectedFileName = document.getElementById('selectedFileName');
    if (state.uploadedFile) {
        selectedFileName.textContent = `${ui.selectedFilePrefix}${state.uploadedFile.name}`;
    } else {
        selectedFileName.textContent = ui.selectedFileEmpty;
    }

    const uploadPanel = document.getElementById('uploadPanel');
    uploadPanel.hidden = state.sourceMode !== 'upload';
    const identifierPanel = document.getElementById('identifierPanel');
    identifierPanel.hidden = state.sourceMode !== 'identifier';
    const urlPanel = document.getElementById('urlPanel');
    urlPanel.hidden = state.sourceMode !== 'url';

    setUploadPanelState();
    setAnalysisVisibility();
    renderIdentifierSelector();
    setUploadReanalyzeButtonVisibility();

    const commonButton = document.querySelector('.mode-button[data-mode="common"]');
    const domainButton = document.querySelector('.mode-button[data-mode="domain"]');
    if (commonButton) {
        commonButton.textContent = MODE_LABELS.common[language];
    }
    if (domainButton) {
        domainButton.textContent = MODE_LABELS.domain[language];
    }

    const langZhButton = document.getElementById('langZhButton');
    const langEnButton = document.getElementById('langEnButton');
    if (langZhButton) {
        langZhButton.classList.toggle('active', language === 'zh');
        langZhButton.textContent = ui.languageZh;
    }
    if (langEnButton) {
        langEnButton.classList.toggle('active', language === 'en');
        langEnButton.textContent = ui.languageEn;
    }
    if (!document.getElementById('logWorkspace').hidden) {
        renderLogs();
    }
}

async function refreshCurrentMode() {
    const mode = state.mode;
    const language = state.language;
    try {
        await loadModeSchema(mode);
        if (state.sourceMode === 'upload') {
            await requestMetadataForUploadedFile(mode);
            state.uploadResultReady = true;
        } else if (state.sourceMode === 'identifier') {
            await requestMetadataFromIdentifiers(mode);
            state.identifierResultReady = true;
        } else if (state.sourceMode === 'url') {
            await requestMetadataFromUrl(mode);
            state.urlResultReady = true;
        } else {
            updateStatus(getUIText(language).loadingExtract, 'loading');
            await requestMetadataForMode(mode);
        }
        setAnalysisVisibility();
        renderMode(mode);
        updateStatus('', 'idle');
    } catch (error) {
        console.error(error);
        updateStatus(`${getUIText(language).errorPrefix}${error.message}`, 'error');
    }
}

function setMode(mode) {
    if (mode === state.mode) {
        return;
    }

    state.mode = mode;
    document.querySelectorAll('.mode-button').forEach((item) => {
        item.classList.toggle('active', item.dataset.mode === mode);
    });
    if (state.resultCache.common || state.resultCache.domain) {
        renderMode(mode);
        updateStatus('', 'idle');
        return;
    }
    refreshCurrentMode();
}

function clearAnalysisView() {
    const metadataRoot = document.getElementById('metadataRoot');
    const extensionInfo = document.getElementById('extensionInfo');
    const modeTitle = document.getElementById('modeTitle');
    const lastUpdated = document.getElementById('lastUpdated');

    metadataRoot.innerHTML = '';
    extensionInfo.textContent = getUIText().waiting;
    extensionInfo.classList.add('empty');
    modeTitle.textContent = MODE_LABELS.common[state.language];
    lastUpdated.textContent = '';
}

function selectSourceMode(sourceMode) {
    activateSourceMode(sourceMode);
    state.uploadStage = 'idle';
    state.uploadResultReady = false;
    state.identifierResultReady = false;
    state.identifierResults = [];
    state.currentIdentifierIndex = 0;
    state.urlResultReady = false;
    state.urlHistoryUsed = false;
    state.uploadedFile = null;
    state.uploadedText = '';
    state.uploadedTitle = '';
    setActiveView(true);
    updateStaticText();
    clearAnalysisView();
    setUrlReanalyzeButtonVisibility();

    if (sourceMode === 'web') {
        refreshCurrentMode();
        return;
    }

    if (state.resultCache.common || state.resultCache.domain) {
        renderMode(state.mode);
    }
    updateStatus('', 'idle');
}

function resetToStartScreen() {
    state.sourceMode = null;
    state.resultCache = {};
    state.resultCacheBySource = { web: {}, url: {}, upload: {}, identifier: {} };
    state.uploadedFile = null;
    state.uploadedText = '';
    state.uploadedTitle = '';
    state.uploadStage = 'idle';
    state.uploadResultReady = false;
    state.identifierInput = '';
    state.identifierResultReady = false;
    state.identifierResults = [];
    state.currentIdentifierIndex = 0;
    state.urlInput = '';
    state.urlResultReady = false;
    state.urlHistoryUsed = false;
    document.getElementById('identifierInput').value = '';
    document.getElementById('urlInput').value = '';
    setActiveView(false);
    clearAnalysisView();
    updateStatus('', 'idle');
    setUrlReanalyzeButtonVisibility();
}

function handleUploadSelection(file) {
    if (!file) {
        return;
    }

    state.uploadedFile = file;
    state.uploadedText = '';
    state.uploadedTitle = file.name;
    state.uploadStage = 'selected';
    state.uploadResultReady = false;
    updateStaticText();
}

function clearUrlInput() {
    state.urlInput = '';
    state.urlResultReady = false;
    state.urlHistoryUsed = false;
    state.resultCache = getSourceResultCache();
    delete state.resultCache.common;
    delete state.resultCache.domain;
    document.getElementById('urlInput').value = '';
    clearAnalysisView();
    updateStaticText();
    updateStatus('', 'idle');
    setUrlReanalyzeButtonVisibility();
}

async function confirmUrlAndAnalyze() {
    const urlInput = document.getElementById('urlInput');
    state.urlInput = urlInput.value.trim();
    state.urlResultReady = false;
    state.urlHistoryUsed = false;
    updateStaticText();
    setUrlReanalyzeButtonVisibility();
    await refreshCurrentMode();
}

async function confirmUploadAndAnalyze() {
    if (!state.uploadedFile) {
        return;
    }

    state.uploadStage = 'confirmed';
    state.uploadHistoryUsed = false;
    updateStaticText();
    await refreshCurrentMode();
}

async function confirmIdentifierAndAnalyze() {
    const identifierInput = document.getElementById('identifierInput');
    state.identifierInput = identifierInput.value.trim();
    state.identifierResultReady = false;
    updateStaticText();
    await refreshCurrentMode();
}

function clearIdentifierInput() {
    state.identifierInput = '';
    state.identifierResultReady = false;
    state.identifierResults = [];
    state.currentIdentifierIndex = 0;
    state.resultCache = getSourceResultCache();
    delete state.resultCache.common;
    delete state.resultCache.domain;
    document.getElementById('identifierInput').value = '';
    clearAnalysisView();
    updateStaticText();
    updateStatus('', 'idle');
}

function reselectUploadFile() {
    state.uploadedFile = null;
    state.uploadedText = '';
    state.uploadedTitle = '';
    state.uploadStage = 'idle';
    state.uploadResultReady = false;
    updateStaticText();
    document.getElementById('fileInput').click();
}

function setLanguage(language) {
    if (language === state.language) {
        return;
    }

    state.language = language;
    updateStaticText();
    renderMode(state.mode);
}

function bindEvents() {
    document.getElementById('homeButton').addEventListener('click', resetToStartScreen);
    document.getElementById('openLogsStartButton').addEventListener('click', showLogs);
    document.getElementById('openLogsButton').addEventListener('click', showLogs);
    document.getElementById('closeLogsButton').addEventListener('click', closeLogs);
    document.getElementById('clearLogsButton').addEventListener('click', () => {
        state.conversionLogs = [];
        state.selectedLogId = null;
        saveConversionLogs();
        renderLogs();
    });
    document.getElementById('chooseWebButton').addEventListener('click', () => selectSourceMode('web'));
    document.getElementById('chooseUrlButton').addEventListener('click', () => selectSourceMode('url'));
    document.getElementById('chooseUploadButton').addEventListener('click', () => selectSourceMode('upload'));
    document.getElementById('chooseIdentifierButton').addEventListener('click', () => selectSourceMode('identifier'));

    document.querySelectorAll('.mode-button').forEach((button) => {
        button.addEventListener('click', () => setMode(button.dataset.mode));
    });

    document.querySelectorAll('.lang-button').forEach((button) => {
        button.addEventListener('click', () => setLanguage(button.dataset.language));
    });

    document.getElementById('refreshButton').addEventListener('click', refreshCurrentMode);
    document.getElementById('downloadButton').addEventListener('click', async () => {
        await downloadJsonFile(state.mode);
    });

    document.getElementById('uploadButton').addEventListener('click', () => {
        if (state.sourceMode !== 'upload') {
            selectSourceMode('upload');
        }
        document.getElementById('fileInput').click();
    });
    document.getElementById('uploadExampleButton').addEventListener('click', () => {
        const example = document.getElementById('uploadExampleJson');
        example.hidden = !example.hidden;
        updateStaticText();
    });

    document.getElementById('confirmUploadButton').addEventListener('click', confirmUploadAndAnalyze);
    document.getElementById('reselectUploadButton').addEventListener('click', reselectUploadFile);
    document.getElementById('confirmUrlButton').addEventListener('click', confirmUrlAndAnalyze);
    document.getElementById('clearUrlButton').addEventListener('click', clearUrlInput);
    document.getElementById('reanalyzeUrlButton').addEventListener('click', async () => {
        const button = document.getElementById('reanalyzeUrlButton');
        if (!button) {
            return;
        }

        const originalText = button.textContent;
        button.disabled = true;
        button.textContent = originalText;
        try {
            await requestMetadataFromUrl(state.mode, { forceReanalyze: true });
            state.urlResultReady = true;
            setAnalysisVisibility();
            renderMode(state.mode);
            updateStatus('', 'idle');
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    });
    document.getElementById('reanalyzeUploadButton').addEventListener('click', async () => {
        const button = document.getElementById('reanalyzeUploadButton');
        if (!button) {
            return;
        }

        const originalText = button.textContent;
        button.disabled = true;
        try {
            console.log('[UI] Reanalyze (upload) clicked — sending force_reanalyze to backend');
            // send the uploaded text back to backend and force reanalysis
            await requestMetadataFromText(state.mode, state.uploadedText || '', {
                title: state.uploadedTitle || '',
                url: '',
                source: 'upload',
                forceReanalyze: true,
            });
            state.uploadResultReady = true;
            setAnalysisVisibility();
            renderMode(state.mode);
            updateStatus('', 'idle');
        } catch (err) {
            console.error('[UI] Reanalyze (upload) failed', err);
            updateStatus(`${getUIText().errorPrefix}${err.message || err}`, 'error');
        } finally {
            button.disabled = false;
            button.textContent = originalText;
        }
    });
    document.getElementById('confirmIdentifierButton').addEventListener('click', confirmIdentifierAndAnalyze);
    document.getElementById('clearIdentifierButton').addEventListener('click', clearIdentifierInput);
    document.getElementById('identifierSelect').addEventListener('change', (event) => {
        const nextIndex = Number(event.target.value);
        state.currentIdentifierIndex = Number.isNaN(nextIndex) ? 0 : nextIndex;
        applyIdentifierItemToCache();
        renderMode(state.mode);
    });
    document.getElementById('urlInput').addEventListener('input', (event) => {
        state.urlInput = event.target.value;
        state.urlResultReady = false;
        state.resultCache = getSourceResultCache();
        delete state.resultCache.common;
        delete state.resultCache.domain;
        clearAnalysisView();
        setAnalysisVisibility();
    });
    document.getElementById('identifierInput').addEventListener('input', (event) => {
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

    document.getElementById('fileInput').addEventListener('change', (event) => {
        const [file] = event.target.files || [];
        handleUploadSelection(file);
        event.target.value = '';
    });

    const llmBtn = document.getElementById('llmExtractButton');
    if (llmBtn) {
        llmBtn.addEventListener('click', async () => {
            const originalText = llmBtn.textContent;
            llmBtn.textContent = '已发送，请等待';
            llmBtn.disabled = true;
            try {
                await reextractWithLLM();
                llmBtn.textContent = '分析完成';
                setTimeout(() => {
                    llmBtn.textContent = originalText;
                }, 2000);
            } catch (e) {
                console.error(e);
                llmBtn.textContent = originalText;
            } finally {
                llmBtn.disabled = false;
            }
        });
    }

}

function showReextractButton() {
    const button = document.getElementById('reextractButton');
    if (button && state.currentPageData) {
        button.hidden = false;
    }
}

async function reextractWithLLM() {
    if (!state.currentPageData) {
        return;
    }

    const language = state.language;
    const mode = state.mode;

    try {
        updateStatus(getUIText(language).loadingSend, 'loading');

        // Force LLM extraction with strategy='llm'
        await requestMetadataFromText(mode, state.currentPageData.text, {
            html: state.currentPageData.html,
            url: state.currentPageData.url,
            title: state.currentPageData.title,
            strategy: 'llm',  // Force LLM extraction
            source: 'web',
            forceReanalyze: true,
        });

        renderMode(mode);
        updateStatus('', 'idle');

        // extraction completed; UI update handled by caller (if any)
    } catch (error) {
        console.error(error);
        updateStatus(`${getUIText(language).errorPrefix}${error.message}`, 'error');
    }
}

document.addEventListener('DOMContentLoaded', async () => {
    loadConversionLogs();
    bindEvents();
    updateStaticText();
    try {
        await loadModeSchema('common');
        await loadModeSchema('domain');
        setActiveView(false);
        setAnalysisVisibility();
    } catch (error) {
        console.error(error);
        updateStatus(`${getUIText(state.language).initErrorPrefix}${error.message}`, 'error');
    }
});
