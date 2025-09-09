"""
报告生成UI组件
用于展示和管理对话报告功能
"""
import streamlit as st
import logging
from typing import Dict, Any, List
import asyncio
from datetime import datetime
import base64
from pathlib import Path

logger = logging.getLogger(__name__)

def _display_content_sections_basic(sections: List[Dict]):
    """基础的内容区段显示方法"""
    for section in sections:
        st.markdown(f"#### {section.get('title', '')}")
        
        if section.get("type") == "qa_pairs":
            for i, qa in enumerate(section.get("content", []), 1):
                with st.expander(f"问答 {i}: {qa.get('question', '')[:50]}...", expanded=False):
                    st.markdown(f"**问题:** {qa.get('question', '')}")
                    st.markdown(f"**回答:** {qa.get('answer', '')}")
                    
                    # 显示相关图表（基础方式）
                    charts = qa.get("charts", {})
                    if charts:
                        st.markdown("**生成的图表:**")
                        for chart_name, chart_json in charts.items():
                            try:
                                # 从JSON重建图表
                                import plotly.graph_objects as go
                                import json
                                chart_data = json.loads(chart_json)
                                fig = go.Figure(chart_data)
                                
                                st.plotly_chart(fig, use_container_width=True)
                                st.caption(f"图表: {chart_name.replace('_', ' ').title()}")
                            except Exception as e:
                                st.warning(f"图表 {chart_name} 显示失败: {str(e)}")
        
        elif section.get("type") == "chart_statistics":
            chart_stats = section.get("content", {})
            total_charts = chart_stats.get("total_charts", 0)
            chart_types = chart_stats.get("chart_types", {})
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("总图表数", total_charts)
            with col2:
                st.metric("图表类型数", len(chart_types))
            
            if chart_types:
                st.markdown("**图表类型分布:**")
                for chart_type, count in chart_types.items():
                    st.markdown(f"- {chart_type}: {count}个")
        
        elif section.get("type") in ["bullet_list", "numbered_list"]:
            for item in section.get("content", []):
                st.markdown(f"• {item}")
        
        elif section.get("type") == "topics":
            topics = section.get("content", [])
            if topics:
                # 以标签形式显示主题
                topic_html = " ".join([f'<span style="background-color: #e1f5fe; padding: 4px 8px; border-radius: 12px; margin: 2px; display: inline-block;">{topic}</span>' for topic in topics])
                st.markdown(topic_html, unsafe_allow_html=True)
        
        elif section.get("type") == "keywords":
            keywords = section.get("content", [])
            if keywords:
                # 以标签形式显示关键词
                keyword_html = " ".join([f'<span style="background-color: #f3e5f5; padding: 4px 8px; border-radius: 12px; margin: 2px; display: inline-block;">{keyword}</span>' for keyword in keywords])
                st.markdown(keyword_html, unsafe_allow_html=True)

