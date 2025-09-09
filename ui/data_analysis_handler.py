"""
数据分析处理模块
"""
import streamlit as st
import pandas as pd
import logging
from pathlib import Path
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def process_data_analysis(uploaded_file, analysis_type, requirements, trend_params, **kwargs):
    """处理数据分析"""
    # 忽略额外的未知参数
    if kwargs:
        logger.warning(f"收到未知参数，将被忽略: {list(kwargs.keys())}")
    
    progress_bar = st.progress(0, text="开始数据分析...")
    try:
        from agents.base_agent import agent_coordinator
        from ui.result_display import display_analysis_results
        
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
            
            # 为传统分析也生成智能图表
            try:
                from utils.chart_generator import ChartGenerator
                
                # 生成基于AI洞察的图表
                ai_insights = analysis_result["result"].get("ai_insights", "")
                if ai_insights and len(df) > 1:
                    chart_generator = ChartGenerator(df)
                    smart_charts = chart_generator.generate_charts_for_analysis(ai_insights)
                    
                    if smart_charts:
                        st.markdown("### 🤖 AI智能图表分析")
                        st.info(f"🎨 基于AI洞察，额外生成了 {len(smart_charts)} 个智能图表")
                        
                        for chart_name, chart_fig in smart_charts.items():
                            if chart_fig:
                                with st.expander(f"🧠 {chart_name.replace('_', ' ').title()}", expanded=False):
                                    st.plotly_chart(chart_fig, use_container_width=True)
                                    
            except Exception as chart_error:
                logger.warning(f"传统分析智能图表生成失败: {chart_error}")
            
            # 记录对话历史
            try:
                from utils.conversation_manager import conversation_manager
                result_text = str(analysis_result["result"])  # 将分析结果转换为文本
                metadata = {
                    "file_name": uploaded_file.name,
                    "analysis_type": analysis_type,
                    "trend_params": trend_params,
                    "agent_type": "传统分析",
                    "charts_generated": len(smart_charts) if 'smart_charts' in locals() else 0
                }
                # 传递图表数据到对话管理器
                charts_to_save = smart_charts if 'smart_charts' in locals() else {}
                conversation_manager.add_conversation(
                    requirements, result_text, "data_analysis", metadata, charts_to_save
                )
            except Exception as e:
                logger.warning(f"记录对话历史失败: {e}")
        else:
            st.error(f"❌ 数据分析失败: {analysis_result.get('error', '未知错误')}")
    except Exception as e:
        st.error(f"❌ 数据分析处理失败: {str(e)}")
        logger.error(f"数据分析处理失败: {e}", exc_info=True)

