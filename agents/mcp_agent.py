"""
MCP增强的思考智能体
支持工具调用、多轮思考和流式输出
"""

from typing import Dict, Any, List, Optional, AsyncIterator, Union
import asyncio
import json
from datetime import datetime
from loguru import logger
import pkgutil
import importlib
import tools

from .base_agent import BaseAgent
from utils.logger import agent_logger, log_async_generator
from mcp_services.models import (
    ThoughtProcess, ThoughtType, ConversationContext, 
    ToolDefinition, ToolCallRequest, MCPStreamResponse,
    ToolParameter, ToolParameterType
)
from mcp_services.modern_mcp_server import mcp_client
from tools.base_tool import tool_registry
from utils.llm_utils import llm_manager
from config.settings import is_third_party_enabled, is_mcp_streaming_enabled


class MCPAgent(BaseAgent):
    """MCP增强的思考智能体"""
    
    def __init__(self, name: str = "MCP_Agent", description: str = "具备工具调用能力的思考智能体"):
        super().__init__(name, description)
        
        self.add_capability("tool_calling")
        self.add_capability("multi_step_reasoning")
        self.add_capability("stream_output")
        
        self.available_tools: List[ToolDefinition] = []
        self.max_iterations = 10
        self.current_iteration = 0
        self.conversation_context: Optional[ConversationContext] = None
        
        self.final_answer_tool = ToolDefinition(
            name="final_answer",
            description="当您拥有足够信息时，调用此工具以向用户提供最终答案。",
            parameters={
                "answer": ToolParameter(
                    type=ToolParameterType.STRING,
                    description="给用户的最终、全面的答案。",
                    required=True,
                )
            },
            required_parameters=["answer"]
        )

        # 使用第三方API作为默认提供商
        if is_third_party_enabled():
            self.llm_provider = "third_party"
        else:
            self.llm_provider = "ollama"
    
    async def initialize(self):
        """初始化智能体"""
        # 注册所有可用工具
        await self._register_tools()
        logger.info(f"MCP智能体初始化完成，注册了 {len(self.available_tools)} 个工具")
    
    async def _register_tools(self):
        """注册所有可用工具到MCP服务器"""
        from mcp_services.modern_mcp_server import mcp_server
        
        # 动态导入所有本地工具模块
        logger.info("开始动态加载本地工具...")
        for _, name, _ in pkgutil.iter_modules(tools.__path__, tools.__name__ + "."):
            try:
                importlib.import_module(name)
                logger.debug(f"成功导入工具模块: {name}")
            except Exception as e:
                logger.warning(f"导入工具模块 {name} 失败: {e}")

        tools_in_registry = tool_registry.list_tools()
        logger.info(f"从注册表中发现 {len(tools_in_registry)} 个本地工具。")
        
        for tool in tools_in_registry:
            try:
                # 注册工具到MCP服务器
                if not hasattr(tool, 'definition'): continue # 跳过无效工具
                
                await mcp_server.register_tool(tool.definition, tool.safe_execute)
                self.available_tools.append(tool.definition)
                logger.info(f"注册本地工具: {tool.name}")
            except Exception as e:
                logger.error(f"注册工具 {tool.name} 失败: {e}")

        # 添加final_answer工具
        self.available_tools.append(self.final_answer_tool)
        logger.info(f"已注册特殊工具: {self.final_answer_tool.name}")

        # 合并远程MCP服务器上的工具定义
        try:
            from mcp_services.modern_mcp_server import mcp_client
            remote_tools = await mcp_client.list_tools()
            if remote_tools:
                local_names = {t.name for t in self.available_tools}
                added = 0
                for rt in remote_tools:
                    if rt.name not in local_names:
                        self.available_tools.append(rt)
                        added += 1
                logger.info(f"从远程MCP服务器加载工具 {added} 个，总计 {len(self.available_tools)} 个")
        except Exception as e:
            logger.warning(f"获取远程工具列表失败: {e}")
    
    @log_async_generator(agent_logger)
    async def think_and_act(self, user_query: str, document_content: str = None, 
                          document_type: str = None, document_file_path: str = None) -> AsyncIterator[ThoughtProcess]:
        """思考并执行的主循环"""
        
        agent_logger.info("开始MCP智能体思考流程", 
                         query_length=len(user_query),
                         has_document=bool(document_content),
                         document_type=document_type,
                         max_iterations=self.max_iterations)
        
        # 初始化对话上下文
        self.conversation_context = ConversationContext(
            user_query=user_query,
            document_content=document_content,
            document_type=document_type,
            document_file_path=document_file_path,
            available_tools=self.available_tools,
            max_iterations=self.max_iterations
        )
        
        self.current_iteration = 0
        
        # 添加用户消息到历史
        self.conversation_context.add_message("user", user_query)
        agent_logger.debug("用户消息已添加到对话历史")
        
        try:
            while not self.conversation_context.is_completed and self.current_iteration < self.max_iterations:
                self.current_iteration += 1
                agent_logger.info(f"开始第 {self.current_iteration} 轮思考")
                
                # 第1步：分析并获取思考过程（纯文本）
                thought = await self._analyze_and_plan()
                
                yield ThoughtProcess(
                    type=ThoughtType.THINKING,
                    content=thought,
                    confidence=0.8
                )
                
                # 第2步：根据思考过程决定下一步的工具调用（纯JSON）
                action = await self._decide_next_action(thought)

                if not action or action.get("type") != "tool_call":
                    yield ThoughtProcess(type=ThoughtType.ERROR, content=f"无效的行动: {action}")
                    break
                
                tool_name = action.get("tool_name")
                parameters = action.get("parameters", {})
                
                # 检查是否是最终答案
                if tool_name == self.final_answer_tool.name:
                    final_answer = parameters.get("answer", "未能生成答案。")
                    self.conversation_context.is_completed = True
                    self.conversation_context.final_answer = final_answer
                    
                    agent_logger.info(f"最终答案生成完成，长度: {len(final_answer)}")
                    yield ThoughtProcess(
                        type=ThoughtType.FINAL_ANSWER,
                        content=final_answer,
                        confidence=0.9
                    )
                    break
                
                # 执行常规工具调用
                agent_logger.info(f"执行工具调用: {tool_name}", parameters=parameters)
                
                yield ThoughtProcess(
                    type=ThoughtType.TOOL_CALL,
                    content=f"调用工具：{tool_name}",
                    tool_name=tool_name,
                    parameters=parameters
                )
                
                tool_result = await self._execute_tool(tool_name, parameters)
                agent_logger.debug(f"工具执行结果: {str(tool_result)[:200]}...")
                
                yield ThoughtProcess(
                    type=ThoughtType.TOOL_RESULT,
                    content=f"工具执行完成",
                    tool_name=tool_name,
                    result=tool_result
                )
                
                # 将工具结果添加到对话历史
                try:
                    result_str = json.dumps(tool_result, ensure_ascii=False, indent=2, default=str)
                except (TypeError, ValueError):
                    result_str = str(tool_result)
                
                self.conversation_context.add_message(
                    "tool", 
                    f"工具 {tool_name} 执行结果: {result_str}"
                )

            # 如果达到最大迭代次数，强制生成答案
            if not self.conversation_context.is_completed:
                agent_logger.warning(f"达到最大迭代次数 {self.max_iterations}，强制结束")
                final_answer = "已达到最大思考次数，未能得出最终结论。请尝试优化问题或提供更多信息。"
                yield ThoughtProcess(
                    type=ThoughtType.FINAL_ANSWER,
                    content=final_answer,
                    confidence=0.7
                )
                
        except Exception as e:
            error_msg = f"执行过程中出现错误: {str(e)}"
            agent_logger.error("思考循环异常", error=e)
            yield ThoughtProcess(
                type=ThoughtType.ERROR,
                content=error_msg
            )
    
    async def _analyze_and_plan(self) -> str:
        """分析当前状态并制定计划（输出纯文本思考过程）。"""
        context = self.conversation_context
        prompt = self._get_analysis_prompt(context)
        
        # 这个调用期望的是纯文本的思考过程
        analysis_text = await self._get_llm_response(prompt)
        return analysis_text

    async def _decide_next_action(self, thought: str) -> Optional[Dict[str, Any]]:
        """根据思考过程，决定下一步的工具调用（输出纯JSON）。"""
        context = self.conversation_context
        prompt = self._get_decision_prompt(context, thought)

        response_text = await self._get_llm_response(prompt)
        
        try:
            cleaned_json = self._extract_json_from_response(response_text)
            action = json.loads(cleaned_json)
            
            # 这里我们只关心action部分
            if "action" in action:
                return action["action"]
            
            # 兼容直接返回action的格式
            if "type" in action and "tool_name" in action:
                 return action

            raise ValueError("决策JSON中缺少'action'或'type'/'tool_name'")

        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"无法解析决策JSON: {e}\n响应: {response_text}")
            return {
                "type": "tool_call",
                "tool_name": "final_answer",
                "parameters": {"answer": "处理过程中遇到错误，无法继续执行。"}
            }

    def _get_analysis_prompt(self, context: ConversationContext) -> str:
        """生成用于分析和思考的提示"""
        return f"""你是一个专家级助手。你的任务是通过调用工具来解决用户的问题。

当前情况:
- 用户问题: {context.user_query}
- 迭代轮次: {self.current_iteration}/{self.max_iterations}
- 对话历史:
{self._format_chat_history()}

可用工具:
{self._format_available_tools()}

请仔细分析以上信息，然后“大声思考”你的计划。你的思考过程应包括：
1.  对用户问题的理解和意图分析。
2.  评估当前是否已掌握足够信息。
3.  如果信息不足，你需要调用哪个工具？为什么？需要什么参数？
4.  如果信息充足，你准备如何回答用户，并调用 `final_answer` 工具。

你的思考过程（纯文本）:"""

    def _get_decision_prompt(self, context: ConversationContext, thought: str) -> str:
        """生成用于决策最终工具调用的提示"""
        return f"""你是一个决策制定者。根据以下思考过程，选择一个工具来执行。

思考过程:
---
{thought}
---

可用工具:
{self._format_available_tools()}

你的任务是严格按照以下JSON格式返回你选择的工具调用，不要包含任何其他文本或markdown标记:
{{
  "action": {{
    "type": "tool_call",
    "tool_name": "工具名称",
    "parameters": {{ "参数名": "参数值" }}
  }}
}}

如果思考过程表明信息已经足够，请调用 `final_answer` 工具。

你的JSON决策:"""
    
    def _extract_json_from_response(self, response: str) -> str:
        """从LLM响应中提取干净的JSON字符串。"""
        # 查找第一个 '{' 和最后一个 '}'
        start_index = response.find('{')
        end_index = response.rfind('}')

        if start_index != -1 and end_index != -1 and end_index > start_index:
            return response[start_index:end_index+1]
        
        # 作为后备，尝试移除markdown代码块
        cleaned = response.strip()
        if cleaned.startswith("```json"):
            cleaned = cleaned[7:]
        if cleaned.startswith("```"):
            cleaned = cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
        
        return cleaned.strip()

    async def _execute_tool(self, tool_name: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """执行工具调用"""
        
        # 已移除对 view_document 的特殊处理
        
        try:
            # 通过工具注册表直接调用本地工具
            tool = tool_registry.get_tool(tool_name)
            if tool:
                # 如果是 document_parser 且缺少/占位 file_path，自动从上下文补齐
                if tool_name == "document_parser":
                    fp = parameters.get("file_path")
                    ctx_fp = self.conversation_context.document_file_path if self.conversation_context else None
                    placeholder_values = {"string", "path", "filepath", "<path>", "<file_path>", "<filepath>"}
                    if (not fp or str(fp).strip().lower() in placeholder_values) and ctx_fp:
                        parameters = {**parameters, "file_path": ctx_fp}
                        agent_logger.info("已自动注入上下文中的 document_file_path 到 document_parser 参数", file_path=ctx_fp)

                result = await tool.safe_execute(**parameters)
                logger.info(f"本地工具执行成功: {tool_name}")
                return result
            else:
                # 通过MCP客户端调用远程工具
                session_id = self.conversation_context.session_id if self.conversation_context else None
                if is_mcp_streaming_enabled():
                    try:
                        # 使用流式接口并获取最终结果
                        final_result = None
                        async for event in mcp_client.stream_tool_call(tool_name, parameters, session_id):
                            if event.event_type == "tool_result":
                                final_result = event.data
                                break
                            elif event.event_type == "error":
                                return {
                                    "success": False,
                                    "error": event.data.get("error", "unknown error"),
                                    "tool_name": tool_name
                                }
                        if final_result is not None:
                            logger.info(f"远程工具流式调用成功: {tool_name}")
                            return final_result
                        # 若未获取到结果，回退到非流式调用
                    except Exception as se:
                        logger.warning(f"流式调用失败，回退普通调用: {se}")

                # 回退到普通调用
                result = await mcp_client.call_tool(tool_name, parameters, session_id)
                logger.info(f"远程工具同步调用成功: {tool_name}")
                return result.model_dump() if hasattr(result, 'model_dump') else result
                
        except Exception as e:
            logger.error(f"工具执行失败: {tool_name}, 错误: {e}")
            return {
                "success": False,
                "error": str(e),
                "tool_name": tool_name
            }
    
    def _format_available_tools(self) -> str:
        """格式化可用工具列表"""
        if not self.available_tools:
            return "无可用工具"
        
        tools_info = []
        for tool in self.available_tools[:5]:  # 只显示前5个工具
            # 基本信息
            tool_info = f"- {tool.name}: {tool.description}"
            
            # 添加参数信息（如果有）
            if hasattr(tool, 'parameters') and tool.parameters:
                param_details = []
                for param_name, param_def in tool.parameters.items():
                    param_type = getattr(param_def, 'type', 'string')
                    if isinstance(param_type, object) and hasattr(param_type, 'value'):
                        param_type = param_type.value # handle enums
                    
                    is_required = getattr(param_def, 'required', False)
                    required_mark = ' (必填)' if is_required else ''
                    param_details.append(f"{param_name}: {param_type}{required_mark}")
                
                if param_details:
                    tool_info += f"\n  参数: {', '.join(param_details)}"
            
            tools_info.append(tool_info)
        
        return "\n".join(tools_info)
    
    def _format_chat_history(self, max_messages: int = 5) -> str:
        """格式化聊天历史"""
        if not self.conversation_context.chat_history:
            return "无历史记录"
        
        recent_history = self.conversation_context.get_recent_history(max_messages)
        
        formatted_messages = []
        for msg in recent_history:
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            # 限制内容长度
            if len(content) > 200:
                content = content[:200] + "..."
            formatted_messages.append(f"{role}: {content}")
        
        return "\n".join(formatted_messages)
    
    async def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理输入数据（保持与BaseAgent兼容）"""
        if not isinstance(input_data, dict):
            raise ValueError("输入数据必须是字典格式")
        
        user_query = input_data.get("question", "")
        document_content = input_data.get("document_content", "")
        document_type = input_data.get("document_type", "")
        document_file_path = input_data.get("document_file_path") or (context or {}).get("document_file_path") if context else None
        
        if not user_query:
            raise ValueError("问题不能为空")
        
        # 初始化智能体
        await self.initialize()
        
        # 收集所有思考过程
        thought_processes = []
        final_answer = ""
        
        async for thought in self.think_and_act(user_query, document_content, document_type, document_file_path):
            thought_processes.append(thought.model_dump())
            
            if thought.type == ThoughtType.FINAL_ANSWER:
                final_answer = thought.content
        
        return {
            "question": user_query,
            "answer": final_answer,
            "thought_processes": thought_processes,
            "iterations_used": self.current_iteration,
            "tools_available": len(self.available_tools),
            "context": self.conversation_context.model_dump() if self.conversation_context else None
        }


class MCPDocumentQAAgent(MCPAgent):
    """专门用于文档问答的MCP智能体"""
    
    def __init__(self):
        super().__init__(
            name="MCP_Document_QA_Agent",
            description="专门用于文档问答的MCP增强智能体"
        )
        
        # 添加文档特定的能力
        self.add_capability("document_analysis")
        self.add_capability("content_extraction")
        self.add_capability("contextual_qa")
    
    def _get_analysis_prompt(self, context: ConversationContext) -> str:
        """为文档问答生成专用的分析提示"""
        document_tools_str = self._format_document_tools()
        # 文档内容预览（移除 view_document 后，直接在提示中提供片段）
        doc_preview = ""
        if context.document_content:
            preview_len = 1500
            doc_text = context.document_content
            doc_preview = (doc_text[:preview_len] + ("..." if len(doc_text) > preview_len else "")).strip()
        
        return f"""你是一个专业的文档问答助手。你的任务是分析文档并使用工具来回答用户的问题。

用户问题: {context.user_query}

文档信息:
- 文档类型: {context.document_type or '未知'}
- 文档长度: {len(context.document_content) if context.document_content else 0} 字符
- 是否有文档内容: {'是' if context.document_content else '否'}
- 文档文件路径: {context.document_file_path or '（未提供）'}

文档片段（最多前1500字符）:
{doc_preview if doc_preview else '（无）'}

当前状态:
- 迭代轮次: {self.current_iteration}/{self.max_iterations}
- 对话历史:
{self._format_chat_history()}

可用的文档处理工具:
{document_tools_str}
- final_answer: 当你拥有足够信息时，调用此工具以向用户提供最终答案。

请仔细分析以上信息，然后“大声思考”你的计划。你的思考过程应包括：
1.  用户的问题是否需要查看文档原文？
    - 如果对话中已经提供了 `document_content`，可直接基于该内容分析。
    - 如果未提供原文而只有文件路径，请优先调用 `document_parser` 解析文档内容。
2.  现有信息是否足够回答问题？
3.  如果需要进一步分析，应该调用哪个工具（如 `document_parser`、`document_search`、`document_analyzer`）？
4.  如果信息足够，准备如何回答，并调用 `final_answer`。

你的思考过程（纯文本）:"""
    
    def _get_decision_prompt(self, context: ConversationContext, thought: str) -> str:
        """为文档问答生成专用的决策提示"""
        document_tools_str = self._format_document_tools()
        
        return f"""你是一个文档问答决策者。根据以下思考过程，选择一个工具来执行。

思考过程:
---
{thought}
---

可用工具:
{document_tools_str}
- final_answer: 当你拥有足够信息时，调用此工具以向用户提供最终答案。

你的任务是严格按照以下JSON格式返回你选择的工具调用，不要包含任何其他文本或markdown标记:
{{
  "action": {{
    "type": "tool_call",
    "tool_name": "工具名称",
    "parameters": {{ "参数名": "参数值" }}
  }}
}}

你的JSON决策:"""

    def _format_document_tools(self) -> str:
        """格式化文档相关工具"""
        document_tools = [
            tool for tool in self.available_tools 
            if "document" in tool.name.lower() or "search" in tool.name.lower()
        ]
        
        if not document_tools:
            return "无文档专用工具"
        
        tools_info = []
        # 使用更详细的格式化逻辑，与 _format_available_tools 一致
        for tool in document_tools:
            tool_info = f"- {tool.name}: {tool.description}"
            if hasattr(tool, 'parameters') and tool.parameters:
                param_details = []
                for param_name, param_def in tool.parameters.items():
                    param_type = getattr(param_def, 'type', 'string')
                    if isinstance(param_type, object) and hasattr(param_type, 'value'):
                        param_type = param_type.value
                    
                    is_required = param_name in getattr(tool, 'required_parameters', [])
                    required_mark = ' (必填)' if is_required else ''
                    param_details.append(f"{param_name}: {param_type}{required_mark}")
                
                if param_details:
                    tool_info += f"\n  参数: {', '.join(param_details)}"
            tools_info.append(tool_info)
        
        return "\n".join(tools_info)