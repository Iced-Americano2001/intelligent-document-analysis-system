# 智能文档分析系统

基于MCP (Model Context Protocol) 和多智能体架构的文档分析系统，支持Word、PowerPoint、Excel、PDF等文档格式的智能问答和数据分析。

## 🚀 快速开始

### 1. 环境要求
- Python 3.8+
- Ollama (推荐) 或 OpenAI API

### 2. 安装依赖
```bash
pip install -r requirements.txt
```

### 3. 配置环境
创建并编辑环境配置文件：
```bash
# 复制示例配置文件
cp .env.example .env
```

配置Ollama (推荐)：
```bash
# 安装Ollama后下载模型
ollama pull llama3.2:3b
```

或配置OpenAI API：
```bash
# 在.env文件中设置
OPENAI_API_KEY=your_api_key
```

### 4. 启动应用

**Windows:**
```bash
start.bat
```

**Linux/Mac:**
```bash
./start.sh
```

**或直接运行:**
```bash
streamlit run app.py
```

### 5. 访问应用
打开浏览器访问: http://localhost:8501

## 📁 项目结构

```
document_analysis_system/
├── app.py                  # 主应用入口
├── requirements.txt        # 依赖包列表  
├── start.bat              # Windows启动脚本
├── start.sh               # Linux/Mac启动脚本
├── .env                   # 环境变量配置
├── README.md              # 项目说明
├── 开发文档.md            # 详细开发文档
│
├── agents/                # 智能体模块
│   ├── base_agent.py      # 智能体基类
│   ├── qa_agent.py        # 问答智能体
│   └── analysis_agent.py  # 分析智能体
│
├── mcp_services/          # MCP服务模块
│   ├── base_service.py    # MCP基础服务类
│   ├── document_parser.py # 文档解析服务
│   └── file_operations.py # 文件操作服务
│
├── workflows/             # 工作流模块
│   ├── base_workflow.py   # 工作流基类
│   └── document_workflow.py # 文档处理工作流
│
├── utils/                 # 工具模块
│   ├── file_utils.py      # 文件处理工具
│   ├── llm_utils.py       # 大语言模型工具
│   └── data_utils.py      # 数据处理工具
│
├── config/                # 配置模块
│   └── settings.py        # 系统配置
│
├── uploads/               # 上传文件目录
├── outputs/               # 输出文件目录
└── temp/                  # 临时文件目录
```

## 💡 主要功能

### 文档支持格式
- 📄 Word文档 (.docx)
- 📊 PowerPoint演示文稿 (.pptx)  
- 📈 Excel表格 (.xlsx)
- 📃 PDF文档 (.pdf)

### 核心功能
- 🤖 **智能问答**: 基于文档内容的问答
- 📊 **数据分析**: 自动提取和分析数据
- 🔍 **内容摘要**: 生成文档摘要和关键信息
- 📋 **结构化提取**: 提取表格、图表等结构化数据

## 🔧 技术栈

- **前端**: Streamlit
- **后端**: Python + FastAPI
- **文档处理**: python-docx, python-pptx, openpyxl, PyPDF2
- **AI模型**: Ollama (本地) / OpenAI API
- **架构**: MCP (Model Context Protocol) + 多智能体

## 📋 环境配置

### 基本配置 (.env)
```bash
# Ollama配置
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=120

# OpenAI配置 (可选)
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo

# 应用配置
MAX_FILE_SIZE=50MB
DEBUG=false
LOG_LEVEL=INFO
```

## 🚦 使用说明

1. **上传文档**: 支持拖拽或选择文件上传
2. **选择模式**: 文档问答或数据分析
3. **交互操作**: 提问或查看分析结果
4. **下载结果**: 导出分析报告或问答记录

## 📚 更多信息

- **详细开发文档**: [开发文档.md](开发文档.md)
- **第三方API配置**: [docs/third_party_api_guide.md](docs/third_party_api_guide.md)

## 🤝 贡献

欢迎提交Issue和Pull Request来改进项目！

## 📄 许可证

MIT License