async def process_mcp_data_analysis(uploaded_file, analysis_requirements, mcp_agent, 
                                   max_iterations=10, show_thinking=True, confidence_threshold=0.7,
                                   use_rag=True, use_reranker=True, rag_top_k=12, rag_rerank_top_n=6, **kwargs):
    """使用MCP智能体处理数据分析"""
    # 忽略额外的未知参数
    if kwargs:
        logger.warning(f"收到未知参数，将被忽略: {list(kwargs.keys())}")
    
    try:
        from config.settings import get_config
        from ui.status_manager import ConversationStatusManager, PerformanceMonitor
        from ui.streaming_components import StreamingChatInterface
        from utils.rag_utils import (
            compute_file_id,
            build_or_load_index,
            retrieve_with_optional_rerank,
            build_context_from_chunks,
        )
        from utils.chart_generator import ChartGenerator, parse_chart_requests_from_text
        
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
                
                # 生成智能图表
                if final_answer:
                    try:
                        status_manager.update_step("thinking", "正在生成智能图表...")
                        
                        # 创建图表生成器
                        chart_generator = ChartGenerator(df)
                        
                        # 基于分析结果生成图表
                        generated_charts = chart_generator.generate_charts_for_analysis(final_answer)
                        
                        if generated_charts:
                            st.markdown("### 📊 智能生成的数据图表")
                            st.info(f"🎨 基于AI分析结果，自动生成了 {len(generated_charts)} 个图表")
                            
                            # 显示每个图表
                            for chart_name, chart_fig in generated_charts.items():
                                if chart_fig:
                                    # 创建可折叠的图表区域
                                    with st.expander(f"📈 {chart_name.replace('_', ' ').title()}", expanded=True):
                                        st.plotly_chart(chart_fig, use_container_width=True)
                            
                            logger.info(f"成功生成并显示了 {len(generated_charts)} 个图表")
                        else:
                            st.info("💡 未生成图表，可能是数据格式不适合可视化")
                    
                    except Exception as chart_error:
                        logger.warning(f"图表生成失败，但分析继续: {chart_error}")
                        st.warning("⚠️ 图表生成遇到问题，但分析结果已完成")
                
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
            
            # 记录对话历史
            try:
                from utils.conversation_manager import conversation_manager
                metadata = {
                    "file_name": uploaded_file.name,
                    "max_iterations": max_iterations,
                    "confidence_threshold": confidence_threshold,
                    "use_rag": use_rag,
                    "use_reranker": use_reranker,
                    "agent_type": "MCP智能助手",
                    "data_shape": f"{df.shape[0]}行×{df.shape[1]}列",
                    "charts_generated": len(generated_charts) if 'generated_charts' in locals() else 0
                }
                # 传递图表数据到对话管理器
                charts_to_save = generated_charts if 'generated_charts' in locals() else {}
                conversation_manager.add_conversation(
                    analysis_requirements, final_answer or "分析完成", "data_analysis", metadata, charts_to_save
                )
            except Exception as e:
                logger.warning(f"记录对话历史失败: {e}")
        
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
                    
                    # 生成智能图表（简化模式）
                    try:
                        from utils.chart_generator import ChartGenerator
                        chart_generator = ChartGenerator(df)
                        generated_charts = chart_generator.generate_charts_for_analysis(result["answer"])
                        
                        if generated_charts:
                            st.markdown("### 📊 自动生成的数据图表")
                            for chart_name, chart_fig in generated_charts.items():
                                if chart_fig:
                                    with st.expander(f"📈 {chart_name.replace('_', ' ').title()}", expanded=False):
                                        st.plotly_chart(chart_fig, use_container_width=True)
                    except Exception as chart_error:
                        logger.warning(f"简化模式图表生成失败: {chart_error}")
                    
                    # 显示简化的结果信息
                    col1, col2, col3 = st.columns(3)
                    with col1:
                        st.metric("思考轮数", result.get("iterations_used", 0))
                    with col2:
                        st.metric("可用工具", result.get("tools_available", 0))
                    with col3:
                        st.metric("思考步骤", len(result.get("thought_processes", [])))
                    
                    # 记录对话历史
                    try:
                        from utils.conversation_manager import conversation_manager
                        metadata = {
                            "file_name": uploaded_file.name,
                            "max_iterations": max_iterations,
                            "confidence_threshold": confidence_threshold,
                            "use_rag": use_rag,
                            "use_reranker": use_reranker,
                            "agent_type": "MCP智能助手(简化模式)",
                            "data_shape": f"{df.shape[0]}行×{df.shape[1]}列",
                            "iterations_used": result.get("iterations_used", 0),
                            "charts_generated": len(generated_charts) if 'generated_charts' in locals() else 0
                        }
                        # 传递图表数据到对话管理器
                        charts_to_save = generated_charts if 'generated_charts' in locals() else {}
                        conversation_manager.add_conversation(
                            analysis_requirements, result["answer"], "data_analysis", metadata, charts_to_save
                        )
                    except Exception as e:
                        logger.warning(f"记录对话历史失败: {e}")
    
    except Exception as e:
        st.error(f"❌ MCP数据分析处理失败: {str(e)}")
        st.warning("💡 如果问题持续存在，请尝试简化分析要求或检查数据格式")
        logger.error(f"MCP数据分析处理失败: {e}")
        
        if 'status_manager' in locals():
            status_manager.complete_conversation(False)
