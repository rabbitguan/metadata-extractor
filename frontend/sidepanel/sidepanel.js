const BACKEND_URL = 'http://127.0.0.1:4000/info';

const LABEL_TRANSLATIONS_EN = {
    资源类型候选列表: 'Resource Type Candidates',
    类型名称: 'Type Name',
    英文类型: 'English Type',
    领域元数据: 'Domain Metadata',
    核心元数据: 'Core Metadata',
    数据集元数据: 'Dataset Metadata',
    数据论文元数据: 'Data Paper Metadata',
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
    资源名称: 'Resource Name',
    描述: 'Description',
    关键词: 'Keywords',
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
    标题: 'Title',
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
    发布日期: 'Publication Date',
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
    出版日期: 'Publication Date',
    数据论文下载地址: 'Data Paper Download URL',
    数据论文共享许可协议: 'Data Paper License',
    数据集访问地址: 'Dataset Access URL',
};

const MODE_LABELS = {
    common: {
        zh: '通用元数据项目表',
        en: 'General Metadata',
    },
    domain: {
        zh: '领域专用元数据项目表',
        en: 'Domain Metadata',
    },
};

const UI_TEXT = {
    zh: {
        appTitle: 'Metadata Organizer',
        startTitle: 'Metadata Organizer',
        startDescription: '请选择分析方式：分析网页 / 上传文件 / 输入 DOI/CSTR',
        chooseWebLabel: '分析网页',
        chooseWebHint: '提取当前页面并整理元数据',
        chooseUploadLabel: '上传数据',
        chooseUploadHint: '上传 JSON / TXT 等文本文件',
        chooseIdentifierLabel: '输入 DOI/CSTR',
        chooseIdentifierHint: '通过编号解析资源并整理元数据',
        uploadTitle: '上传数据文件',
        uploadDescription: '支持文件格式：JSON / TXT / CSV / MD / XML / HTML / LOG',
        uploadButton: '选择文件',
        confirmUploadButton: '确认并分析',
        reselectUploadButton: '重新选择',
        identifierTitle: '输入 DOI/CSTR',
        identifierDescription: '支持单个或多个 DOI / CSTR，多个编号可用换行、空格或逗号分隔',
        identifierPlaceholder: '10.xxxx/example 或 12345.12.123456.123456',
        confirmIdentifierButton: '确认并分析',
        clearIdentifierButton: '清空',
        selectedFileEmpty: '尚未选择文件',
        selectedFilePrefix: '已选择：',
        modeSwitcherLabel: '元数据模式切换',
        extensionTitle: '扩展信息',
        waiting: '等待提取结果',
        noContent: '未提取到内容',
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
    },
    en: {
        appTitle: 'Metadata Organizer',
        startTitle: 'Metadata Organizer',
        startDescription: 'Choose an analysis mode: analyze web page / upload file / enter DOI/CSTR',
        chooseWebLabel: 'Analyze web page',
        chooseWebHint: 'Extract the current page and organize metadata',
        chooseUploadLabel: 'Upload data',
        chooseUploadHint: 'Upload JSON / TXT and other text files',
        chooseIdentifierLabel: 'Enter DOI/CSTR',
        chooseIdentifierHint: 'Resolve identifiers and organize metadata',
        uploadTitle: 'Upload data file',
        uploadDescription: 'Supported file formats: JSON / TXT / CSV / MD / XML / HTML / LOG',
        uploadButton: 'Choose file',
        confirmUploadButton: 'Confirm and analyze',
        reselectUploadButton: 'Choose again',
        identifierTitle: 'Enter DOI/CSTR',
        identifierDescription: 'Supports one or more DOI / CSTR identifiers separated by new lines, spaces, or commas',
        identifierPlaceholder: '10.xxxx/example or 12345.12.123456.123456',
        confirmIdentifierButton: 'Confirm and analyze',
        clearIdentifierButton: 'Clear',
        selectedFileEmpty: 'No file selected yet',
        selectedFilePrefix: 'Selected: ',
        modeSwitcherLabel: 'Metadata mode switcher',
        extensionTitle: 'Extension Info',
        waiting: 'Waiting for results',
        noContent: 'No content extracted',
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
    },
};

