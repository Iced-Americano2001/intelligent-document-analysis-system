# 🤖 智能文档分析系统

基于 **MCP (Model Context Protocol)** 和 **多智能体架构** 的现代化文档分析平台，集成先进的AI技术，支持多种文档格式的智能问答、数据分析和对话报告生成。

## ✨ 核心特性

### 📄 文档处理能力
- **多格式支持**: Word (.docx)、PowerPoint (.pptx)、Excel (.xlsx)、PDF (.pdf)
- **智能解析**: 自动提取文本、表格、图表等结构化内容
- **批量处理**: 支持多文档联合分析

### 🧠 AI智能体系统
- **QA智能体**: 基于文档内容的精准问答
- **分析智能体**: 专业的数据分析和可视化
- **MCP智能体**: 增强的推理和工具调用能力
- **报告智能体**: 自动生成结构化分析报告

### 📊 数据分析功能
- **统计分析**: 描述性统计、相关性分析、趋势分析
- **时间序列**: 时序数据处理和预测
- **可视化**: matplotlib、plotly、seaborn多种图表支持
- **报告生成**: 自动生成Markdown格式的分析报告

### � 工作流引擎
- **模块化设计**: 可扩展的工作流架构
- **异步处理**: 高性能的并发处理能力
- **状态管理**: 完整的任务状态跟踪

## �🚀 快速开始

### 环境要求
- **Python**: 3.8+ 
- **AI模型**: Ollama (推荐) / OpenAI API / 第三方API转发平台
- **系统**: Windows / Linux / macOS

### 1. 克隆项目
```bash
git clone <repository-url>
cd document_analysis_system
```

### 2. 创建虚拟环境 (推荐)
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python -m venv venv
source venv/bin/activate
```

### 3. 安装依赖
```bash
pip install -r requirements.txt
```

### 4. 配置环境变量
创建 `.env` 文件并配置：

```bash

# 第三方API转发平台配置 (推荐)
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_API_KEY=your_third_party_key
THIRD_PARTY_BASE_URL=https://your-api-provider.com/v1
THIRD_PARTY_MODEL=gpt-3.5-turbo

