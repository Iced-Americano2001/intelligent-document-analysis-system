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
    render_sidebar()
    
    # 初始化服务
    if not initialize_services():
        st.error("系统初始化失败，请检查配置")
        st.stop()

    # 如果选择MCP智能体，初始化MCP服务
    mcp_agent = initialize_mcp_agent()
    if mcp_agent is None:
        st.warning("MCP智能体初始化失败")

    # Tab切换
    if st.session_state.app_mode == "📄 智能文档问答":
        render_document_qa_tab(mcp_agent)
    elif st.session_state.app_mode == "📊 智能数据分析":
        render_data_analysis_tab(mcp_agent)
    elif st.session_state.app_mode == "📋 对话报告":
        render_conversation_report_tab()



def render_sidebar():
    """
    渲染应用的侧边栏，作为主导航。
    """
    with st.sidebar:
        st.markdown("")
        st.markdown("")
        st.markdown("")
        # 1. 模式选择
        st.header("⚙️ 模式选择")
        app_mode = st.radio(
            "选择任务类型",
            ("📄 智能文档问答", "📊 智能数据分析", "📋 对话报告"),
            key="app_mode",
        )
        st.markdown("---")

        # 2. 根据选择的模式，显示不同的功能说明
        if app_mode == "📄 智能文档问答":
            st.header("💡 功能")
            st.markdown("- 🤔 深度思考\n- 🔧 工具调用\n- 📊 过程透明\n- 🎯 智能决策")

        elif app_mode == "📊 智能数据分析":
            st.header("💡 功能")
            st.markdown("- 📈 综合分析\n- 📊 描述性统计\n- 🔗 相关性分析\n- 📉 趋势分析")
        
        elif app_mode == "📋 对话报告":
            st.header("💡 功能")
            st.markdown("- 💾 保存对话\n- 📄 生成报告\n- 📂 管理历史")

        # 3. 页脚信息
        st.markdown("---")
        st.info("当前版本: v3.0.0")



def render_conversation_report_tab():
    """渲染对话报告标签页"""
    try:
        from ui.report_components import render_conversation_report_section
        from utils.conversation_manager import conversation_manager
        
        st.header("对话报告管理")
        st.markdown("### 📋 生成和管理您的对话报告")
        
        # 选择报告类型
        report_type_tab = st.radio(
            "选择报告类型",
            ["文档问答报告", "数据分析报告"],
            horizontal=True,
            key="report_type_selector"
        )
        
        conversation_type = "document_qa" if report_type_tab == "文档问答报告" else "data_analysis"
        
        # 渲染对应的报告部分
        render_conversation_report_section(conversation_type)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"渲染对话报告标签页失败: {e}", exc_info=True)
        st.error(f"❌ 对话报告功能加载失败: {str(e)}")

def render_document_qa_tab(mcp_agent):
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
        
        mcp_options = render_mcp_options()
        
        # 问答按钮
        button_text = "🧠 开始深度分析"
        if st.button(button_text, type="primary", use_container_width=True):
            if not question:
                st.error("请输入问题内容！")
                return
            
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
        # 上传提示
        display_upload_prompt("document")
        
        # 问答示例
        display_examples("qa")
        
        # 添加快速报告功能
        st.markdown("---")
        try:
            from ui.report_components import render_conversation_report_section
            render_conversation_report_section("document_qa")
        except Exception as e:
            st.info("💡 对话报告功能需要先进行文档问答对话")



def render_data_analysis_tab(mcp_agent):
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
                if mcp_agent is None:
                    st.error("❌ MCP智能体未初始化")
                else:
                    run_async_in_streamlit(
                        process_mcp_data_analysis(
                            data_uploader, analysis_requirements, mcp_agent, 
                            **data_options  # 使用字典展开，自动过滤不需要的参数
                        )
                    )

    
    else:
        # 上传提示
        display_upload_prompt("data")
        
        # 数据分析示例
        display_examples("data")
        
        # 添加快速报告功能
        st.markdown("---")
        try:
            from ui.report_components import render_conversation_report_section
            render_conversation_report_section("data_analysis")
        except Exception as e:
            st.info("💡 对话报告功能需要先进行数据分析对话")

if __name__ == "__main__":
    main()
