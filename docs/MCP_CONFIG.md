# MCP配置说明 (Model Context Protocol Configuration)

## 概述

本系统支持完整的MCP (Model Context Protocol) 协议实现，提供现代化的工具调用、多轮推理和流式交互功能。

## 快速开始

1. **复制配置文件**
   ```bash
   cp .env.example .env
   ```

2. **基础配置**
   ```bash
   # 确保Ollama正在运行
   ollama serve
   
   # 启动系统
   streamlit run app.py
   ```

## MCP服务器配置

### 服务器地址配置

**方式1: 直接填写完整URL（推荐）**
```env
# MCP服务器启用状态
MCP_SERVER_ENABLED=true

# 直接填写streamable服务的完整URL
MCP_SERVER_URL=https://your-streamable-service.com/mcp
```

**方式2: 分离host和port（向后兼容）**
```env
# 去掉 https:// 只填写域名
MCP_SERVER_HOST=your-streamable-service.com
MCP_SERVER_PORT=443  # HTTPS默认端口443，HTTP为80
```

**配置示例**:
- 本地服务: `MCP_SERVER_URL=http://localhost:8503`
- 远程HTTPS: `MCP_SERVER_URL=https://api.example.com/mcp/v1`
- 分离配置: `MCP_SERVER_HOST=api.example.com` + `MCP_SERVER_PORT=443`

### 流式响应配置

```env
# 启用HTTP流式响应
MCP_STREAMING_ENABLED=true

# 流式响应超时时间（秒）
MCP_STREAM_TIMEOUT=30
```

### 工具系统配置

```env
# 启用MCP工具系统
MCP_TOOLS_ENABLED=true

# 自动注册所有可用工具
MCP_TOOLS_AUTO_REGISTER=true
```

## MCP智能体配置

### 核心参数

```env
# 最大思考轮数（防止无限循环）
MCP_AGENT_MAX_ITERATIONS=10

# 智能体超时时间（秒）
MCP_AGENT_TIMEOUT=120

# 显示思考过程（在UI中展示推理步骤）
MCP_AGENT_SHOW_THINKING=true
```

### 调试配置

```env
# 开启MCP调试模式
MCP_DEBUG=false

# 记录工具调用日志
MCP_LOG_TOOL_CALLS=true
```

## 工具系统架构

### 自动工具注册

系统会自动扫描 `tools/` 目录下的所有工具模块，并注册带有 `@register_tool` 装饰器的工具。

```python
@register_tool
class DocumentParserTool(BaseTool):
    def get_name(self) -> str:
        return "document_parser"
    
    def get_description(self) -> str:
        return "解析文档并提取文本内容"
```

### 可用工具类型

1. **文档处理工具** (`tools/document_tools.py`)
   - `document_parser`: 解析PDF、Word、PPT等文档
   - `document_analyzer`: 分析文档结构和内容
   - `document_search`: 在文档中搜索特定内容

2. **网络工具** (`tools/web_tools.py`)
   - 已移除 `web_search`（请使用远程MCP提供的搜索工具）
   - `url_fetch`: 获取网页内容

3. **文件操作工具** (`tools/file_tools.py`)
   - `file_read`: 读取文件内容
   - `file_write`: 写入文件
   - `directory_list`: 列出目录内容

## 流式UI配置

### 思考过程展示

系统支持实时显示AI的思考过程：

- **思考盒子**: 显示AI的分析和推理步骤
- **工具调用盒子**: 展示工具执行状态和结果
- **状态管理**: 完整的进度跟踪和性能监控

### UI组件配置

```python
# 在应用中的配置示例
if agent_type == "MCP智能助手":
    # MCP特定选项
    max_iterations = st.number_input("最大思考轮数", min_value=3, max_value=20, value=10)
    show_thinking = st.checkbox("显示思考过程", value=True)
```

## LLM提供商配置

### Ollama (推荐)
```env
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=llama3.2:3b
OLLAMA_TIMEOUT=120
```

### OpenAI兼容API
```env
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai.com/v1
```

### 第三方API转发
```env
THIRD_PARTY_API_ENABLED=true
THIRD_PARTY_API_KEY=your_key
THIRD_PARTY_BASE_URL=https://your-service.com/v1
THIRD_PARTY_PROVIDER=openai
```

## 性能优化

### 并发和内存
```env
MAX_WORKERS=4          # 并发处理数量
MAX_MEMORY_MB=1024     # 内存限制
ENABLE_CACHE=true      # 启用缓存
CACHE_TTL=3600         # 缓存有效期
```

### MCP特定优化
```env
MCP_MAX_CONNECTIONS=100    # 最大连接数
MCP_STREAM_TIMEOUT=30      # 流式超时
```

## 安全考虑

### 网络安全
```env
CORS_ORIGINS=http://localhost:8501,http://127.0.0.1:8501
SECRET_KEY=strong_random_key_in_production
```

### 工具安全

所有工具调用都经过安全验证：
- 参数类型检查
- 文件路径安全验证
- 网络访问控制
- 错误处理和日志记录

## 故障排除

### 常见问题

1. **MCP服务器无法启动**
   ```bash
   # 检查端口占用
   netstat -an | find "8503"
   
   # 更换端口
   MCP_SERVER_PORT=8504
   ```

2. **工具注册失败**
   ```python
   # 检查工具导入
   from tools.base_tool import tool_registry
   print(tool_registry.list_tools())
   ```

3. **流式响应中断**
   ```env
   # 增加超时时间
   MCP_STREAM_TIMEOUT=60
   MCP_AGENT_TIMEOUT=180
   ```

### 调试模式

启用调试获取详细信息：
```env
MCP_DEBUG=true
LOG_LEVEL=DEBUG
```

## 高级配置

### 自定义工具开发

1. **创建工具类**
   ```python
   @register_tool
   class CustomTool(BaseTool):
       def get_name(self) -> str:
           return "custom_tool"
       
       async def execute(self, **kwargs) -> Dict[str, Any]:
           # 工具逻辑实现
           return {"result": "success"}
   ```

2. **注册到系统**
   - 将工具文件放在 `tools/` 目录
   - 在 `tools/__init__.py` 中导入
   - 系统会自动注册

### 自定义智能体

扩展 `MCPAgent` 类创建专用智能体：

```python
class CustomMCPAgent(MCPAgent):
    async def _analyze_and_plan(self) -> str:
        # 自定义分析逻辑
        return "custom analysis"
```