const state = {
    sourceMode: null,
    mode: 'common',
    language: 'zh',
    schemaCache: {},
    resultCacheBySource: {
        web: {},
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
    identifierInput: '',
    identifierResultReady: false,
};

function isObject(value) {
    return typeof value === 'object' && value !== null && !Array.isArray(value);
}

function normalizeWhitespace(value) {
    return value.replace(/\s+/g, ' ').replace(/\n{3,}/g, '\n\n').trim();
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
}

function setAnalysisVisibility() {
    const modeSwitcher = document.querySelector('.mode-switcher');
    const analysisContent = document.getElementById('analysisContent');
    const uploadPanel = document.getElementById('uploadPanel');
    const identifierPanel = document.getElementById('identifierPanel');

    if (state.sourceMode === 'upload') {
        uploadPanel.hidden = false;
        identifierPanel.hidden = true;
        modeSwitcher.hidden = !state.uploadResultReady;
        analysisContent.hidden = !state.uploadResultReady;
        return;
    }

    if (state.sourceMode === 'identifier') {
        uploadPanel.hidden = true;
        identifierPanel.hidden = false;
        modeSwitcher.hidden = !state.identifierResultReady;
        analysisContent.hidden = !state.identifierResultReady;
        return;
    }

    uploadPanel.hidden = true;
    identifierPanel.hidden = true;
    modeSwitcher.hidden = false;
    analysisContent.hidden = false;
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

    if (!trimmedText) {
        return '';
    }

    if (file.name.toLowerCase().endsWith('.json') || trimmedText.startsWith('{') || trimmedText.startsWith('[')) {
        try {
            const parsed = JSON.parse(rawText);
            const flattenedText = flattenStructuredValue(parsed).join('\n').trim();
            return flattenedText || normalizeWhitespace(rawText);
        } catch (error) {
            console.warn('Failed to parse JSON upload, falling back to raw text.', error);
        }
    }

    return normalizeWhitespace(rawText);
}

function getModeSchemaKey(mode) {
    return '核心元数据';
}

function getLocalizedModeTitle(mode, language = state.language) {
    return (MODE_LABELS[mode] && MODE_LABELS[mode][language]) || MODE_LABELS.common[language] || mode;
}

function getCacheKey(mode = state.mode) {
    return mode;
}

function getExtensionKey(language = state.language) {
    return language === 'en' ? 'Extension Info' : '扩展信息';
}

function getDomainClassificationKey(language = state.language) {
    return language === 'en' ? 'Domain Classification' : '领域判定';
}

function getResourceTypeClassificationKey(language = state.language) {
    return language === 'en' ? 'Resource Type Classification' : '资源类型判定';
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
        const coreData = isObject(payload) ? payload[coreKey] : null;
        
        // 从核心元数据中获取领域判定
        const classificationKey = language === 'en' ? 'Domain Classification' : '领域判定';
        const classification = isObject(coreData) ? coreData[classificationKey] : null;
        
        if (classification) {
            // 直接映射领域判定到 schema 名称
            if (language === 'en') {
                return {
                    'Core Metadata': '核心元数据',
                    'Dataset Metadata': '数据集元数据',
                    'Data Paper Metadata': '数据论文元数据',
                    'Standard Literature Metadata': '标准文献元数据',
                    'Ecological Science Data Metadata': '生态科学数据元数据',
                }[classification] || '核心元数据';
            } else {
                return classification; // 直接返回，如 "数据论文元数据"
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
        return directSection;
    }

    const coreSectionKey = schemaKey === '核心元数据' ? '核心元数据' : schemaKey;
    if (isObject(payload[coreSectionKey])) {
        return payload[coreSectionKey];
    }

    return payload;
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

async function extractPageText() {
    const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
    if (!tabs.length || !tabs[0].id) {
        throw new Error('未找到当前活动标签页');
    }

    const [result] = await chrome.scripting.executeScript({
        target: { tabId: tabs[0].id },
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
        title: pageData.title || '',
        url: pageData.url || '',
    };
}

async function requestMetadataFromText(mode, text, { title = '', url = '' } = {}) {
    const language = state.language;
    if (!text) {
        throw new Error('没有可发送给大模型的内容');
    }

    updateStatus(getUIText(language).loadingSend, 'loading');
    const response = await fetch(BACKEND_URL, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            text,
            url,
            title,
            mode,
        }),
    });

    if (!response.ok) {
        throw new Error(`HTTP 错误: ${response.status}`);
    }

    const payload = await response.json();
    state.resultCache.common = payload;
    state.resultCache.domain = payload;
    state.resultCache[getCacheKey(mode)] = payload;
    state.lastFetchedAt = new Date();
    return payload;
}

async function requestMetadataFromIdentifiers(mode) {
    const language = state.language;
    const identifiers = normalizeWhitespace(state.identifierInput || '');
    if (!identifiers) {
        throw new Error('请输入 DOI 或 CSTR 编号');
    }

    updateStatus(getUIText(language).loadingIdentifier, 'loading');
    const response = await fetch(BACKEND_URL, {
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
    state.resultCache.common = payload;
    state.resultCache.domain = payload;
    state.resultCache[getCacheKey(mode)] = payload;
    state.lastFetchedAt = new Date();
    return payload;
}

async function requestMetadataForMode(mode) {
    const language = state.language;
    updateStatus(getUIText(language).loadingExtract, 'loading');

    const pageData = await extractPageText();
    if (!pageData.text) {
        throw new Error('当前页面没有可提取的文本');
    }

    return requestMetadataFromText(mode, pageData.text, {
        url: pageData.url,
        title: pageData.title,
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
    });
}

function renderFieldValue(data) {
    const ui = getUIText();
    if (data === null || typeof data === 'undefined') {
        return {
            text: ui.noContent,
            isEmpty: true,
        };
    }

    if (isObject(data) && Object.prototype.hasOwnProperty.call(data, 'value')) {
        const rawValue = data.value;
        if (rawValue === null || typeof rawValue === 'undefined' || rawValue === '') {
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
            // 回退：在整个语言 payload 中查找该字段，解决模型将字段放在不同层级的问题
            currentValue = findValueInPayload(valueNode, key);
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

function extractExtensionText(payload, language = state.language) {
    if (!isObject(payload)) {
        return '';
    }

    const extensionValue = payload[getExtensionKey(language)] ?? payload[getExtensionKey(language === 'en' ? 'zh' : 'en')];
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
    const payloadBundle = state.resultCache[getCacheKey(mode)] || {};
    const payload = isObject(payloadBundle[language]) ? payloadBundle[language] : {};
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

    lastUpdated.textContent = state.lastFetchedAt ? `${ui.updatedAt}${state.lastFetchedAt.toLocaleTimeString('zh-CN', { hour12: false })}` : '';

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

        if (isObject(currentValue) && Object.prototype.hasOwnProperty.call(currentValue, 'value')) {
            result[key] = currentValue.value ?? null;
            return;
        }

        if (Array.isArray(currentValue)) {
            result[key] = currentValue;
            return;
        }

        result[key] = currentValue ?? null;
    });
    return result;
}

function downloadJsonFile(mode) {
    const language = state.language;
    const payloadBundle = state.resultCache[getCacheKey(mode)];
    const payload = payloadBundle && payloadBundle[language];
    const schema = state.schemaCache[mode];
    if (!schema || !payload) {
        updateStatus(getUIText(language).downloadBlocked, 'error');
        return;
    }

    const schemaKey = getSchemaKeyForMode(mode, payloadBundle[language], language);
    const schemaRoot = schema[schemaKey] || schema['核心元数据'];
    const localizedSchemaRoot = translateTree(schemaRoot, language);
    const sectionPayload = getEffectiveSectionPayload(payload, schemaKey);
    const downloadPayload = stripMetadataForDownload(localizedSchemaRoot, sectionPayload);
    const blob = new Blob([JSON.stringify(downloadPayload, null, 2)], { type: 'application/json;charset=utf-8' });
    const link = document.createElement('a');
    link.href = URL.createObjectURL(blob);
    link.download = `${mode}-${language}-metadata.json`;
    link.click();
    URL.revokeObjectURL(link.href);
}

function updateStaticText() {
    const language = state.language;
    const ui = getUIText(language);

    document.getElementById('startTitle').textContent = ui.startTitle;
    document.getElementById('startDescription').textContent = ui.startDescription;
    document.getElementById('chooseWebLabel').textContent = ui.chooseWebLabel;
    document.getElementById('chooseWebHint').textContent = ui.chooseWebHint;
    document.getElementById('chooseUploadLabel').textContent = ui.chooseUploadLabel;
    document.getElementById('chooseUploadHint').textContent = ui.chooseUploadHint;
    document.getElementById('chooseIdentifierLabel').textContent = ui.chooseIdentifierLabel;
    document.getElementById('chooseIdentifierHint').textContent = ui.chooseIdentifierHint;
    document.getElementById('appTitle').textContent = ui.appTitle;
    document.getElementById('extensionTitle').textContent = ui.extensionTitle;
    document.getElementById('uploadTitle').textContent = ui.uploadTitle;
    document.getElementById('uploadDescription').textContent = ui.uploadDescription;
    document.getElementById('identifierTitle').textContent = ui.identifierTitle;
    document.getElementById('identifierDescription').textContent = ui.identifierDescription;
    document.getElementById('identifierInput').setAttribute('placeholder', ui.identifierPlaceholder);
    document.getElementById('confirmIdentifierButton').textContent = ui.confirmIdentifierButton;
    document.getElementById('clearIdentifierButton').textContent = ui.clearIdentifierButton;
    document.getElementById('homeButton').setAttribute('aria-label', '返回初始页');
    document.getElementById('homeButton').setAttribute('title', '返回初始页');
    document.getElementById('refreshButton').setAttribute('aria-label', ui.refreshTitle);
    document.getElementById('refreshButton').setAttribute('title', ui.refreshTitle);
    document.getElementById('downloadButton').setAttribute('aria-label', ui.downloadTitle);
    document.getElementById('downloadButton').setAttribute('title', ui.downloadTitle);
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

    setUploadPanelState();
    setAnalysisVisibility();

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
    state.uploadedFile = null;
    state.uploadedText = '';
    state.uploadedTitle = '';
    setActiveView(true);
    updateStaticText();
    clearAnalysisView();

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
    state.resultCacheBySource = { web: {}, upload: {}, identifier: {} };
    state.uploadedFile = null;
    state.uploadedText = '';
    state.uploadedTitle = '';
    state.uploadStage = 'idle';
    state.uploadResultReady = false;
    state.identifierInput = '';
    state.identifierResultReady = false;
    document.getElementById('identifierInput').value = '';
    setActiveView(false);
    clearAnalysisView();
    updateStatus('', 'idle');
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

async function confirmUploadAndAnalyze() {
    if (!state.uploadedFile) {
        return;
    }

    state.uploadStage = 'confirmed';
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
    document.getElementById('chooseWebButton').addEventListener('click', () => selectSourceMode('web'));
    document.getElementById('chooseUploadButton').addEventListener('click', () => selectSourceMode('upload'));
    document.getElementById('chooseIdentifierButton').addEventListener('click', () => selectSourceMode('identifier'));

    document.querySelectorAll('.mode-button').forEach((button) => {
        button.addEventListener('click', () => setMode(button.dataset.mode));
    });

    document.querySelectorAll('.lang-button').forEach((button) => {
        button.addEventListener('click', () => setLanguage(button.dataset.language));
    });

    document.getElementById('refreshButton').addEventListener('click', refreshCurrentMode);
    document.getElementById('downloadButton').addEventListener('click', () => downloadJsonFile(state.mode));

    document.getElementById('uploadButton').addEventListener('click', () => {
        if (state.sourceMode !== 'upload') {
            selectSourceMode('upload');
        }
        document.getElementById('fileInput').click();
    });

    document.getElementById('confirmUploadButton').addEventListener('click', confirmUploadAndAnalyze);
    document.getElementById('reselectUploadButton').addEventListener('click', reselectUploadFile);
    document.getElementById('confirmIdentifierButton').addEventListener('click', confirmIdentifierAndAnalyze);
    document.getElementById('clearIdentifierButton').addEventListener('click', clearIdentifierInput);
    document.getElementById('identifierInput').addEventListener('input', (event) => {
        state.identifierInput = event.target.value;
        state.identifierResultReady = false;
        state.resultCache = getSourceResultCache();
        delete state.resultCache.common;
        delete state.resultCache.domain;
        clearAnalysisView();
        setAnalysisVisibility();
    });

    document.getElementById('fileInput').addEventListener('change', (event) => {
        const [file] = event.target.files || [];
        handleUploadSelection(file);
        event.target.value = '';
    });
}

document.addEventListener('DOMContentLoaded', async () => {
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
