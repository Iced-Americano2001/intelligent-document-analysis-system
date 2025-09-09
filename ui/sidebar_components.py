"""
侧边栏组件模块
"""
import streamlit as st

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

def render_advanced_options(mode="qa"):
    """渲染高级选项"""
    with st.expander("🔧 高级选项"):
        options = {}
        
        if mode == "qa":
            col1, col2 = st.columns(2)
            with col1:
                options["answer_style"] = st.selectbox(
                    "回答风格",
                    ["detailed", "concise", "bullet_points"],
                    format_func=lambda x: {
                        "detailed": "📝 详细解释",
                        "concise": "💡 简洁明了", 
                        "bullet_points": "📋 要点列表"
                    }[x]
                )
            with col2:
                options["include_quotes"] = st.checkbox("📖 包含原文引用", value=True)
                options["confidence_threshold"] = st.slider("置信度阈值", 0.3, 1.0, 0.7, 0.1)
            
            # 高级置信度评估开关（默认关闭以提升速度）
            options["enable_advanced_confidence"] = st.checkbox(
                "⚙️ 启用高级置信度评估（较慢）", 
                value=False, 
                help="开启后将调用额外一次模型对答案进行置信度打分，可能显著增加响应时间"
            )
        
        # RAG 相关参数
        st.markdown("**RAG设置**")
        # 第一行：两个开关
        col3, col4 = st.columns(2)
        with col3:
            options["use_rag"] = st.checkbox("启用RAG", value=True, key="data_use_rag")
        with col4:
            options["use_reranker"] = st.checkbox("启用重排", value=True, key="data_use_reranker")

        # 第二行：两个滑块
        col5, col6 = st.columns(2)
        with col5:
            options["rag_top_k"] = st.slider("RAG TopK", 4, 20, 8, key="data_rag_top_k")
        with col6:
            options["rag_rerank_top_n"] = st.slider("重排后片段数", 2, 10, 4, key="data_rag_rerank_n")

        st.markdown("**MCP 智能体设置**")
        col3, col4 = st.columns(2)
        with col3:
            options["max_iterations"] = st.number_input("最大思考轮数", min_value=3, max_value=20, value=10)
        with col4:
            options["show_thinking"] = st.checkbox("显示思考过程", value=True)
        
        return options



def render_data_analysis_options():
    """渲染数据分析特定选项"""
    options = {}

    # 第一行：两个滑块
    col1, col2 = st.columns(2)
    with col1:
        options["max_iterations"] = st.slider("最大思考轮数", 5, 20, 10, key="data_max_iter")
    with col2:
        options["confidence_threshold"] = st.slider("置信度阈值", 0.1, 1.0, 0.7, key="data_confidence")

    # 第二行：一个独立的开关
    options["show_thinking"] = st.checkbox("显示思考过程", value=True, key="data_show_thinking")
 
    # RAG 相关参数
    st.markdown("**RAG设置**")
    # 第一行：两个开关
    col3, col4 = st.columns(2)
    with col3:
        options["use_rag"] = st.checkbox("启用RAG", value=True, key="data_use_rag")
    with col4:
        options["use_reranker"] = st.checkbox("启用重排", value=True, key="data_use_reranker")

    # 第二行：两个滑块
    col5, col6 = st.columns(2)
    with col5:
        options["rag_top_k"] = st.slider("RAG TopK", 4, 20, 8, key="data_rag_top_k")
    with col6:
        options["rag_rerank_top_n"] = st.slider("重排后片段数", 2, 10, 4, key="data_rag_rerank_n")
    
    return options