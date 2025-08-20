import os
from dotenv import load_dotenv
from typing import List, Dict, Any

load_dotenv()

# Ollama 配置
OLLAMA_CONFIG = {
    "host": os.getenv("OLLAMA_HOST", "http://localhost:11434"),
    "model": os.getenv("OLLAMA_MODEL", "llama3.2:3b"),
    "timeout": int(os.getenv("OLLAMA_TIMEOUT", "120")),
    "max_tokens": int(os.getenv("OLLAMA_MAX_TOKENS", "2000")),
}

# OpenAI 配置 (支持第三方API转发)
OPENAI_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY", ""),
    "model": os.getenv("OPENAI_MODEL", "gpt-3.5-turbo"),
    "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "4000")),
    # 第三方API转发配置
    "base_url": os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),  # 自定义API端点
    "api_version": os.getenv("OPENAI_API_VERSION", "v1"),
    "timeout": int(os.getenv("OPENAI_TIMEOUT", "60")),
    "proxy": os.getenv("OPENAI_PROXY", ""),  # 代理设置
    "headers": {
        "User-Agent": os.getenv("OPENAI_USER_AGENT", "DocumentAnalysisSystem/1.0"),
        "X-Custom-Source": os.getenv("OPENAI_CUSTOM_SOURCE", "document-analysis"),
    },
    "retry_attempts": int(os.getenv("OPENAI_RETRY_ATTEMPTS", "3")),
    "retry_delay": float(os.getenv("OPENAI_RETRY_DELAY", "1.0")),
}

# Anthropic 配置 (可选)
ANTHROPIC_CONFIG = {
    "api_key": os.getenv("ANTHROPIC_API_KEY", ""),
    "model": os.getenv("ANTHROPIC_MODEL", "claude-3-sonnet-20240229"),
    "max_tokens": int(os.getenv("ANTHROPIC_MAX_TOKENS", "4000")),
}

# 第三方API转发平台配置
THIRD_PARTY_API_CONFIG = {
    # 通用第三方平台配置
    "enabled": os.getenv("THIRD_PARTY_API_ENABLED", "false").lower() == "true",
    "provider": os.getenv("THIRD_PARTY_PROVIDER", "openai"),  # openai, anthropic, custom
    
    # API基础配置
    "api_key": os.getenv("THIRD_PARTY_API_KEY", ""),
    "base_url": os.getenv("THIRD_PARTY_BASE_URL", ""),  # 第三方转发平台的URL
    "api_version": os.getenv("THIRD_PARTY_API_VERSION", "v1"),
    
    # 模型配置
    "model": os.getenv("THIRD_PARTY_MODEL", "gpt-3.5-turbo"),
    "max_tokens": int(os.getenv("THIRD_PARTY_MAX_TOKENS", "4000")),
    "temperature": float(os.getenv("THIRD_PARTY_TEMPERATURE", "0.7")),
    
    # 请求配置
    "timeout": int(os.getenv("THIRD_PARTY_TIMEOUT", "60")),
    "retry_attempts": int(os.getenv("THIRD_PARTY_RETRY_ATTEMPTS", "3")),
    "retry_delay": float(os.getenv("THIRD_PARTY_RETRY_DELAY", "1.0")),
    
    # 自定义请求头
    "headers": {
        "User-Agent": os.getenv("THIRD_PARTY_USER_AGENT", "DocumentAnalysisSystem/1.0"),
        "X-Source": os.getenv("THIRD_PARTY_SOURCE", "document-analysis"),
        "Authorization": f"Bearer {os.getenv('THIRD_PARTY_API_KEY', '')}",
    },
    
    # 代理和网络配置
    "proxy": os.getenv("THIRD_PARTY_PROXY", ""),
    "verify_ssl": os.getenv("THIRD_PARTY_VERIFY_SSL", "true").lower() == "true",
    
    # 速率限制
    "rate_limit": {
        "requests_per_minute": int(os.getenv("THIRD_PARTY_RPM", "60")),
        "tokens_per_minute": int(os.getenv("THIRD_PARTY_TPM", "60000")),
    },
    
    # 常见第三方平台预设
    "presets": {
        "oneapi": {
            "base_url_suffix": "/v1/chat/completions",
            "auth_header": "Authorization",
            "auth_prefix": "Bearer ",
        },
        "fastgpt": {
            "base_url_suffix": "/api/v1/chat/completions", 
            "auth_header": "Authorization",
            "auth_prefix": "Bearer ",
        },
        "azure": {
            "base_url_suffix": "/openai/deployments/{deployment_id}/chat/completions",
            "auth_header": "api-key",
            "auth_prefix": "",
            "api_version": "2023-12-01-preview",
        },
        "cloudflare": {
            "base_url_suffix": "/v1/chat/completions",
            "auth_header": "Authorization", 
            "auth_prefix": "Bearer ",
        },
    }
}

