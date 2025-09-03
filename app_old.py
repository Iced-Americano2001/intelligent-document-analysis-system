import streamlit as st
import asyncio
from pathlib import Path
from typing import Dict, Any
import logging
import pandas as pd

# 尝试导入nest_asyncio，如果失败则使用备用方案
try:
    import nest_asyncio
    # 安全地应用嵌套事件循环支持
    try:
        nest_asyncio.apply()
    except RuntimeError:
        # 如果当前线程没有事件循环，先创建一个
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            nest_asyncio.apply(loop)
        except Exception:
            # 如果仍然失败，忽略错误继续执行
            pass
except ImportError:
    # 如果nest_asyncio不可用，使用备用方案
    pass

# 设置页面配置
st.set_page_config(
    page_title="智能文档问答",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# 导入系统模块
try:
    from config.settings import get_config
    from mcp_services.base_service import mcp_manager, handle_mcp_request
    from mcp_services.document_parser import DocumentParserService
    # 暂时注释掉有问题的file_operations模块
    # from mcp_services.file_operations import FileOperationsService
    from agents.base_agent import agent_coordinator
    from agents.mcp_agent import MCPDocumentQAAgent
    from utils.llm_utils import llm_manager
    from ui.streaming_components import StreamingChatInterface, InteractiveElements
    from ui.status_manager import ConversationStatusManager, PerformanceMonitor
    from utils.rag_utils import (
        compute_file_id,
        build_or_load_index,
        retrieve_with_optional_rerank,
        build_context_from_chunks,
    )
except ImportError as e:
    st.error(f"模块导入失败: {e}")
    st.stop()

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化服务
@st.cache_resource
def initialize_services():
    """初始化MCP服务和智能体"""
    try:
        # 初始化MCP服务
        doc_parser_service = DocumentParserService()
        # 暂时只初始化文档解析服务，跳过有问题的文件操作服务
        mcp_manager.register_service(doc_parser_service)
        
        # 直接调用服务初始化（不通过异步方式）
        import asyncio
        
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
        from agents.qa_agent import QAAgent
        from agents.analysis_agent import AnalysisAgent
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
        mcp_agent = MCPDocumentQAAgent()
        
        # 同步预初始化本地工具（避免第一次使用时的异步初始化问题）
        def _sync_pre_init():
            try:
                # 同步加载本地工具模块
                import tools
                import pkgutil
                import importlib
                from tools.base_tool import tool_registry
                from mcp_services.modern_mcp_server import mcp_server
                
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

def run_async_in_streamlit(coro):
    """在Streamlit环境中安全运行异步代码"""
    import threading
    
    try:
        # 方法1: 直接运行（如果没有运行中的事件循环）
        return asyncio.run(coro)
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # 方法2: 在新线程中运行
            try:
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, coro)
                    return future.result()
            except Exception:
                # 方法3: 创建新的事件循环
                try:
                    loop = asyncio.new_event_loop()
                    old_loop = None
                    try:
                        old_loop = asyncio.get_event_loop()
                    except RuntimeError:
                        pass
                    
                    asyncio.set_event_loop(loop)
                    try:
                        return loop.run_until_complete(coro)
                    finally:
                        loop.close()
                        if old_loop:
                            asyncio.set_event_loop(old_loop)
                except Exception as final_e:
                    logger.error(f"所有异步执行方法都失败了: {final_e}")
                    raise RuntimeError(f"无法执行异步操作: {final_e}")
        else:
            raise

def display_qa_results(result: Dict[str, Any]):
    """显示问答结果"""
    st.success("✅ 问答完成！")
    
    if "answer" in result:
        st.markdown("### 📝 AI回答")
        st.markdown(result["answer"])
    
    # 显示相关段落（QA Agent 返回的是 relevant_passages）
    if "relevant_passages" in result and result["relevant_passages"]:
        st.markdown("### 📖 相关引用")
        passages = result["relevant_passages"]
        if isinstance(passages, list):
            for i, passage in enumerate(passages, 1):
                st.info(f"**引用 {i}**: {passage}")
        else:
            st.info(f"**相关内容**: {passages}")
    
    # 显示置信度
    if "confidence" in result:
        st.markdown("### 📊 置信度分析")
        confidence = result["confidence"]
        if isinstance(confidence, (int, float)):
            st.progress(float(confidence), text=f"置信度: {confidence:.1%}")
        else:
            st.info(f"置信度: {confidence}")
    
    # 显示额外信息
    if "content_length" in result:
        col1, col2 = st.columns(2)
        with col1:
            st.metric("文档长度", f"{result['content_length']:,} 字符")
        with col2:
            st.metric("回答长度", f"{result.get('answer_length', 0):,} 字符")

