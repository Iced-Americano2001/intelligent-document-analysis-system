from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field
import asyncio
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class MCPRequest(BaseModel):
    """MCP请求模型 - 简化版"""
    method: str
    params: Dict[str, Any]
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class MCPResponse(BaseModel):
    """MCP响应模型 - 简化版"""
    result: Optional[Dict[str, Any]] = None
    error: Optional[Dict[str, Any]] = None
    id: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.now)

class MCPError(BaseModel):
    """MCP错误模型"""
    code: int
    message: str
    data: Optional[Dict[str, Any]] = None

class BaseMCPService(ABC):
    """MCP服务基类 - 简化版"""
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.capabilities = []
        self.methods = {}
        
    @abstractmethod
    async def initialize(self) -> bool:
        """初始化服务"""
        pass
    
    def register_method(self, method_name: str, handler):
        """注册方法处理器"""
        self.methods[method_name] = handler
        logger.info(f"服务 {self.service_name} 注册方法: {method_name}")
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """处理请求"""
        try:
            method_name = request.method
            if method_name not in self.methods:
                return MCPResponse(
                    error={"code": -32601, "message": f"方法未找到: {method_name}"},
                    id=request.id
                )
            
            handler = self.methods[method_name]
            result = await handler(request.params)
            
            return MCPResponse(
                result={"success": True, "result": result},
                id=request.id
            )
            
        except Exception as e:
            logger.error(f"处理请求失败: {e}")
            return MCPResponse(
                error={"code": -32603, "message": f"内部错误: {str(e)}"},
                id=request.id
            )
    
    def get_service_info(self) -> Dict[str, Any]:
        """获取服务信息"""
        return {
            "name": self.service_name,
            "version": "1.0.0",
            "capabilities": self.capabilities,
            "methods": list(self.methods.keys())
        }

class MCPService(BaseMCPService):
    """通用MCP服务实现"""
    
    def __init__(self, service_name: str = "generic_service"):
        super().__init__(service_name)
        
    async def initialize(self) -> bool:
        """初始化服务"""
        logger.info(f"初始化服务: {self.service_name}")
        return True

class MCPServiceManager:
    """MCP服务管理器 - 简化版"""
    
    def __init__(self):
        self.services: Dict[str, BaseMCPService] = {}
        
    def register_service(self, service: BaseMCPService) -> None:
        """注册服务"""
        self.services[service.service_name] = service
        logger.info(f"服务已注册: {service.service_name}")
    
    async def initialize_all_services(self) -> bool:
        """初始化所有服务"""
        try:
            for service_name, service in self.services.items():
                success = await service.initialize()
                if not success:
                    logger.error(f"服务初始化失败: {service_name}")
                    return False
            logger.info("所有服务初始化完成")
            return True
        except Exception as e:
            logger.error(f"服务初始化异常: {e}")
            return False
    
    async def handle_request(self, service_name: str, request: MCPRequest) -> MCPResponse:
        """处理服务请求"""
        if service_name not in self.services:
            return MCPResponse(
                error={"code": -32601, "message": f"服务未找到: {service_name}"},
                id=request.id
            )
        
        service = self.services[service_name]
        return await service.handle_request(request)
    
    def get_all_services(self) -> Dict[str, Any]:
        """获取所有服务信息"""
        return {
            name: service.get_service_info() 
            for name, service in self.services.items()
        }

# 全局服务管理器实例
mcp_manager = MCPServiceManager()

# 简化的请求处理函数
async def handle_mcp_request(method: str, params: Dict[str, Any], 
                           service_name: Optional[str] = None) -> Dict[str, Any]:
    """处理MCP请求的便捷函数"""
    try:
        # 解析服务名和方法
        if "/" in method and service_name is None:
            service_name, method_name = method.split("/", 1)
        else:
            method_name = method
            service_name = service_name or "default"
        
        logger.info(f"处理MCP请求: 服务={service_name}, 方法={method_name}")
        logger.info(f"可用服务: {list(mcp_manager.services.keys())}")
        
        # 创建请求
        request = MCPRequest(method=method_name, params=params)
        
        # 处理请求
        response = await mcp_manager.handle_request(service_name, request)
        
        # 返回结果
        return response.dict()
        
    except Exception as e:
        logger.error(f"MCP请求处理失败: {e}")
        return {
            "error": {"code": -32603, "message": f"请求处理失败: {str(e)}"},
            "result": None
        }
