"""
服务初始化模块
"""
import streamlit as st
import asyncio
import logging
import importlib
import pkgutil

logger = logging.getLogger(__name__)

@st.cache_resource
def initialize_services():
    """初始化MCP服务和智能体"""
    try:
        # 导入必要模块
        from mcp_services.base_service import mcp_manager
        from mcp_services.document_parser import DocumentParserService
        from agents.base_agent import agent_coordinator
        from agents.qa_agent import QAAgent
        from agents.analysis_agent import AnalysisAgent
        
        # 初始化MCP服务
        doc_parser_service = DocumentParserService()
        # 暂时只初始化文档解析服务，跳过有问题的文件操作服务
        mcp_manager.register_service(doc_parser_service)
        
        # 创建临时事件循环来初始化服务
        try:
            # 尝试在当前线程初始化
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 如果循环正在运行，创建任务
                future = asyncio.ensure_future(doc_parser_service.initialize())
            else:
                # 如果循环未运行，直接运行
                init_success = loop.run_until_complete(doc_parser_service.initialize())
        except RuntimeError:
            # 创建新的事件循环
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                init_success = loop.run_until_complete(doc_parser_service.initialize())
            finally:
                loop.close()
        
        # 初始化并注册智能体
        qa_agent = QAAgent()
        analysis_agent = AnalysisAgent()
        agent_coordinator.register_agent(qa_agent)
        agent_coordinator.register_agent(analysis_agent)
        
        logger.info("文档解析服务、数据分析服务和智能体初始化完成")
        return True
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

@st.cache_resource
def initialize_mcp_agent():
    """初始化MCP智能体"""
    try:
        from agents.mcp_agent import MCPDocumentQAAgent
        
        mcp_agent = MCPDocumentQAAgent()
        
        # 同步预初始化本地工具（避免第一次使用时的异步初始化问题）
        def _sync_pre_init():
            try:
                # 同步加载本地工具模块
                import tools
                from tools.base_tool import tool_registry
                
                logger.info("开始预加载本地工具模块...")
                for _, name, _ in pkgutil.iter_modules(tools.__path__, tools.__name__ + "."):
                    try:
                        importlib.import_module(name)
                        logger.debug(f"预加载工具模块: {name}")
                    except Exception as e:
                        logger.warning(f"预加载工具模块 {name} 失败: {e}")
                
                # 预注册本地工具到智能体
                tools_in_registry = tool_registry.list_tools()
                for tool in tools_in_registry:
                    if hasattr(tool, 'definition'):
                        mcp_agent.available_tools.append(tool.definition)
                
                # 添加final_answer工具
                mcp_agent.available_tools.append(mcp_agent.final_answer_tool)
                
                logger.info(f"预初始化完成，加载了 {len(mcp_agent.available_tools)} 个本地工具")
                mcp_agent._local_tools_loaded = True
                return True
            except Exception as e:
                logger.warning(f"预初始化失败: {e}")
                mcp_agent._local_tools_loaded = False
                return False
        
        # 执行同步预初始化
        _sync_pre_init()
        
        logger.info("MCP智能体创建完成，本地工具已预加载")
        return mcp_agent
    except Exception as e:
        logger.error(f"MCP智能体创建失败: {e}")
        return None