async def process_document_qa(uploaded_file, question, answer_style="detailed", include_quotes=True, confidence_threshold=0.7,
                            enable_advanced_confidence=False, use_rag=True, use_reranker=True, rag_top_k=12, rag_rerank_top_n=6):
    """处理文档问答"""
    try:
        # 进度指示
        progress_bar = st.progress(0, text="开始处理问答...")
        
        # 保存文件
        file_config = get_config("file")
        upload_dir = Path(file_config.get("upload_dir", "uploads"))
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        progress_bar.progress(25, text="📁 文档保存完成...")
        
        # 解析文档
        progress_bar.progress(50, text="📖 正在解析文档...")
        
        parse_result = await handle_mcp_request(
            method="document_parser/extract_text",
            params={"file_path": str(file_path)}
        )
        
        if parse_result.get("result", {}).get("success", False):
            text_content = parse_result["result"]["result"]["text_content"]
            
            # RAG处理
            context_text = text_content
            if use_rag and text_content:
                try:
                    progress_bar.progress(60, text="🔍 构建RAG索引...")
                    
                    # 计算文件ID
                    file_id = compute_file_id(str(file_path))
                    
                    # 构建或加载索引
                    store, embedder, reranker = build_or_load_index(file_id, text_content)
                    
                    progress_bar.progress(70, text="🔍 RAG检索相关内容...")
                    
                    # 检索相关片段
                    chunks = retrieve_with_optional_rerank(
                        query=question,
                        store=store,
                        embedder=embedder,
                        top_k=rag_top_k,
                        rerank_top_n=rag_rerank_top_n,
                        use_reranker=use_reranker
                    )
                    
                    if chunks:
                        # 构建上下文
                        context_text = build_context_from_chunks(chunks)
                        logger.info(f"RAG检索到{len(chunks)}个相关片段")
                    else:
                        logger.warning("RAG未检索到相关片段，使用原始文本")
                        
                except Exception as e:
                    logger.error(f"RAG处理失败，使用原始文本: {e}")
                    # RAG失败时回退到原始文本
                    context_text = text_content
            
            progress_bar.progress(75, text="🤖 AI正在思考答案...")
            
            # 执行问答
            qa_input = {
                "document_content": context_text,
                "question": question,
                "document_type": Path(uploaded_file.name).suffix,
                "answer_style": answer_style,
                "include_quotes": include_quotes,
                "confidence_threshold": confidence_threshold,
                "use_rag": use_rag,
                "rag_chunks_count": len(chunks) if use_rag and 'chunks' in locals() else 0
            }
            
            qa_result = await agent_coordinator.execute_agent(
                "QA_Agent",
                qa_input
            )
            
            progress_bar.progress(100, text="✅ 问答完成！")
            
            if qa_result.get("success", False):
                display_qa_results(qa_result["result"])
            else:
                st.error(f"❌ 问答失败: {qa_result.get('error', '未知错误')}")
                st.warning("💡 建议重新表述问题或检查文档内容")
        else:
            st.error("❌ 文档解析失败")
            st.warning("💡 请检查文档格式是否正确")
            
    except Exception as e:
        st.error(f"❌ 问答处理失败: {str(e)}")
        st.warning("💡 如果问题持续存在，请尝试简化问题或更换文档")
        logger.error(f"问答处理失败: {e}")