def render_conversation_report_section(conversation_type: str = "document_qa"):
    """
    渲染对话报告部分
    
    Args:
        conversation_type: 对话类型 ('document_qa' 或 'data_analysis')
    """
    try:
        from utils.conversation_manager import conversation_manager
        from agents.report_agent import ReportAgent
        from utils.report_exporter import ReportExporter
        
        # 获取对话历史
        history = conversation_manager.get_conversation_history(conversation_type)
        stats = conversation_manager.get_conversation_statistics(conversation_type)
        
        type_name = "文档问答" if conversation_type == "document_qa" else "数据分析"
        
        # 报告部分标题
        st.markdown("### 📊 对话报告")
        
        if not history:
            st.info(f"📝 当前没有{type_name}对话记录。开始对话后，您可以在这里生成报告。")
            return
        
        # 显示统计信息
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("对话轮数", stats.get("total_conversations", 0))
        with col2:
            st.metric("问题数", stats.get("total_questions", 0))
        with col3:
            st.metric("回答数", stats.get("total_answers", 0))
        with col4:
            avg_answer_len = stats.get("avg_answer_length", 0)
            st.metric("平均回答长度", f"{avg_answer_len:.0f}字符")
        
        # 显示图表统计（如果是数据分析报告）
        if conversation_type == "data_analysis":
            try:
                from utils.chart_report_enhancer import ChartReportEnhancer
                chart_enhancer = ChartReportEnhancer()
                chart_stats = chart_enhancer.analyze_chart_statistics(history)
                
                if chart_stats.get("total_charts", 0) > 0:
                    with st.expander("📊 图表统计概览", expanded=False):
                        chart_enhancer.display_chart_statistics_dashboard(chart_stats)
                    
                    # 提供批量导出图表选项
                    with st.expander("📦 批量导出图表", expanded=False):
                        if st.button("📥 导出所有图表为ZIP", type="primary", key=f"export_charts_{conversation_type}"):
                            zip_path = chart_enhancer.export_all_charts_as_zip(history)
                            if zip_path:
                                st.success(f"✅ 图表已导出到: {zip_path}")
                                # 提供下载链接
                                with open(zip_path, "rb") as f:
                                    st.download_button(
                                        label="💾 下载图表ZIP文件",
                                        data=f.read(),
                                        file_name=Path(zip_path).name,
                                        mime="application/zip"
                                    )
                            else:
                                st.error("❌ 图表导出失败")
            except Exception as e:
                logger.warning(f"图表功能加载失败: {e}")
        
        # 报告选项
        with st.expander("🔧 报告生成选项", expanded=False):
            col1, col2 = st.columns(2)
            
            with col1:
                report_style = st.selectbox(
                    "报告样式",
                    ["detailed", "summary", "bullet_points"],
                    format_func=lambda x: {
                        "detailed": "📖 详细报告",
                        "summary": "📋 摘要报告", 
                        "bullet_points": "📝 要点报告"
                    }[x],
                    key=f"report_style_{conversation_type}"
                )
                
                include_metadata = st.checkbox("包含元数据", value=True, key=f"include_metadata_{conversation_type}")
                include_statistics = st.checkbox("包含统计信息", value=True, key=f"include_statistics_{conversation_type}")
            
            with col2:
                export_format = st.selectbox(
                    "导出格式",
                    ["html", "docx", "json"],
                    format_func=lambda x: {
                        "html": "🌐 HTML网页",
                        "docx": "📄 Word文档",
                        "json": "🔧 JSON数据"
                    }[x],
                    key=f"export_format_{conversation_type}"
                )
                
                auto_download = st.checkbox("自动下载", value=True, key=f"auto_download_{conversation_type}")
        
        # 操作按钮
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            if st.button("📊 生成报告", type="primary", use_container_width=True, key=f"generate_report_{conversation_type}"):
                generate_conversation_report(
                    conversation_type, report_style, include_metadata, 
                    include_statistics, export_format, auto_download
                )
        
        with col2:
            if st.button("👀 预览对话", use_container_width=True, key=f"preview_conversation_{conversation_type}"):
                show_conversation_preview(conversation_type)
        
        with col3:
            if st.button("🔍 搜索对话", use_container_width=True, key=f"search_conversation_{conversation_type}"):
                show_conversation_search(conversation_type)
        
        with col4:
            if st.button("🗑️ 清空历史", use_container_width=True, key=f"clear_history_{conversation_type}"):
                clear_conversation_history(conversation_type)
        
        # 显示最近的报告
        show_recent_reports()
        
    except Exception as e:
        logger.error(f"渲染报告部分失败: {e}", exc_info=True)
        st.error(f"❌ 报告功能加载失败: {str(e)}")

def generate_conversation_report(conversation_type: str, report_style: str, 
                               include_metadata: bool, include_statistics: bool,
                               export_format: str, auto_download: bool):
    """生成对话报告"""
    try:
        from utils.conversation_manager import conversation_manager
        from agents.report_agent import ReportAgent
        from utils.report_exporter import ReportExporter
        
        # 获取对话历史
        history = conversation_manager.get_conversation_history(conversation_type)
        
        if not history:
            st.warning("⚠️ 没有对话历史可生成报告")
            return
        
        with st.spinner("🤖 AI正在生成报告..."):
            # 创建报告agent
            report_agent = ReportAgent()
            
            # 设置用户偏好
            user_preferences = {
                "report_style": report_style,
                "include_metadata": include_metadata,
                "include_statistics": include_statistics
            }
            
            # 异步运行报告生成
            async def run_report_generation():
                return await report_agent.generate_conversation_report(
                    history, conversation_type, user_preferences
                )
            
            # 使用streamlit的异步支持
            result = asyncio.run(run_report_generation())
            
            if result.get("success"):
                st.success("✅ 报告生成成功！")
                
                # 显示报告
                display_generated_report(result["report"])
                
                # 导出报告
                if export_format and export_format != "preview":
                    export_report(result, export_format, auto_download, conversation_type)
            else:
                st.error(f"❌ 报告生成失败: {result.get('error', '未知错误')}")
        
    except Exception as e:
        logger.error(f"生成报告失败: {e}", exc_info=True)
        st.error(f"❌ 报告生成失败: {str(e)}")

