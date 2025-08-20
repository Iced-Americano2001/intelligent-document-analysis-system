"""
工具基类定义
使用现代化的Python语法和类型注解
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union, AsyncIterator, Callable
from pydantic import BaseModel, Field
from loguru import logger

from mcp_services.models import ToolDefinition, ToolParameter, ToolParameterType


class BaseTool(ABC):
    """工具基类"""
    
    def __init__(self):
        self.name = self.get_name()
        self.description = self.get_description()
        self.definition = self.get_definition()
    
    @abstractmethod
    def get_name(self) -> str:
        """获取工具名称"""
        pass
    
    @abstractmethod
    def get_description(self) -> str:
        """获取工具描述"""
        pass
    
    @abstractmethod
    def get_parameters(self) -> Dict[str, ToolParameter]:
        """获取工具参数定义"""
        pass
    
    @abstractmethod
    def get_required_parameters(self) -> List[str]:
        """获取必需参数列表"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> Dict[str, Any]:
        """执行工具逻辑"""
        pass
    
    def get_definition(self) -> ToolDefinition:
        """获取完整的工具定义"""
        return ToolDefinition(
            name=self.get_name(),
            description=self.get_description(),
            parameters=self.get_parameters(),
            required_parameters=self.get_required_parameters()
        )
    
    async def validate_parameters(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """验证和清理参数"""
        tool_params = self.get_parameters()
        required_params = self.get_required_parameters()
        
        # 检查必需参数
        for param_name in required_params:
            if param_name not in parameters:
                raise ValueError(f"缺少必需参数: {param_name}")
        
        # 验证和转换参数类型
        validated_params = {}
        for param_name, param_value in parameters.items():
            if param_name in tool_params:
                param_def = tool_params[param_name]
                validated_params[param_name] = self._validate_parameter_type(
                    param_name, param_value, param_def
                )
            else:
                logger.warning(f"未知参数: {param_name}")
                validated_params[param_name] = param_value
        
        return validated_params
    
    def _validate_parameter_type(self, param_name: str, value: Any, param_def: ToolParameter) -> Any:
        """验证单个参数类型"""
        if value is None:
            if param_def.required:
                raise ValueError(f"参数 {param_name} 不能为空")
            return param_def.default
        
        try:
            if param_def.type == ToolParameterType.STRING:
                return str(value)
            elif param_def.type == ToolParameterType.INTEGER:
                return int(value)
            elif param_def.type == ToolParameterType.NUMBER:
                return float(value)
            elif param_def.type == ToolParameterType.BOOLEAN:
                if isinstance(value, bool):
                    return value
                return str(value).lower() in ('true', '1', 'yes', 'on')
            elif param_def.type == ToolParameterType.ARRAY:
                if isinstance(value, list):
                    return value
                return [value]
            elif param_def.type == ToolParameterType.OBJECT:
                if isinstance(value, dict):
                    return value
                raise ValueError(f"参数 {param_name} 必须是对象类型")
            else:
                return value
        except (ValueError, TypeError) as e:
            raise ValueError(f"参数 {param_name} 类型转换失败: {e}")
    
    async def safe_execute(self, **kwargs) -> Dict[str, Any]:
        """安全执行工具，包含错误处理"""
        try:
            # 验证参数
            validated_params = await self.validate_parameters(kwargs)
            
            # 执行工具
            result = await self.execute(**validated_params)
            
            # 确保返回字典格式
            if not isinstance(result, dict):
                result = {"output": result}
            
            result["success"] = True
            return result
            
        except Exception as e:
            logger.error(f"工具执行失败: {self.name}, 错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": self.name
            }
    
    def to_openai_format(self) -> Dict[str, Any]:
        """转换为OpenAI Function Calling格式"""
        return self.definition.to_openai_format()


class ToolRegistry:
    """工具注册表"""
    
    def __init__(self):
        self.tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool):
        """注册工具"""
        self.tools[tool.name] = tool
        logger.info(f"注册工具: {tool.name}")
    
    def unregister(self, tool_name: str):
        """注销工具"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            logger.info(f"注销工具: {tool_name}")
    
    def get_tool(self, tool_name: str) -> Optional[BaseTool]:
        """获取工具"""
        return self.tools.get(tool_name)
    
    def list_tools(self) -> List[BaseTool]:
        """列出所有工具"""
        return list(self.tools.values())
    
    def get_tool_definitions(self) -> List[ToolDefinition]:
        """获取所有工具定义"""
        return [tool.definition for tool in self.tools.values()]
    
    def get_openai_functions(self) -> List[Dict[str, Any]]:
        """获取OpenAI Function Calling格式的工具定义"""
        return [tool.to_openai_format() for tool in self.tools.values()]


# 全局工具注册表
tool_registry = ToolRegistry()


def register_tool(cls: type[BaseTool]) -> type[BaseTool]:
    """工具注册装饰器"""
    tool_instance = cls()
    tool_registry.register(tool_instance)
    return cls