# 文件处理配置
FILE_CONFIG = {
    "max_file_size": os.getenv("MAX_FILE_SIZE", "50MB"),
    "supported_formats": os.getenv("SUPPORTED_FORMATS", ".doc,.docx,.pptx,.xlsx,.pdf").split(","),
    "upload_dir": os.getenv("UPLOAD_DIR", "uploads/"),
    "output_dir": os.getenv("OUTPUT_DIR", "outputs/"),
    "temp_dir": os.getenv("TEMP_DIR", "temp/"),
}

# MCP服务器配置 (Model Context Protocol)
MCP_CONFIG = {
    "enabled": os.getenv("MCP_SERVER_ENABLED", "true").lower() == "true",
    
    # 方式1: 完整URL配置 (优先使用)
    "server_url": os.getenv("MCP_SERVER_URL", ""),
    
    # 方式2: 分离配置 (向后兼容)
    "host": os.getenv("MCP_SERVER_HOST", "localhost"),
    "port": int(os.getenv("MCP_SERVER_PORT", "8503")),
    
    # 流式响应配置
    "streaming_enabled": os.getenv("MCP_STREAMING_ENABLED", "true").lower() == "true",
    "stream_timeout": int(os.getenv("MCP_STREAM_TIMEOUT", "30")),
    
    # 工具配置
    "tools_enabled": os.getenv("MCP_TOOLS_ENABLED", "true").lower() == "true",
    "tools_auto_register": os.getenv("MCP_TOOLS_AUTO_REGISTER", "true").lower() == "true",
    
    # 智能体配置
    "agent_max_iterations": int(os.getenv("MCP_AGENT_MAX_ITERATIONS", "10")),
    "agent_timeout": int(os.getenv("MCP_AGENT_TIMEOUT", "120")),
    "agent_show_thinking": os.getenv("MCP_AGENT_SHOW_THINKING", "true").lower() == "true",
    
    # 调试配置
    "debug": os.getenv("MCP_DEBUG", "false").lower() == "true",
    "log_tool_calls": os.getenv("MCP_LOG_TOOL_CALLS", "true").lower() == "true",
    
    # 传统配置保持兼容
    "max_connections": int(os.getenv("MCP_MAX_CONNECTIONS", "100")),
    "timeout": int(os.getenv("MCP_TIMEOUT", "30")),
}

# 系统配置
SYSTEM_CONFIG = {
    "debug": os.getenv("DEBUG", "True").lower() == "true",
    "log_level": os.getenv("LOG_LEVEL", "INFO"),
    "log_file": os.getenv("LOG_FILE", "logs/document_analysis.log"),
    "max_concurrent_tasks": int(os.getenv("MAX_CONCURRENT_TASKS", "5")),
    "cache_enabled": os.getenv("CACHE_ENABLED", "True").lower() == "true",
    "cache_ttl": int(os.getenv("CACHE_TTL", "3600")),  # 1小时
}

# 智能体配置
AGENT_CONFIG = {
    "qa_agent": {
        "name": "QA_Agent",
        "description": "文档问答智能体",
        "max_context_length": 4000,
        "temperature": 0.7,
    },
    "analysis_agent": {
        "name": "Analysis_Agent", 
        "description": "数据分析智能体",
        "max_context_length": 8000,
        "temperature": 0.3,
    },
    "report_agent": {
        "name": "Report_Agent",
        "description": "报告生成智能体", 
        "max_context_length": 6000,
        "temperature": 0.5,
    },
}

# 工作流配置
WORKFLOW_CONFIG = {
    "default_timeout": 300,  # 5分钟
    "retry_attempts": 3,
    "retry_delay": 5,  # 秒
    "parallel_processing": True,
    "save_intermediate_results": True,
}

# 提示词模板
PROMPT_TEMPLATES = {
    "document_qa": """
你是一个专业的文档分析助手。请基于以下文档内容回答用户的问题。

文档内容:
{document_content}

用户问题: {question}

请提供准确、详细的回答，如果文档中没有相关信息，请明确说明。

回答:
""",
    
    "data_analysis": """
你是一个专业的数据分析师。请分析以下数据并提供洞察。

数据概览:
{data_summary}

数据详情:
{data_details}

分析要求: {analysis_requirements}

请提供以下内容:
1. 数据概述
2. 关键发现
3. 趋势分析
4. 建议和结论

分析结果:
""",
    
    "report_generation": """
你是一个专业的报告撰写专家。请基于以下分析结果生成一份完整的报告。

分析结果:
{analysis_results}

报告要求:
{report_requirements}

请生成一份结构化的报告，包含:
1. 执行摘要
2. 分析过程
3. 主要发现
4. 结论和建议
5. 附录（如需要）

报告内容:
""",
}

# 数据分析配置
ANALYSIS_CONFIG = {
    "statistical_methods": ["mean", "median", "std", "correlation", "regression"],
    "visualization_types": ["line", "bar", "scatter", "heatmap", "box"],
    "default_chart_size": (10, 6),
    "color_palette": "viridis",
    "output_formats": ["png", "pdf", "svg", "html"],
}

