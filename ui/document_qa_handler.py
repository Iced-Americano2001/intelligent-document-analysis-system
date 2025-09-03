"""
文档问答处理模块
"""
import streamlit as st
import asyncio
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_document_qa(uploaded_file, question, answer_style="detailed", include_quotes=True, confidence_threshold=0.7,
                            enable_advanced_confidence=False, use_rag=True, use_reranker=True, rag_top_k=12, rag_rerank_top_n=6):
    """处理文档问答"""
    try:
        from config.settings import get_config
        from mcp_services.base_service import handle_mcp_request
        from agents.base_agent import agent_coordinator
        from utils.rag_utils import (
            compute_file_id,
            build_or_load_index,
            retrieve_with_optional_rerank,
            build_context_from_chunks,
        )
        
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
                from ui.result_display import display_qa_results
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
        from config.settings import get_config
        from mcp_services.base_service import handle_mcp_request
        from ui.status_manager import ConversationStatusManager, PerformanceMonitor
        from ui.streaming_components import StreamingChatInterface
        from utils.rag_utils import (
            compute_file_id,
            build_or_load_index,
            retrieve_with_optional_rerank,
            build_context_from_chunks,
        )
        
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