def display_generated_report(report_data: Dict[str, Any]):
    """显示生成的报告"""
    try:
        metadata = report_data.get("metadata", {})
        content = report_data.get("content", {})
        statistics = report_data.get("statistics", {})
        
        # 报告标题
        st.markdown(f"## {content.get('title', '对话报告')}")
        
        # 元数据
        if metadata:
            with st.expander("📋 报告信息", expanded=False):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**生成时间:** {metadata.get('generated_at', '')}")
                    st.write(f"**分析类型:** {metadata.get('analysis_type', '')}")
                with col2:
                    st.write(f"**对话轮数:** {metadata.get('conversation_count', 0)}")
                    st.write(f"**报告样式:** {metadata.get('report_style', '')}")
        
        # 执行摘要
        if content.get("executive_summary"):
            st.markdown("### 📝 执行摘要")
            st.markdown(content["executive_summary"])
        
        # 主要内容
        if content.get("main_content"):
            st.markdown("### 📖 详细内容")
            
            # 检查是否有图表内容，如果有则使用增强显示
            has_charts = False
            qa_pairs_with_charts = []
            
            for section in content["main_content"]:
                if section.get("type") == "qa_pairs":
                    qa_pairs = section.get("content", [])
                    for qa in qa_pairs:
                        if qa.get("charts"):
                            has_charts = True
                            qa_pairs_with_charts.extend(qa_pairs)
                            break
                    if has_charts:
                        break
            
            # 如果有图表，使用图表增强器显示
            if has_charts:
                try:
                    from utils.chart_report_enhancer import ChartReportEnhancer
                    chart_enhancer = ChartReportEnhancer()
                    
                    st.markdown("#### 📊 包含图表的问答内容")
                    chart_enhancer.display_charts_in_report(qa_pairs_with_charts, expanded=False)
                    
                except Exception as e:
                    logger.warning(f"图表增强显示失败，回退到基础显示: {e}")
                    # 回退到原有显示方式
                    _display_content_sections_basic(content["main_content"])
            else:
                # 没有图表时使用基础显示
                _display_content_sections_basic(content["main_content"])
        
        # 结论
        if content.get("conclusions"):
            conclusions = content["conclusions"]
            st.markdown("### 🎯 结论与建议")
            
            if conclusions.get("summary"):
                st.markdown("#### 总结")
                st.markdown(conclusions["summary"])
            
            if conclusions.get("key_insights"):
                st.markdown("#### 关键洞察")
                for insight in conclusions["key_insights"]:
                    st.markdown(f"• {insight}")
            
            if conclusions.get("recommendations"):
                st.markdown("#### 建议")
                for recommendation in conclusions["recommendations"]:
                    st.markdown(f"• {recommendation}")
        
        # 统计信息
        if statistics:
            with st.expander("📊 统计信息", expanded=False):
                st.json(statistics)
        
    except Exception as e:
        logger.error(f"显示报告失败: {e}", exc_info=True)
        st.error(f"❌ 报告显示失败: {str(e)}")

def export_report(report_result: Dict[str, Any], export_format: str, 
                 auto_download: bool, conversation_type: str):
    """导出报告"""
    try:
        from utils.report_exporter import ReportExporter
        
        exporter = ReportExporter()
        
        with st.spinner(f"📤 正在导出{export_format.upper()}格式..."):
            export_result = exporter.export_report(report_result, export_format)
            
            if export_result.get("success"):
                file_path = export_result["file_path"]
                file_size = export_result.get("file_size", 0)
                
                st.success(f"✅ 报告已导出: {export_result['format'].upper()}格式")
                st.info(f"📁 文件路径: {file_path}")
                st.info(f"📦 文件大小: {file_size:,} 字节")
                
                # 提供下载功能
                if auto_download:
                    provide_download_link(file_path, export_format)
            else:
                st.error(f"❌ 导出失败: {export_result.get('error', '未知错误')}")
        
    except Exception as e:
        logger.error(f"导出报告失败: {e}", exc_info=True)
        st.error(f"❌ 导出失败: {str(e)}")

def provide_download_link(file_path: str, format_type: str):
    """提供文件下载链接"""
    try:
        from utils.report_exporter import ReportExporter
        from pathlib import Path
        
        exporter = ReportExporter()
        download_info = exporter.get_file_as_download(file_path)
        
        if download_info.get("success"):
            filename = download_info["filename"]
            content = download_info["content"]
            mime_type = download_info["mime_type"]
            
            # 解码base64内容
            file_content = base64.b64decode(content)
            
            st.download_button(
                label=f"📥 下载 {format_type.upper()} 报告",
                data=file_content,
                file_name=filename,
                mime=mime_type,
                use_container_width=True
            )
        else:
            st.error(f"❌ 准备下载失败: {download_info.get('error', '未知错误')}")
    
    except Exception as e:
        logger.error(f"提供下载链接失败: {e}", exc_info=True)
        st.error(f"❌ 下载准备失败: {str(e)}")

