"""
智能文档分析系统 - 主应用入口
重构版本：模块化设计
"""
import streamlit as st
from pathlib import Path

# 应用初始化
from ui.app_config import setup_page_config, setup_asyncio, setup_logging, setup_session_state
from ui.async_utils import run_async_in_streamlit
from ui.initialization import initialize_services, initialize_mcp_agent
from ui.sidebar_components import render_sidebar, render_advanced_options, render_mcp_options, render_data_analysis_options
from ui.result_display import display_file_info, display_upload_prompt, display_examples, display_agent_features
from ui.document_qa_handler import process_document_qa, process_mcp_qa
from ui.data_analysis_handler import process_mcp_data_analysis

def main():
    """主应用函数"""
    # 初始化配置
    setup_page_config()
    setup_asyncio()
    logger = setup_logging()
    setup_session_state()
    
    # 页面标题
    st.title("🤖 智能文档分析系统")
    st.write("上传文档后，您可以用自然语言提问，AI助手将基于文档内容为您提供准确答案。")
    
    # 侧边栏
    agent_type = render_sidebar()
    
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

    # Tab切换
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
        render_document_qa_tab(agent_type, mcp_agent)
    elif active_tab == "📊 智能数据分析":
        render_data_analysis_tab(agent_type, mcp_agent)

def render_document_qa_tab(agent_type, mcp_agent):
    """渲染文档问答标签页"""
    from config.settings import get_config
    
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
        # 文件信息显示
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
        options = render_advanced_options(mode="qa")
        
        # MCP特定选项
        mcp_options = {}
        if agent_type == "MCP智能助手":
            mcp_options = render_mcp_options()
        
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
                    process_mcp_qa(
                        uploaded_file, question, mcp_agent, 
                        options.get("answer_style", "detailed"),
                        options.get("include_quotes", True),
                        options.get("confidence_threshold", 0.7),
                        mcp_options.get("max_iterations", 10),
                        mcp_options.get("show_thinking", True),
                        options.get("use_rag", True),
                        options.get("use_reranker", True),
                        options.get("rag_top_k", 12),
                        options.get("rag_rerank_top_n", 6)
                    )
                )
            else:
                # 传统问答处理流程
                with st.spinner("🔄 AI正在分析文档并准备答案..."):
                    run_async_in_streamlit(
                        process_document_qa(
                            uploaded_file,
                            question,
                            options.get("answer_style", "detailed"),
                            options.get("include_quotes", True),
                            options.get("confidence_threshold", 0.7),
                            options.get("enable_advanced_confidence", False),
                            options.get("use_rag", True),
                            options.get("use_reranker", True),
                            options.get("rag_top_k", 12),
                            options.get("rag_rerank_top_n", 6),
                        )
                    )
                
    else:
        # 上传提示
        display_upload_prompt("document")
        
        # Agent类型说明
        if agent_type == "MCP智能助手":
            display_agent_features(agent_type)
        
        # 问答示例
        display_examples("qa")

def render_data_analysis_tab(agent_type, mcp_agent):
    """渲染数据分析标签页"""
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
            data_options = render_data_analysis_options()
        
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
                            process_mcp_data_analysis(
                                data_uploader, analysis_requirements, mcp_agent, 
                                max_iterations=data_options.get("max_iterations", 10),
                                show_thinking=data_options.get("show_thinking", True),
                                confidence_threshold=data_options.get("confidence_threshold", 0.7),
                                use_rag=data_options.get("use_rag", True),
                                use_reranker=data_options.get("use_reranker", True),
                                rag_top_k=data_options.get("rag_top_k", 8),
                                rag_rerank_top_n=data_options.get("rag_rerank_top_n", 4)
                            )
                        )
                else:
                    st.warning("💡 数据分析当前仅支持MCP智能助手模式")
    
    else:
        # 上传提示
        display_upload_prompt("data")
        
        # 数据分析示例
        display_examples("data")

if __name__ == "__main__":
    main()
