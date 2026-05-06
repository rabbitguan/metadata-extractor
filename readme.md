# 科技资源模型双向映射工具

Chrome插件 + Flask后端，自动提取网页中的科技资源元数据，支持中英文双语输出。

## 功能

- 自动识别网页资源类型（数据集/数据论文/其他）
- 按标准提取元数据（核心元数据 + 领域专用元数据）
- 中英文双语展示
- 扩展信息智能提取
- 一键下载JSON

## 使用方法

### 1. 后端

    git clone https://github.com/rabbitguan/metadata-extractor.git
    cd metadata-extractor/backend

    # 创建虚拟环境
    python -m venv .venv
    source .venv/bin/activate  # Windows: .venv\Scripts\activate

    # 安装依赖
    pip install -r requirements.txt

    # 配置API Key（编辑 llm_api.py，填入你的API Key）

    # 启动服务
    python backend.py

服务运行在 http://127.0.0.1:4000

---

### 2. Chrome插件

1. 打开 Chrome，地址栏输入 `chrome://extensions/`
2. 开启右上角「开发者模式」
3. 点击「加载已解压的扩展程序」
4. 选择项目根目录 `metadata-extractor` 文件夹
5. 安装完成，浏览器工具栏出现插件图标

---

## 使用

### 插件使用方法

1. 确保后端服务已启动（`python backend.py`）
2. 打开任意科技资源网页（如 arXiv论文、数据集页面）

#### 打开侧边栏：
- 点击浏览器工具栏的插件图标  
- 或右键网页 → 选择「Side Panel」

#### 查看结果：
- 顶部切换「通用模式」/「领域模式」
- 下方显示中英文元数据

#### 下载：
- 点击右上角「下载JSON」按钮

---