def show_conversation_preview(conversation_type: str):
    """显示对话预览"""
    try:
        from utils.conversation_manager import conversation_manager
        
        history = conversation_manager.get_conversation_history(conversation_type)
        
        if not history:
            st.info("📝 暂无对话记录")
            return
        
        type_name = "文档问答" if conversation_type == "document_qa" else "数据分析"
        
        st.markdown(f"### 👀 {type_name}对话预览")
        
        # 显示最近的对话
        recent_limit = st.selectbox("显示最近对话数量", [5, 10, 20, 50], index=1, key=f"preview_limit_{conversation_type}")
        recent_history = conversation_manager.get_recent_conversations(recent_limit * 2, conversation_type)  # *2因为包含问题和答案
        
        if recent_history:
            for i in range(0, len(recent_history), 2):
                if i + 1 < len(recent_history):
                    question = recent_history[i]
                    answer = recent_history[i + 1]
                    
                    if question.get("type") == "question" and answer.get("type") == "answer":
                        with st.expander(f"问答 {(i//2) + 1}: {question.get('content', '')[:50]}...", expanded=False):
                            st.markdown(f"**时间:** {question.get('timestamp', '')}")
                            st.markdown(f"**问题:** {question.get('content', '')}")
                            st.markdown(f"**回答:** {answer.get('content', '')}")
        
    except Exception as e:
        logger.error(f"显示对话预览失败: {e}", exc_info=True)
        st.error(f"❌ 对话预览失败: {str(e)}")

def show_conversation_search(conversation_type: str):
    """显示对话搜索"""
    try:
        from utils.conversation_manager import conversation_manager
        
        type_name = "文档问答" if conversation_type == "document_qa" else "数据分析"
        
        st.markdown(f"### 🔍 {type_name}对话搜索")
        
        search_keyword = st.text_input(
            "搜索关键词",
            placeholder="输入关键词搜索对话内容...",
            key=f"search_keyword_{conversation_type}"
        )
        
        if search_keyword:
            matching_conversations = conversation_manager.search_conversations(search_keyword, conversation_type)
            
            if matching_conversations:
                st.success(f"🎯 找到 {len(matching_conversations)} 条匹配记录")
                
                for i, conv in enumerate(matching_conversations, 1):
                    conv_type = "❓ 问题" if conv.get("type") == "question" else "💡 回答"
                    content = conv.get("content", "")
                    timestamp = conv.get("timestamp", "")
                    
                    with st.expander(f"{conv_type} {i}: {content[:50]}...", expanded=False):
                        st.markdown(f"**时间:** {timestamp}")
                        st.markdown(f"**内容:** {content}")
            else:
                st.info("🔍 未找到匹配的对话记录")
        
    except Exception as e:
        logger.error(f"对话搜索失败: {e}", exc_info=True)
        st.error(f"❌ 对话搜索失败: {str(e)}")

def clear_conversation_history(conversation_type: str):
    """清空对话历史"""
    try:
        from utils.conversation_manager import conversation_manager
        
        type_name = "文档问答" if conversation_type == "document_qa" else "数据分析"
        
        # 确认对话框
        if st.button(f"⚠️ 确认清空{type_name}历史", type="secondary", key=f"confirm_clear_{conversation_type}"):
            conversation_manager.clear_conversation_history(conversation_type)
            st.success(f"✅ {type_name}对话历史已清空")
            st.experimental_rerun()
        
    except Exception as e:
        logger.error(f"清空对话历史失败: {e}", exc_info=True)
        st.error(f"❌ 清空失败: {str(e)}")

def show_recent_reports():
    """显示最近的报告"""
    try:
        from pathlib import Path
        
        reports_dir = Path("outputs/reports")
        if not reports_dir.exists():
            return
        
        # 获取最近的报告文件
        report_files = list(reports_dir.glob("conversation_report_*"))
        report_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        if report_files:
            with st.expander("📁 最近生成的报告", expanded=False):
                st.markdown("### 📋 报告文件列表")
                
                for i, report_file in enumerate(report_files[:10], 1):  # 显示最近10个报告
                    file_stat = report_file.stat()
                    file_size = file_stat.st_size
                    modified_time = datetime.fromtimestamp(file_stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                    
                    col1, col2, col3 = st.columns([3, 1, 1])
                    with col1:
                        st.write(f"📄 {report_file.name}")
                    with col2:
                        st.write(f"{file_size:,} 字节")
                    with col3:
                        st.write(modified_time)
        
    except Exception as e:
        logger.error(f"显示最近报告失败: {e}", exc_info=True)