def get_config(section: str) -> Dict[str, Any]:
    """获取指定配置段"""
    config_map = {
        "llm": {  # 添加LLM配置映射
            "default_provider": "ollama",
            "ollama": OLLAMA_CONFIG,
            "openai": OPENAI_CONFIG,
            "anthropic": ANTHROPIC_CONFIG,
            "third_party": THIRD_PARTY_API_CONFIG,
        },
        "ollama": OLLAMA_CONFIG,
        "openai": OPENAI_CONFIG,
        "anthropic": ANTHROPIC_CONFIG,
        "third_party": THIRD_PARTY_API_CONFIG,
        "file": FILE_CONFIG,
        "mcp": MCP_CONFIG,
        "system": SYSTEM_CONFIG,
        "agent": AGENT_CONFIG,
        "workflow": WORKFLOW_CONFIG,
        "analysis": ANALYSIS_CONFIG,
    }
    return config_map.get(section, {})

def get_supported_formats() -> List[str]:
    """获取支持的文件格式列表"""
    return [fmt.strip() for fmt in FILE_CONFIG["supported_formats"]]

def is_file_supported(filename: str) -> bool:
    """检查文件格式是否受支持"""
    file_ext = os.path.splitext(filename)[1].lower()
    return file_ext in get_supported_formats()

def get_prompt_template(template_name: str) -> str:
    """获取提示词模板"""
    return PROMPT_TEMPLATES.get(template_name, "")

def get_third_party_config(preset_name: str = None) -> Dict[str, Any]:
    """获取第三方API配置，支持预设"""
    config = THIRD_PARTY_API_CONFIG.copy()
    
    if preset_name and preset_name in config["presets"]:
        preset = config["presets"][preset_name]
        # 应用预设配置
        if "base_url_suffix" in preset:
            base_url = config.get("base_url", "").rstrip("/")
            config["full_url"] = base_url + preset["base_url_suffix"]
        
        # 更新认证头
        if "auth_header" in preset:
            auth_value = preset.get("auth_prefix", "") + config.get("api_key", "")
            config["headers"][preset["auth_header"]] = auth_value
        
        # 更新API版本
        if "api_version" in preset:
            config["api_version"] = preset["api_version"]
    
    return config

def is_third_party_enabled() -> bool:
    """检查是否启用第三方API"""
    return THIRD_PARTY_API_CONFIG.get("enabled", False)

def get_active_llm_config() -> Dict[str, Any]:
    """获取当前激活的LLM配置"""
    if is_third_party_enabled():
        return get_third_party_config()
    
    # 检查各个配置的可用性
    if OPENAI_CONFIG.get("api_key"):
        return OPENAI_CONFIG
    elif ANTHROPIC_CONFIG.get("api_key"):
        return ANTHROPIC_CONFIG
    else:
        return OLLAMA_CONFIG  # 默认使用Ollama

def validate_api_config(config: Dict[str, Any]) -> bool:
    """验证API配置是否完整"""
    required_fields = ["api_key", "model"]
    
    if config.get("base_url"):  # 如果有自定义base_url，需要验证
        required_fields.append("base_url")
    
    for field in required_fields:
        if not config.get(field):
            return False
    
    return True

# MCP服务器辅助函数
def is_mcp_enabled() -> bool:
    """检查MCP服务器是否启用"""
    return MCP_CONFIG.get("enabled", True)

def get_mcp_server_url() -> str:
    """获取MCP服务器完整URL - 智能处理两种配置方式"""
    
    # 方式1: 优先使用完整URL配置
    server_url = MCP_CONFIG.get("server_url", "").strip()
    if server_url:
        return server_url
    
    # 方式2: 从host和port构建URL (向后兼容)
    host = MCP_CONFIG.get("host", "localhost")
    port = MCP_CONFIG.get("port", 8503)
    
    # 智能判断协议
    if port == 443:
        protocol = "https"
        url = f"{protocol}://{host}"
    elif port == 80:
        protocol = "http" 
        url = f"{protocol}://{host}"
    else:
        protocol = "https" if port == 443 else "http"
        url = f"{protocol}://{host}:{port}"
    
    return url

def get_mcp_agent_config() -> Dict[str, Any]:
    """获取MCP智能体配置"""
    return {
        "max_iterations": MCP_CONFIG.get("agent_max_iterations", 10),
        "timeout": MCP_CONFIG.get("agent_timeout", 120),
        "show_thinking": MCP_CONFIG.get("agent_show_thinking", True),
        "debug": MCP_CONFIG.get("debug", False),
        "log_tool_calls": MCP_CONFIG.get("log_tool_calls", True),
    }

def is_mcp_streaming_enabled() -> bool:
    """检查MCP流式响应是否启用"""
    return MCP_CONFIG.get("streaming_enabled", True)

def is_mcp_tools_auto_register() -> bool:
    """检查MCP工具是否自动注册"""
    return MCP_CONFIG.get("tools_auto_register", True)