async def process_mcp_qa(uploaded_file, question, mcp_agent, answer_style="detailed", 
                        include_quotes=True, confidence_threshold=0.7, max_iterations=10, show_thinking=True,
                        use_rag=True, use_reranker=True, rag_top_k=12, rag_rerank_top_n=6):
    """使用MCP智能体处理文档问答"""
    try:
        # 进度指示
        status_manager = ConversationStatusManager()
        status_manager.start_conversation(max_iterations)
        
        performance_monitor = PerformanceMonitor()
        performance_monitor.start_monitoring()
        
        # 保存文件
        file_config = get_config("file")
        upload_dir = Path(file_config.get("upload_dir", "uploads"))
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        status_manager.update_step("thinking", "文档已保存，开始解析...")
        
        # 解析文档
        parse_result = await handle_mcp_request(
            method="document_parser/extract_text",
            params={"file_path": str(file_path)}
        )
        
        if parse_result.get("result", {}).get("success", False):
            text_content = parse_result["result"]["result"]["text_content"]
            
            # RAG处理
            context_text = text_content
            rag_chunks_info = {"enabled": False, "chunks_count": 0}
            
            if use_rag and text_content:
                try:
                    status_manager.update_step("thinking", "构建RAG索引...")
                    
                    # 计算文件ID
                    file_id = compute_file_id(str(file_path))
                    
                    # 构建或加载索引
                    store, embedder, reranker = build_or_load_index(file_id, text_content)
                    
                    status_manager.update_step("thinking", "RAG检索相关内容...")
                    
                    # 检索相关片段
                    chunks = retrieve_with_optional_rerank(
                        query=question,
                        store=store,
                        embedder=embedder,
                        top_k=rag_top_k,
                        rerank_top_n=rag_rerank_top_n,
                        use_reranker=use_reranker
                    )
                    
                    if chunks:
                        # 构建上下文
                        context_text = build_context_from_chunks(chunks)
                        rag_chunks_info = {"enabled": True, "chunks_count": len(chunks)}
                        logger.info(f"RAG检索到{len(chunks)}个相关片段")
                        status_manager.update_step("thinking", f"RAG检索完成，获得{len(chunks)}个相关片段")
                    else:
                        logger.warning("RAG未检索到相关片段，使用原始文本")
                        status_manager.update_step("thinking", "RAG未检索到相关片段，使用原始文档")
                        
                except Exception as e:
                    logger.error(f"RAG处理失败，使用原始文本: {e}")
                    status_manager.update_step("thinking", f"RAG处理失败，回退到原始文档: {str(e)}")
                    # RAG失败时回退到原始文本
                    context_text = text_content
            
            status_manager.update_step("thinking", "文档解析完成，启动MCP智能体...")
            
            # 设置智能体参数
            mcp_agent.max_iterations = max_iterations
            
            # 准备输入数据
            qa_input = {
                "question": question,
                "document_content": context_text,
                "document_type": Path(uploaded_file.name).suffix,
                "document_file_path": str(file_path),
                "answer_style": answer_style,
                "include_quotes": include_quotes,
                "confidence_threshold": confidence_threshold,
                "rag_info": rag_chunks_info
            }
            
            # 创建流式聊天界面
            if show_thinking:
                chat_interface = StreamingChatInterface()
                
                # 显示思考过程流 - 正确传递异步生成器
                logger.info("开始创建MCP智能体思考流程")
                try:
                    # 智能初始化检查
                    if not mcp_agent.is_initialized():
                        logger.info("智能体需要初始化...")
                        
                        # 显示初始化进度
                        with st.spinner("🔧 正在初始化MCP智能体..."):
                            await mcp_agent.ensure_initialized()
                        
                        st.success("✅ MCP智能体初始化完成")
                    else:
                        logger.info(f"智能体已初始化，{len(mcp_agent.available_tools)}个工具可用")
                    
                    # 在聊天界面显示RAG信息
                    if rag_chunks_info["enabled"]:
                        st.info(f"🔍 RAG已激活，检索到 {rag_chunks_info['chunks_count']} 个相关文档片段")
                    
                    # 创建异步生成器
                    thought_generator = mcp_agent.think_and_act(
                        question,
                        context_text,  # 使用RAG处理后的内容
                        Path(uploaded_file.name).suffix,
                        str(file_path)
                    )
                    logger.info(f"思考生成器创建成功: {type(thought_generator)}")
                    
                    # 显示思考流程
                    final_answer = await chat_interface.display_thought_stream(thought_generator)
                    logger.info(f"思考流程完成，最终答案长度: {len(final_answer) if final_answer else 0}")
                    
                except Exception as e:
                    logger.error(f"MCP思考流程执行失败: {e}")
                    import traceback
                    logger.error(f"错误堆栈: {traceback.format_exc()}")
                    st.error(f"❌ MCP智能体执行失败: {str(e)}")
                    return
                
                status_manager.complete_conversation(True)
                performance_monitor.end_monitoring()
                
                # 显示性能报告
                with st.expander("📊 执行性能报告", expanded=False):
                    performance_monitor.show_performance_report()
                
                # 显示状态历史
                with st.expander("📋 详细执行历史", expanded=False):
                    status_manager.show_status_history()
            
            else:
                # 不显示思考过程，直接处理
                with st.spinner("🧠 MCP智能体正在深度思考..."):
                    # 在简化模式下也显示RAG信息
                    if rag_chunks_info["enabled"]:
                        st.info(f"🔍 RAG已激活，检索到 {rag_chunks_info['chunks_count']} 个相关文档片段")
                    
                    result = await mcp_agent.process(qa_input)
                    
                    if result.get("answer"):
                        st.markdown("### 🎯 最终答案")
                        st.write(result["answer"])
                        
                        # 显示简化的结果信息
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("思考轮数", result.get("iterations_used", 0))
                        with col2:
                            st.metric("可用工具", result.get("tools_available", 0))
                        with col3:
                            st.metric("思考步骤", len(result.get("thought_processes", [])))
                
        else:
            st.error("❌ 文档解析失败")
            status_manager.complete_conversation(False)
            st.warning("💡 请检查文档格式是否正确")
            
    except Exception as e:
        st.error(f"❌ MCP问答处理失败: {str(e)}")
        st.warning("💡 如果问题持续存在，请尝试简化问题或切换到传统问答模式")
        logger.error(f"MCP问答处理失败: {e}")
        
        if 'status_manager' in locals():
            status_manager.complete_conversation(False)