# 应用配置
MAX_FILE_SIZE=50MB
DEBUG=false
LOG_LEVEL=INFO
```

### 5. 启动应用


```bash
streamlit run app.py
```

### 6. 访问应用
打开浏览器访问: **http://localhost:8501**

## 🏗️ 项目架构

```
document_analysis_system/
├── 📱 app.py                    # 主应用入口
├── 📦 requirements.txt          # 依赖包列表
├── 🚀 start.bat / start.sh      # 启动脚本
│
├── 🤖 agents/                   # 智能体模块
│   ├── base_agent.py           # 智能体基类
│   ├── qa_agent.py             # 问答智能体
│   ├── analysis_agent.py       # 分析智能体
│   ├── mcp_agent.py            # MCP增强智能体
│   └── report_agent.py         # 报告生成智能体
│
├── 🔌 mcp_services/            # MCP服务层
│   ├── base_service.py         # MCP基础服务
│   ├── document_parser.py      # 文档解析服务
│   ├── file_operations.py      # 文件操作服务
│   ├── modern_mcp_server.py    # 现代化MCP服务器
│   └── models.py               # 数据模型定义
│
├── 🌊 workflows/               # 工作流引擎
│   ├── base_workflow.py        # 工作流基类
│   └── document_workflow.py    # 文档处理工作流
│
├── 🛠️ utils/                   # 工具模块
│   ├── file_utils.py           # 文件处理工具
│   ├── llm_utils.py            # LLM工具
│   ├── data_utils.py           # 数据处理工具
│   └── logger.py               # 日志工具
│
├── 🎨 ui/                      # 用户界面模块
│   ├── app_config.py           # 应用配置
│   ├── sidebar_components.py   # 侧边栏组件
│   ├── document_qa_handler.py  # 问答处理器
│   ├── data_analysis_handler.py # 数据分析处理器
│   └── report_components.py    # 报告组件
│
├── ⚙️ config/                  # 配置模块
│   └── settings.py             # 系统设置
│
├── 📁 uploads/                 # 上传文件目录
├── 📊 outputs/                 # 输出文件目录
├── 📝 logs/                    # 日志目录
└── 🗂️ temp/                    # 临时文件目录
```

## 🎯 主要功能

### 1. 📄 智能文档问答
- **多轮对话**: 支持上下文相关的连续对话
- **精准定位**: 引用具体文档段落和页码
- **多文档**: 跨文档信息整合和对比分析
- **语义理解**: 深度理解文档语义和逻辑关系

### 2. 📊 智能数据分析
- **自动识别**: 智能识别数据类型和结构
- **统计分析**: 描述性统计、相关性分析、假设检验
- **时间序列**: 趋势分析、季节性分解、预测建模
- **可视化**: 自动生成专业图表和交互式图形

### 3. 📋 对话报告生成
- **会话记录**: 完整记录用户与AI的对话过程
- **结构化报告**: 自动生成Markdown格式的分析报告
- **导出功能**: 支持多种格式导出 (HTML、PDF、Word)
- **模板定制**: 可自定义报告模板和样式

### 4. 🔧 高级特性
- **MCP协议**: 现代化的模型-上下文协议实现
- **异步处理**: 高性能并发处理能力
- **流式输出**: 实时显示AI生成过程
- **错误恢复**: 智能的错误处理和重试机制

## 🔧 技术栈

### 前端技术
- **Streamlit**: 现代化Web应用框架
- **plotly/matplotlib**: 数据可视化
- **HTML/CSS**: 自定义样式和布局

### 后端技术
- **FastAPI**: 高性能API框架
- **asyncio**: 异步编程支持
- **pandas/numpy**: 数据处理和分析
- **statsmodels/scipy**: 统计分析

### 文档处理
- **python-docx**: Word文档处理
- **python-pptx**: PowerPoint处理
- **openpyxl**: Excel文档处理
- **PyPDF2/pdfplumber**: PDF文档处理

### AI模型支持
- **Ollama**: 本地大语言模型
- **OpenAI API**: GPT系列模型
- **第三方平台**: OneAPI、FastGPT等转发平台
- **MCP协议**: 标准化的模型交互协议

## 🚦 使用指南

### 基础使用流程
1. **上传文档** → 支持拖拽上传或文件选择器
2. **选择模式** → 智能问答 / 数据分析 / 对话报告
3. **交互操作** → 自然语言提问或分析请求
4. **查看结果** → 实时显示AI响应和分析结果
5. **导出报告** → 下载分析报告或对话记录

### 高级功能
- **批量处理**: 同时上传多个文档进行联合分析
- **自定义提示**: 使用自定义提示词优化AI响应
- **模型切换**: 在不同AI模型间灵活切换
- **工作流配置**: 自定义文档处理工作流

## 📋 环境配置详解


### 第三方API配置
支持多种第三方API转发平台：
- **OneAPI**: 统一API管理平台
- **FastGPT**: 知识库问答平台  
- **Azure OpenAI**: 微软Azure平台
- **Cloudflare Workers AI**: Cloudflare AI服务

## 🐛 常见问题

### Q: 启动时提示端口占用
A: 修改Streamlit默认端口：
```bash
streamlit run app.py --server.port 8502
```

### Q: 文档解析失败
A: 确认文档格式和大小：
- 支持格式：.docx, .pptx, .xlsx, .pdf
- 文件大小：默认限制50MB
- 编码格式：建议UTF-8

### Q: 内存占用过高
A: 优化配置：
```bash
# 限制模型tokens
OLLAMA_MAX_TOKENS=1000
OPENAI_MAX_TOKENS=2000

# 启用文件分块处理
ENABLE_CHUNKING=true
CHUNK_SIZE=1000
```


### 开发规范
- 遵循PEP 8代码规范
- 添加适当的注释和文档
- 编写单元测试覆盖新功能
- 确保向后兼容性

## 📄 许可证

本项目采用 **MIT License** 开源协议。详情请参阅 [LICENSE](LICENSE) 文件。

## 🙏 致谢

感谢以下开源项目和技术的支持：
- [Streamlit](https://streamlit.io/) - Web应用框架
- [Ollama](https://ollama.ai/) - 本地LLM部署
- [MCP Protocol](https://modelcontextprotocol.io/) - 模型上下文协议
- [OpenAI](https://openai.com/) - GPT系列模型

---

⭐ 如果这个项目对您有帮助，请给我们一个Star！
