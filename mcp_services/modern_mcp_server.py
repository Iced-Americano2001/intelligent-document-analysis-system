"""
现代化MCP服务器实现
使用官方MCP库进行标准协议连接
"""

import asyncio
import json
from typing import Dict, List, Optional, AsyncIterator, Callable, Any
from urllib.parse import urlparse, urlunparse
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from contextlib import asynccontextmanager
from loguru import logger

# 使用官方MCP库
MCP_AVAILABLE = False
ClientSession = None
streamablehttp_client = None
StdioServerParameters = None

try:
    import mcp
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.streamable_http import streamablehttp_client
    from mcp.types import Tool, CallToolRequest, CallToolResult
    MCP_AVAILABLE = True
    logger.info("官方MCP库加载成功")
except ImportError as e:
    logger.error(f"官方MCP库加载失败: {e}")
    logger.error("请确保已安装官方MCP库: pip install mcp")
    raise ImportError("必须安装官方MCP库才能连接远程MCP服务器")

from .models import (
    ToolDefinition, ToolCallRequest, ToolCallResult, 
    MCPStreamResponse, ConversationContext, ToolExecutionContext,
    ToolParameter, ToolParameterType
)
from config.settings import get_mcp_server_url


class ModernMCPServer:
    """现代化MCP服务器"""
    
    def __init__(self, host: str = "localhost", port: int = 8765):
        self.host = host
        self.port = port
        self.tools: Dict[str, ToolDefinition] = {}
        self.tool_handlers: Dict[str, Callable] = {}
        self.sessions: Dict[str, ConversationContext] = {}
        self.app = FastAPI(
            title="Modern MCP Server",
            description="现代化MCP协议服务器，支持HTTP Streaming",
            version="1.0.0"
        )
        self._setup_routes()
    
    def _setup_routes(self):
        """设置API路由"""
        
        @self.app.get("/health")
        async def health_check():
            """健康检查端点"""
            return {
                "status": "healthy",
                "version": "1.0.0",
                "tools_count": len(self.tools),
                "active_sessions": len(self.sessions)
            }
        
        @self.app.get("/tools")
        async def list_tools():
            """列出所有可用工具"""
            return {
                "tools": [tool.model_dump() for tool in self.tools.values()]
            }
        
        @self.app.get("/tools/{tool_name}")
        async def get_tool(tool_name: str):
            """获取特定工具的定义"""
            if tool_name not in self.tools:
                raise HTTPException(status_code=404, detail=f"工具 '{tool_name}' 不存在")
            return self.tools[tool_name].model_dump()
        
        @self.app.post("/sessions")
        async def create_session(context: ConversationContext):
            """创建新的会话"""
            self.sessions[context.session_id] = context
            logger.info(f"创建新会话: {context.session_id}")
            return {"session_id": context.session_id, "status": "created"}
        
        @self.app.delete("/sessions/{session_id}")
        async def delete_session(session_id: str):
            """删除会话"""
            if session_id in self.sessions:
                del self.sessions[session_id]
                logger.info(f"删除会话: {session_id}")
                return {"status": "deleted"}
            raise HTTPException(status_code=404, detail="会话不存在")
        
        @self.app.post("/tools/{tool_name}/call")
        async def call_tool(tool_name: str, request: ToolCallRequest):
            """同步调用工具"""
            try:
                result = await self._execute_tool(tool_name, request.parameters, request.session_id)
                return result.model_dump()
            except Exception as e:
                logger.error(f"工具调用失败: {tool_name}, 错误: {e}")
                return ToolCallResult(
                    success=False,
                    error=str(e)
                ).model_dump()
        
        @self.app.post("/tools/{tool_name}/stream")
        async def stream_tool_call(tool_name: str, request: ToolCallRequest):
            """流式调用工具"""
            async def generate_stream():
                try:
                    # 发送开始执行事件
                    yield MCPStreamResponse(
                        event_type="tool_call",
                        data={
                            "tool_name": tool_name,
                            "parameters": request.parameters,
                            "status": "started"
                        }
                    ).to_sse_format()
                    
                    # 执行工具
                    result = await self._execute_tool(tool_name, request.parameters, request.session_id)
                    
                    # 发送执行结果
                    yield MCPStreamResponse(
                        event_type="tool_result", 
                        data=result.model_dump()
                    ).to_sse_format()
                    
                except Exception as e:
                    logger.error(f"流式工具调用失败: {tool_name}, 错误: {e}")
                    yield MCPStreamResponse(
                        event_type="error",
                        data={"error": str(e), "tool_name": tool_name}
                    ).to_sse_format()
            
            return EventSourceResponse(generate_stream())
    
    async def register_tool(self, tool_definition: ToolDefinition, handler: Callable):
        """注册工具"""
        self.tools[tool_definition.name] = tool_definition
        self.tool_handlers[tool_definition.name] = handler
        logger.info(f"注册工具: {tool_definition.name}")
    
    async def unregister_tool(self, tool_name: str):
        """注销工具"""
        if tool_name in self.tools:
            del self.tools[tool_name]
            del self.tool_handlers[tool_name]
            logger.info(f"注销工具: {tool_name}")
    
    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any], 
                          session_id: Optional[str] = None) -> ToolCallResult:
        """执行工具"""
        if tool_name not in self.tools:
            raise ValueError(f"工具 '{tool_name}' 不存在")
        
        if tool_name not in self.tool_handlers:
            raise ValueError(f"工具 '{tool_name}' 没有注册处理器")
        
        # 创建执行上下文
        context = ToolExecutionContext(
            tool_name=tool_name,
            parameters=parameters,
            session_id=session_id or "default",
            conversation_context=self.sessions.get(session_id) if session_id else ConversationContext(user_query="")
        )
        
        try:
            handler = self.tool_handlers[tool_name]
            
            # 支持同步和异步处理器
            if asyncio.iscoroutinefunction(handler):
                result = await handler(**parameters)
            else:
                result = handler(**parameters)
            
            execution_time = context.get_execution_time()
            logger.info(f"工具执行成功: {tool_name}, 耗时: {execution_time:.2f}s")
            
            return ToolCallResult(
                success=True,
                result=result if isinstance(result, dict) else {"output": result},
                execution_time=execution_time
            )
            
        except Exception as e:
            execution_time = context.get_execution_time()
            logger.error(f"工具执行失败: {tool_name}, 耗时: {execution_time:.2f}s, 错误: {e}")
            
            return ToolCallResult(
                success=False,
                error=str(e),
                execution_time=execution_time
            )
    
    async def start_server(self):
        """启动服务器"""
        import uvicorn
        logger.info(f"启动MCP服务器: http://{self.host}:{self.port}")
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
            access_log=True
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    def get_app(self) -> FastAPI:
        """获取FastAPI应用实例"""
        return self.app