async def process_mcp_data_analysis(uploaded_file, analysis_requirements, mcp_agent, 
                                   max_iterations=10, show_thinking=True, confidence_threshold=0.7,
                                   use_rag=True, use_reranker=True, rag_top_k=12, rag_rerank_top_n=6):
    """使用MCP智能体处理数据分析"""
    try:
        # 进度指示
        status_manager = ConversationStatusManager()
        status_manager.start_conversation(max_iterations)
        
        performance_monitor = PerformanceMonitor()
        performance_monitor.start_monitoring()
        
        # 保存文件
        file_config = get_config("file")
        upload_dir = Path(file_config.get("upload_dir", "uploads"))
        upload_dir.mkdir(exist_ok=True)
        
        file_path = upload_dir / uploaded_file.name
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        status_manager.update_step("thinking", "数据文件已保存，开始解析...")
        
        # 读取数据
        try:
            df = pd.read_excel(file_path)
            data_json = df.to_json(orient='records', date_format='iso')
            
            # 为数据分析创建可读的文本表示
            data_summary = f"""
数据概览:
- 总行数: {df.shape[0]}
- 总列数: {df.shape[1]}
- 列名: {', '.join(df.columns.tolist())}

数据样本 (前5行):
{df.head().to_string()}

数据统计信息:
{df.describe().to_string()}
"""
            
            status_manager.update_step("thinking", f"数据解析完成，{df.shape[0]}行{df.shape[1]}列")
            
        except Exception as e:
            st.error(f"❌ 数据解析失败: {str(e)}")
            status_manager.complete_conversation(False)
            return
        
        # RAG处理 - 对于数据分析，我们可以对数据摘要和分析需求进行RAG处理
        context_text = data_json
        rag_chunks_info = {"enabled": False, "chunks_count": 0}
        
        if use_rag and len(data_summary) > 1000:  # 只有当数据摘要足够长时才使用RAG
            try:
                status_manager.update_step("thinking", "构建数据RAG索引...")
                
                # 计算文件ID
                file_id = compute_file_id(str(file_path) + "_data_analysis")
                
                # 使用数据摘要构建索引
                store, embedder, reranker = build_or_load_index(file_id, data_summary)
                
                status_manager.update_step("thinking", "RAG检索相关数据信息...")
                
                # 检索相关片段
                chunks = retrieve_with_optional_rerank(
                    query=analysis_requirements,
                    store=store,
                    embedder=embedder,
                    top_k=rag_top_k,
                    rerank_top_n=rag_rerank_top_n,
                    use_reranker=use_reranker
                )
                
                if chunks:
                    # 构建上下文，但仍保留原始JSON数据
                    context_summary = build_context_from_chunks(chunks)
                    # 合并RAG检索的上下文和原始数据
                    context_text = f"数据上下文:\n{context_summary}\n\n原始数据:\n{data_json}"
                    rag_chunks_info = {"enabled": True, "chunks_count": len(chunks)}
                    logger.info(f"数据分析RAG检索到{len(chunks)}个相关片段")
                    status_manager.update_step("thinking", f"RAG检索完成，获得{len(chunks)}个相关数据片段")
                else:
                    logger.warning("数据分析RAG未检索到相关片段，使用原始数据")
                    status_manager.update_step("thinking", "RAG未检索到相关片段，使用原始数据")
                    
            except Exception as e:
                logger.error(f"数据分析RAG处理失败，使用原始数据: {e}")
                status_manager.update_step("thinking", f"RAG处理失败，回退到原始数据: {str(e)}")
                # RAG失败时回退到原始数据
                context_text = data_json
        
        status_manager.update_step("thinking", "开始MCP智能体分析...")
        
        # 设置智能体参数
        mcp_agent.max_iterations = max_iterations
        
        # 创建流式聊天界面
        if show_thinking:
            chat_interface = StreamingChatInterface()
            
            # 显示思考过程流
            logger.info("开始创建MCP智能体数据分析流程")
            try:
                # 智能初始化检查
                if not mcp_agent.is_initialized():
                    logger.info("智能体需要初始化...")
                    
                    # 显示初始化进度
                    with st.spinner("🔧 正在初始化MCP智能体..."):
                        await mcp_agent.ensure_initialized()
                    
                    st.success("✅ MCP智能体初始化完成")
                else:
                    logger.info(f"智能体已初始化，{len(mcp_agent.available_tools)}个工具可用")
                
                # 在聊天界面显示数据和RAG信息
                st.info(f"📊 数据已加载: {df.shape[0]}行 × {df.shape[1]}列")
                if rag_chunks_info["enabled"]:
                    st.info(f"🔍 RAG已激活，检索到 {rag_chunks_info['chunks_count']} 个相关数据片段")
                
                # 创建异步生成器 - 使用RAG处理后的数据内容
                thought_generator = mcp_agent.think_and_act(
                    analysis_requirements,
                    context_text,  # 传递RAG处理后的数据内容
                    Path(uploaded_file.name).suffix,
                    str(file_path)
                )
                logger.info(f"数据分析思考生成器创建成功: {type(thought_generator)}")
                
                # 显示思考流程
                final_answer = await chat_interface.display_thought_stream(thought_generator)
                logger.info(f"数据分析思考流程完成，最终答案长度: {len(final_answer) if final_answer else 0}")
                
            except Exception as e:
                logger.error(f"MCP数据分析思考流程执行失败: {e}")
                import traceback
                logger.error(f"错误堆栈: {traceback.format_exc()}")
                st.error(f"❌ MCP智能体数据分析执行失败: {str(e)}")
                return
            
            status_manager.complete_conversation(True)
            performance_monitor.end_monitoring()
            
            # 显示性能报告
            with st.expander("📊 执行性能报告", expanded=False):
                performance_monitor.show_performance_report()
            
            # 显示状态历史
            with st.expander("📋 详细执行历史", expanded=False):
                status_manager.show_status_history()
        
        else:
            # 不显示思考过程，直接处理
            with st.spinner("🧠 MCP智能体正在深度分析数据..."):
                # 在简化模式下也显示数据和RAG信息
                st.info(f"📊 数据已加载: {df.shape[0]}行 × {df.shape[1]}列")
                if rag_chunks_info["enabled"]:
                    st.info(f"🔍 RAG已激活，检索到 {rag_chunks_info['chunks_count']} 个相关数据片段")
                
                # 这里可以调用mcp_agent的同步方法，但目前使用think_and_act并忽略流
                result = await mcp_agent.process({
                    "question": analysis_requirements,
                    "document_content": context_text,
                    "document_type": Path(uploaded_file.name).suffix,
                    "document_file_path": str(file_path),
                    "confidence_threshold": confidence_threshold,
                    "rag_info": rag_chunks_info
                })
                
                if result.get("answer"):
                    st.markdown("### 🎯 数据分析结果")
                    st.write(result["answer"])
                    
                    # 显示简化的结果信息
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("思考轮数", result.get("iterations_used", 0))
                    with col2:
                        st.metric("可用工具", result.get("tools_available", 0))
                    with col3:
                        st.metric("思考步骤", len(result.get("thought_processes", [])))
    
    except Exception as e:
        st.error(f"❌ MCP数据分析处理失败: {str(e)}")
        st.warning("💡 如果问题持续存在，请尝试简化分析要求或检查数据格式")
        logger.error(f"MCP数据分析处理失败: {e}")
        
        if 'status_manager' in locals():
            status_manager.complete_conversation(False)

