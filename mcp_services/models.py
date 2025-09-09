"""
MCP协议相关的数据模型定义
使用现代化的Pydantic v2语法
"""

from typing import Any, Dict, List, Optional, Union, AsyncIterator, Literal
from pydantic import BaseModel, Field, ConfigDict
from datetime import datetime
from enum import Enum
import uuid


class MessageRole(str, Enum):
    """消息角色枚举"""
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"


class ThoughtType(str, Enum):
    """思考过程类型枚举"""
    THINKING = "thinking"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result" 
    FINAL_ANSWER = "final_answer"
    ERROR = "error"


class ToolParameterType(str, Enum):
    """工具参数类型枚举"""
    STRING = "string"
    NUMBER = "number"
    INTEGER = "integer"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class MCPMessage(BaseModel):
    """MCP消息基类"""
    model_config = ConfigDict(
        extra="forbid",
        use_enum_values=True,
        validate_assignment=True
    )
    
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.now)


class ToolParameter(BaseModel):
    """工具参数定义"""
    model_config = ConfigDict(extra="forbid")
    
    type: ToolParameterType
    description: str
    required: bool = False
    default: Optional[Any] = None
    enum: Optional[List[str]] = None


class ToolDefinition(BaseModel):
    """工具定义模型"""
    model_config = ConfigDict(extra="forbid")
    
    name: str = Field(..., description="工具名称")
    description: str = Field(..., description="工具描述") 
    parameters: Dict[str, ToolParameter] = Field(default_factory=dict)
    required_parameters: List[str] = Field(default_factory=list)
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI Function Calling格式"""
        properties = {}
        for param_name, param_def in self.parameters.items():
            # 安全处理枚举值，支持字符串和枚举对象
            param_type = param_def.type
            if hasattr(param_type, 'value'):
                param_type = param_type.value
            elif isinstance(param_type, str):
                param_type = param_type
            else:
                param_type = str(param_type)
                
            properties[param_name] = {
                "type": param_type,
                "description": param_def.description
            }
            if param_def.enum:
                properties[param_name]["enum"] = param_def.enum
            if param_def.default is not None:
                properties[param_name]["default"] = param_def.default
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": self.required_parameters
                }
            }
        }


class ToolCallRequest(MCPMessage):
    """工具调用请求"""
    tool_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    session_id: Optional[str] = None


class ToolCallResult(MCPMessage):
    """工具调用结果"""
    success: bool
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    execution_time: Optional[float] = None


class ThoughtProcess(MCPMessage):
    """思考过程模型"""
    type: ThoughtType
    content: str
    tool_name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    confidence: Optional[float] = None


class ConversationContext(BaseModel):
    """对话上下文"""
    model_config = ConfigDict(extra="allow")
    
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_query: str
    document_content: Optional[str] = None
    document_type: Optional[str] = None
    document_file_path: Optional[str] = None
    chat_history: List[Dict[str, Any]] = Field(default_factory=list)
    available_tools: List[ToolDefinition] = Field(default_factory=list)
    max_iterations: int = Field(default=10)
    current_iteration: int = Field(default=0)
    is_completed: bool = Field(default=False)
    final_answer: Optional[str] = None
    trend_params: Optional[Dict[str, Any]] = Field(default=None)  # 趋势分析参数
    
    def add_message(self, role: MessageRole, content: str, **kwargs):
        """添加消息到聊天历史"""
        # 安全处理角色枚举值
        role_str = role.value if hasattr(role, 'value') else str(role)
        
        message = {
            "role": role_str,
            "content": content,
            "timestamp": datetime.now().isoformat(),
            **kwargs
        }
        self.chat_history.append(message)
    
    def get_recent_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的聊天历史"""
        return self.chat_history[-limit:] if self.chat_history else []


class MCPStreamResponse(BaseModel):
    """MCP流式响应模型"""
    model_config = ConfigDict(extra="forbid")
    
    event_type: Literal["thought", "tool_call", "tool_result", "final_answer", "error"]
    data: Dict[str, Any]
    timestamp: datetime = Field(default_factory=datetime.now)
    
    def to_sse_format(self) -> str:
        """转换为Server-Sent Events格式"""
        import json
        return f"data: {json.dumps(self.model_dump(), default=str)}\n\n"


class AgentConfig(BaseModel):
    """智能体配置"""
    model_config = ConfigDict(extra="allow")
    
    name: str
    description: str
    llm_provider: str = "ollama"
    temperature: float = 0.7
    max_tokens: int = 2000
    max_iterations: int = 10
    thinking_enabled: bool = True
    tool_calling_enabled: bool = True
    stream_output: bool = True


class ToolExecutionContext(BaseModel):
    """工具执行上下文"""
    model_config = ConfigDict(extra="allow")
    
    tool_name: str
    parameters: Dict[str, Any]
    session_id: str
    conversation_context: ConversationContext
    start_time: datetime = Field(default_factory=datetime.now)
    
    def get_execution_time(self) -> float:
        """获取执行时间"""
        return (datetime.now() - self.start_time).total_seconds()