class MCPClient:
    """标准MCP客户端 - 使用streamable HTTP"""
    
    def __init__(self, server_url: str = "http://localhost:8765"):
        self.server_url = server_url.rstrip("/")
        self.session: Optional[ClientSession] = None
        self.client_context = None
        self.session_context = None
        self.connected = False
        logger.info(f"初始化MCP客户端: {self.server_url}")
    
    def _normalize_server_url(self, raw_url: str) -> str:
        """确保HTTP端点正确：
        - 若路径中已包含 'mcp' 段（如 /api/mcp/...），保持不变
        - 若路径为空或根路径，则补充为 /mcp
        - 若路径非空且不含 'mcp'，则在末尾追加 /mcp
        """
        try:
            parsed = urlparse(raw_url)
            path = parsed.path or ""
            segments = [seg for seg in path.split("/") if seg]
            if any(seg.lower() == "mcp" for seg in segments):
                return raw_url  # 已包含mcp，直接使用
            if not path or path == "/":
                path = "/mcp"
            else:
                path = (path.rstrip("/")) + "/mcp"
            normalized = parsed._replace(path=path)
            return urlunparse(normalized)
        except Exception:
            return raw_url
    
    @asynccontextmanager
    async def get_session(self):
        """异步上下文管理器，用于获取和管理MCP会话"""
        import asyncio
        
        try:
            if not self.connected or not self.session:
                # 添加连接超时
                await asyncio.wait_for(self.connect(), timeout=15.0)
            
            if not self.session:
                raise ConnectionError("无法建立MCP会话")
            
            yield self.session
        except asyncio.TimeoutError:
            logger.error("MCP服务器连接超时")
            raise ConnectionError("MCP服务器连接超时")
        except Exception as e:
            logger.error(f"获取MCP会话失败: {e}")
            raise
        finally:
            # 在这里可以添加会话级别的清理逻辑（如果需要）
            pass

    async def connect(self):
        """连接到MCP服务器"""
        if self.connected:
            return
            
        try:
            if self.server_url.startswith("http"):
                logger.info(f"使用streamable HTTP连接到: {self.server_url}")
                normalized_url = self._normalize_server_url(self.server_url)
                if normalized_url != self.server_url:
                    logger.info(f"规范化MCP端点: {normalized_url}")
                
                # 使用streamablehttp_client按照官方示例
                self.client_context = streamablehttp_client(normalized_url)
                read_stream, write_stream, _ = await self.client_context.__aenter__()
                
                # 创建会话
                self.session_context = ClientSession(read_stream, write_stream)
                self.session = await self.session_context.__aenter__()
                
                # 初始化连接
                await self.session.initialize()
                
                self.connected = True
                logger.info("MCP客户端连接成功")
            else:
                raise ValueError(f"不支持的URL格式: {self.server_url}")
                
        except Exception as e:
            logger.error(f"MCP客户端连接失败: {e}")
            self.connected = False
            await self.close() # 连接失败时尝试清理
            raise
    
    async def list_tools(self) -> List[ToolDefinition]:
        """获取所有可用工具，并解析其参数定义"""
        import asyncio
        
        try:
            # 使用Python 3.8+兼容的超时处理
            try:
                # Python 3.11+ 版本
                async with asyncio.timeout(20.0):
                    return await self._do_list_tools()
            except AttributeError:
                # Python 3.8-3.10 版本
                return await asyncio.wait_for(self._do_list_tools(), timeout=20.0)
                    
        except asyncio.TimeoutError:
            logger.error("获取工具列表超时")
            return []
        except ConnectionError as e:
            logger.error(f"MCP连接错误: {e}")
            return []        
        except Exception as e:
            logger.error(f"获取工具列表失败: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []
    
    async def _do_list_tools(self) -> List[ToolDefinition]:
        """执行获取工具列表的核心逻辑"""
        async with self.get_session() as session:
            logger.info("使用MCP协议获取工具列表")
            tools_result = await session.list_tools()
            
            tools: List[ToolDefinition] = []
            if hasattr(tools_result, 'tools'):
                for tool in tools_result.tools:
                    name = getattr(tool, 'name', 'unknown_tool')
                    description = getattr(tool, 'description', '')
                    parameters: Dict[str, ToolParameter] = {}
                    required_params: List[str] = []

                    input_schema = getattr(tool, 'input_schema', {})
                    if isinstance(input_schema, dict):
                        schema_props = input_schema.get('properties', {})
                        required_params = input_schema.get('required', [])
                        
                        for param_name, schema in schema_props.items():
                            type_str = schema.get('type', 'string')
                            type_map = {
                                'string': ToolParameterType.STRING,
                                'number': ToolParameterType.NUMBER,
                                'integer': ToolParameterType.INTEGER,
                                'boolean': ToolParameterType.BOOLEAN,
                                'array': ToolParameterType.ARRAY,
                                'object': ToolParameterType.OBJECT,
                            }
                            param_type = type_map.get(type_str, ToolParameterType.STRING)

                            parameters[param_name] = ToolParameter(
                                type=param_type,
                                description=schema.get('description', ''),
                                required=param_name in required_params,
                                default=schema.get('default'),
                                enum=schema.get('enum')
                            )

                    tools.append(ToolDefinition(
                        name=name,
                        description=description,
                        parameters=parameters,
                        required_parameters=required_params
                    ))
                
                logger.info(f"通过MCP协议解析到 {len(tools)} 个工具")
                return tools
            else:
                logger.warning("工具结果中没有找到tools属性")
                return []
    
    async def call_tool(self, tool_name: str, parameters: Dict[str, Any], 
                       session_id: Optional[str] = None) -> ToolCallResult:
        """调用工具"""
        try:
            async with self.get_session() as session:
                logger.info(f"使用MCP协议调用工具: {tool_name} with params {parameters}")
                
                # 与SDK示例保持一致: 使用位置参数 name, arguments
                result = await session.call_tool(tool_name, parameters or {})
                
                logger.debug(f"MCP anwser: {result}")
                
                if hasattr(result, 'isError') and result.isError:
                    error_content = str(result.content[0]) if result.content else "Unknown tool call error"
                    logger.warning(f"工具调用失败: {error_content}, anwser: {result}")
                    return ToolCallResult(success=False, error=error_content)
                else:
                    logger.info(f"工具 '{tool_name}' 调用成功")
                    result_content = {}
                    if hasattr(result, 'content') and result.content:
                        content_item = result.content[0]
                        if hasattr(content_item, 'text'):
                            # 尝试解析JSON
                            try:
                                result_content = json.loads(content_item.text)
                            except json.JSONDecodeError:
                                result_content = {"text": content_item.text}
                        else:
                            result_content = {"output": str(content_item)}
                    
                    logger.debug(f"工具返回内容: {result_content}")
                    return ToolCallResult(success=True, result=result_content)
                
        except Exception as e:
            logger.error(f"工具调用异常: {tool_name}, 错误: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return ToolCallResult(success=False, error=str(e))
    
    async def stream_tool_call(self, tool_name: str, parameters: Dict[str, Any],
                             session_id: Optional[str] = None) -> AsyncIterator[MCPStreamResponse]:
        """流式调用工具"""
        try:
            async with self.get_session() as session:
                logger.info(f"使用MCP协议流式调用工具: {tool_name}")
                
                # 位置参数调用，避免签名不匹配
                async for chunk in session.stream_tool_call(tool_name, parameters or {}):
                    event_type = "unknown"
                    data = {}

                    if chunk.type == "tool_code":
                        event_type = "tool_code"
                        data = {"language": chunk.language, "code": chunk.code}
                    elif chunk.type == "text_delta":
                        event_type = "text_delta"
                        data = {"delta": chunk.text}
                    elif chunk.type == "tool_result" and chunk.content:
                        event_type = "tool_result"
                        content = chunk.content[0]
                        if hasattr(content, "text"):
                            try:
                                data = json.loads(content.text)
                            except json.JSONDecodeError:
                                data = {"text": content.text}
                        else:
                            data = {"output": str(content)}
                    elif chunk.type == "error":
                        event_type = "error"
                        data = {"error": str(chunk.content[0]) if chunk.content else "Unknown error"}
                    
                    yield MCPStreamResponse(event_type=event_type, data=data)

        except Exception as e:
            logger.error(f"流式工具调用失败: {tool_name}, 错误: {e}")
            yield MCPStreamResponse(
                event_type="error",
                data={"error": str(e), "tool_name": tool_name}
            )
    
    async def create_session(self, context: ConversationContext) -> bool:
        """创建会话"""
        try:
            if not self.connected:
                await self.connect()
            return True
        except Exception as e:
            logger.error(f"创建会话失败: {e}")
            return False
    
    async def close(self):
        """关闭客户端"""
        try:
            if self.session_context:
                await self.session_context.__aexit__(None, None, None)
            if self.client_context:
                await self.client_context.__aexit__(None, None, None)
                
            self.session = None
            self.session_context = None
            self.client_context = None
            self.connected = False
            logger.info("MCP客户端已关闭")
        except Exception as e:
            logger.error(f"关闭MCP客户端失败: {e}")


# 全局MCP服务器实例
mcp_server = ModernMCPServer()

# 全局MCP客户端实例  
try:
    mcp_client = MCPClient(get_mcp_server_url())
except Exception:
    mcp_client = MCPClient()


async def start_mcp_server_background():
    """在后台启动MCP服务器"""
    try:
        await mcp_server.start_server()
    except Exception as e:
        logger.error(f"MCP服务器启动失败: {e}")


def get_mcp_app() -> FastAPI:
    """获取MCP FastAPI应用"""
    return mcp_server.get_app()