def display_analysis_results(result: Dict[str, Any]):
    """显示数据分析结果"""
    st.success("✅ 数据分析完成！")

    # 1. AI 数据分析
    if "ai_insights" in result:
        st.markdown("### 🤖 AI 数据分析")
        st.info(result["ai_insights"])

    # 2. 业务建议
    if "recommendations" in result and result["recommendations"]:
        with st.expander("📈 业务建议与行动指南", expanded=True):
            for rec in result["recommendations"]:
                st.markdown(f"- {rec}")
    
    # 3. 可视化图表
    if "visualizations" in result and result["visualizations"]:
        st.markdown("### 🎨 交互式可视化图表")
        for title, fig in result["visualizations"].items():
            if fig: # 确保图表对象存在
                st.plotly_chart(fig, use_container_width=True)

    # 4. 数据摘要
    with st.expander("📊 数据摘要与统计"):
        if "data_summary" in result:
            summary = result["data_summary"]
            basic_info = summary.get("基本信息", {})
            cols = st.columns(4)
            cols[0].metric("数据行数", basic_info.get('行数', 'N/A'))
            cols[1].metric("数据列数", basic_info.get('列数', 'N/A'))
            cols[2].metric("内存占用", basic_info.get('内存占用', 'N/A'))
            cols[3].metric("数据源", basic_info.get('数据源', 'N/A'))
            
            if "列信息" in summary:
                st.markdown("#### 列信息概览")
                # 将列信息转换为DataFrame以便更好地显示
                col_df = pd.DataFrame(summary["列信息"]).T
                st.dataframe(col_df)

        if "statistical_analysis" in result and result["statistical_analysis"].get("descriptive"):
             st.markdown("#### 描述性统计")
             st.dataframe(pd.DataFrame(result["statistical_analysis"]["descriptive"]))


async def process_data_analysis(uploaded_file, analysis_type, requirements, trend_params):
    """处理数据分析"""
    progress_bar = st.progress(0, text="开始数据分析...")
    try:
        try:
            df = pd.read_excel(uploaded_file)
        except Exception as e:
            st.error(f"无法读取文件，请检查文件格式是否正确。错误: {e}")
            return
        
        progress_bar.progress(25, text="📄 数据加载完成...")

        analysis_input = {
            "data": df,
            "analysis_type": analysis_type,
            "requirements": requirements,
            "source": uploaded_file.name,
            **trend_params # 合并趋势分析参数
        }
        progress_bar.progress(50, text="🤖 AI正在进行数据分析...")

        analysis_result = await agent_coordinator.execute_agent("Analysis_Agent", analysis_input)
        progress_bar.progress(100, text="✅ 分析完成！")
        
        if analysis_result.get("success", False):
            display_analysis_results(analysis_result["result"])
        else:
            st.error(f"❌ 数据分析失败: {analysis_result.get('error', '未知错误')}")
    except Exception as e:
        st.error(f"❌ 数据分析处理失败: {str(e)}")
        logger.error(f"数据分析处理失败: {e}", exc_info=True)

def main():
    st.title("🤖 智能文档分析系统")
    st.write("上传文档后，您可以用自然语言提问，AI助手将基于文档内容为您提供准确答案。")
    
    # 侧边栏 - Agent选择
    st.sidebar.title("⚙️ 系统设置")
    st.sidebar.markdown("---")
    
    # Agent类型选择
    agent_type = st.sidebar.selectbox(
        "🤖 选择AI助手类型",
        options=["传统问答", "MCP智能助手"],
        index=1,  # 默认选择MCP
        help="传统问答：快速简单问答\nMCP智能助手：具备工具调用和深度思考能力"
    )
    
    # 显示Agent特性
    if agent_type == "传统问答":
        st.sidebar.info("""
        **特点**:
        • ⚡ 快速响应
        • 📝 直接问答
        • 🎯 简洁准确
        """)
    else:
        st.sidebar.success("""
        **特点**:
        • 🧠 深度思考
        • 🔧 工具调用
        • 🔄 多轮推理
        • 📊 流程透明
        """)
    
    st.sidebar.markdown("---")
    st.sidebar.write("当前版本: v3.0.0")
    
    # 初始化服务
    if not initialize_services():
        st.error("系统初始化失败，请检查配置")
        st.stop()

    # 如果选择MCP智能体，初始化MCP服务
    mcp_agent = None
    if agent_type == "MCP智能助手":
        mcp_agent = initialize_mcp_agent()
        if mcp_agent is None:
            st.warning("MCP智能体初始化失败，将使用传统问答模式")
            agent_type = "传统问答"

    # 初始化tab状态
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "🤖 智能文档问答"

    # 使用radio按钮替代tabs来更好地控制状态
    active_tab = st.radio(
        "选择功能",
        ["🤖 智能文档问答", "📊 智能数据分析"],
        index=["🤖 智能文档问答", "📊 智能数据分析"].index(st.session_state.active_tab),
        horizontal=True,
        key="main_tab_selector"
    )
    
    # 更新session state
    st.session_state.active_tab = active_tab
    
    if active_tab == "🤖 智能文档问答":
        st.header("智能文档问答")

        st.markdown("### 📁 文档上传")
        
        # 获取支持的文件格式
        file_config = get_config("file")
        supported_formats = [fmt.lstrip('.') for fmt in file_config.get("supported_formats", ["pdf", "txt", "docx"])]
        
        uploaded_file = st.file_uploader(
            "选择需要问答的文档",
            type=supported_formats,
            help="支持PDF、Word、文本等格式",
            key="document_uploader"
        )
        
        if uploaded_file is not None:
            # 文件信息
            st.success(f"✅ 文档已加载: **{uploaded_file.name}**")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("文件大小", f"{uploaded_file.size:,} 字节")
            with col2:
                st.metric("文件类型", Path(uploaded_file.name).suffix.upper())
            with col3:
                st.metric("AI类型", "🧠 MCP智能" if agent_type == "MCP智能助手" else "⚡ 传统问答")
            
            st.markdown("---")
            
            # 问答区域
            st.markdown("### 💭 智能问答")
            
            # 问题输入
            question = st.text_area(
                "请输入您的问题:",
                height=100,
                placeholder="例如：\n• 这个文档的核心观点是什么？\n• 提到了哪些解决方案？\n• 有哪些重要的统计数据？\n• 作者建议采取什么行动？",
                help="用自然语言描述您想了解的内容"
            )
            
            # 高级选项
            with st.expander("🔧 高级选项"):
                col1, col2 = st.columns(2)
                with col1:
                    answer_style = st.selectbox(
                        "回答风格",
                        ["detailed", "concise", "bullet_points"],
                        format_func=lambda x: {
                            "detailed": "📝 详细解释",
                            "concise": "💡 简洁明了", 
                            "bullet_points": "📋 要点列表"
                        }[x]
                    )
                with col2:
                    include_quotes = st.checkbox("📖 包含原文引用", value=True)
                    confidence_threshold = st.slider("置信度阈值", 0.3, 1.0, 0.7, 0.1)
                
                # 高级置信度评估开关（默认关闭以提升速度）
                enable_advanced_confidence = st.checkbox("⚙️ 启用高级置信度评估（较慢）", value=False, help="开启后将调用额外一次模型对答案进行置信度打分，可能显著增加响应时间")
                
                # RAG 相关参数
                use_rag = st.checkbox("启用RAG", value=True)
                col3, col4, col5 = st.columns(3)
                with col3:
                    rag_top_k = st.slider("向量召回TopK", 4, 30, 12, 1)
                with col4:
                    use_reranker = st.checkbox("启用重排", value=True)
                with col5:
                    rag_rerank_top_n = st.slider("重排后片段数", 2, 12, 6, 1)
                
                # MCP特定选项
                if agent_type == "MCP智能助手":
                    st.markdown("**MCP高级设置**")
                    col6, col7 = st.columns(2)
                    with col6:
                        max_iterations = st.number_input("最大思考轮数", min_value=3, max_value=20, value=10)
                    with col7:
                        show_thinking = st.checkbox("显示思考过程", value=True)
        
        # 问答按钮
        button_text = "🧠 开始深度分析" if agent_type == "MCP智能助手" else "🔍 开始问答"
        if st.button(button_text, type="primary", use_container_width=True):
            if not question:
                st.error("请输入问题内容！")
                return
            
            # 根据选择的Agent类型执行不同的处理流程
            if agent_type == "MCP智能助手":
                # MCP智能体处理流程
                run_async_in_streamlit(
                    process_mcp_qa(uploaded_file, question, mcp_agent, 
                                 answer_style, include_quotes, confidence_threshold,
                                 max_iterations if 'max_iterations' in locals() else 10,
                                 show_thinking if 'show_thinking' in locals() else True,
                                 use_rag, use_reranker, rag_top_k, rag_rerank_top_n)
                )
            else:
                # 传统问答处理流程
                with st.spinner("🔄 AI正在分析文档并准备答案..."):
                    run_async_in_streamlit(
                        process_document_qa(
                            uploaded_file,
                            question,
                            answer_style,
                            include_quotes,
                            confidence_threshold,
                            enable_advanced_confidence,
                            use_rag,
                            use_reranker,
                            rag_top_k,
                            rag_rerank_top_n,
                        )
                    )
                
        else:
            # 上传提示
            st.markdown("""
            <div style="border: 2px dashed #ccc; border-radius: 10px; padding: 3rem; text-align: center; margin: 2rem 0;">
                <h3 style="color: #666;">🤖 智能问答助手</h3>
                <p style="color: #888;">上传文档后即可开始智能问答</p>
                <p style="font-size: 0.9rem; color: #aaa;">支持复杂问题和多轮对话</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Agent类型说明
            if agent_type == "MCP智能助手":
                st.markdown("#### 🧠 MCP智能助手特性")
                st.info("""
                **MCP智能助手具备以下能力：**
                - 🤔 **深度思考**：多轮分析推理过程
                - 🔧 **工具调用**：自动使用文档分析、搜索等工具
                - 📊 **过程透明**：实时显示思考和执行过程
                - 🎯 **智能决策**：根据问题复杂度自动选择处理策略
                """)
            
            # 问答示例
            st.markdown("#### 💡 问答示例")
            examples = [
                "这个文档的主要内容是什么？",
                "文档中提到了哪些重要数据？",
                "作者的主要观点和结论是什么？", 
                "有什么重要的建议或推荐？"
            ]
            
            for example in examples:
                st.info(f"**问题示例**: {example}")

    elif active_tab == "📊 智能数据分析":
        st.header("智能数据分析")

        st.markdown("### 📁 文档上传")
        
        data_uploader = st.file_uploader(
            "上传您的数据文件", 
            type=["xlsx", "xls"],
            key="data_uploader"
        )
        
        if data_uploader is not None:
            st.success(f"✅ 数据文件已加载: **{data_uploader.name}**")
            
            # 分析要求输入
            analysis_requirements = st.text_area(
                "请输入您的分析要求",
                height=100,
                placeholder="例如：\n• 帮我分析销售额和广告投入的关系\n• 找出哪些产品的利润率最高\n• 分析数据中的趋势和异常值",
                key="analysis_requirements"
            )
            
            # 高级选项
            with st.expander("🔧 高级选项"):
                col1, col2, col3 = st.columns(3)
                with col1:
                    max_iterations = st.slider("最大思考轮数", 5, 20, 10, key="data_max_iter")
                with col2:
                    show_thinking = st.checkbox("显示思考过程", value=True, key="data_show_thinking")
                with col3:
                    confidence_threshold = st.slider("置信度阈值", 0.1, 1.0, 0.7, key="data_confidence")
                
                # RAG 相关参数
                st.markdown("**RAG设置**")
                col4, col5, col6 = st.columns(3)
                with col4:
                    use_rag = st.checkbox("启用RAG", value=True, key="data_use_rag")
                with col5:
                    use_reranker = st.checkbox("启用重排", value=True, key="data_use_reranker")
                with col6:
                    rag_top_k = st.slider("RAG TopK", 4, 20, 8, key="data_rag_top_k")
                rag_rerank_top_n = st.slider("重排后片段数", 2, 10, 4, key="data_rag_rerank_n")
            
            # 开始分析按钮
            if st.button("🧠 开始深度分析", type="primary", use_container_width=True, key="data_analysis_button"):
                if not analysis_requirements.strip():
                    st.warning("⚠️ 请先输入分析要求")
                else:
                    # 根据选择的Agent类型执行不同的处理流程
                    if agent_type == "MCP智能助手":
                        if mcp_agent is None:
                            st.error("❌ MCP智能体未初始化")
                        else:
                            run_async_in_streamlit(
                                process_mcp_data_analysis(data_uploader, analysis_requirements, mcp_agent, 
                                                        max_iterations=max_iterations, show_thinking=show_thinking,
                                                        confidence_threshold=confidence_threshold,
                                                        use_rag=use_rag, use_reranker=use_reranker,
                                                        rag_top_k=rag_top_k, rag_rerank_top_n=rag_rerank_top_n)
                            )
                    else:
                        st.warning("💡 数据分析当前仅支持MCP智能助手模式")
        
        else:
            # 上传提示
            st.markdown("""
            <div style="border: 2px dashed #ccc; border-radius: 10px; padding: 3rem; text-align: center; margin: 2rem 0;">
                <h3 style="color: #666;">📊 智能数据分析</h3>
                <p style="color: #888;">上传数据文件后即可开始智能数据分析</p>
                <p style="font-size: 0.9rem; color: #aaa;">支持复杂分析和多轮推理</p>
            </div>
            """, unsafe_allow_html=True)
            
            # 数据分析示例
            st.markdown("#### 💡 数据分析示例")
            examples = [
                "帮我分析销售额和广告投入的关系",
                "找出哪些产品的利润率最高",
                "分析数据中的趋势和异常值",
                "预测下个季度的销售增长",
            ]
            
            for example in examples:
                st.info(f"**分析示例**: {example}")

if __name__ == "__main__":
    main()
