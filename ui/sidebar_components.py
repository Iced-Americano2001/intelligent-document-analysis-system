"""
侧边栏组件模块
"""
import streamlit as st

def render_sidebar():
    """渲染侧边栏"""
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
    
    return agent_type

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
        
        # 共通的RAG参数
        options["use_rag"] = st.checkbox("启用RAG", value=True)
        col3, col4, col5 = st.columns(3)
        with col3:
            options["rag_top_k"] = st.slider("向量召回TopK", 4, 30, 12, 1)
        with col4:
            options["use_reranker"] = st.checkbox("启用重排", value=True)
        with col5:
            options["rag_rerank_top_n"] = st.slider("重排后片段数", 2, 12, 6, 1)
        
        return options

def render_mcp_options():
    """渲染MCP特定选项"""
    st.markdown("**MCP高级设置**")
    options = {}
    
    col6, col7 = st.columns(2)
    with col6:
        options["max_iterations"] = st.number_input("最大思考轮数", min_value=3, max_value=20, value=10)
    with col7:
        options["show_thinking"] = st.checkbox("显示思考过程", value=True)
    
    return options

def render_data_analysis_options():
    """渲染数据分析特定选项"""
    options = {}
    
    col1, col2, col3 = st.columns(3)
    with col1:
        options["max_iterations"] = st.slider("最大思考轮数", 5, 20, 10, key="data_max_iter")
    with col2:
        options["show_thinking"] = st.checkbox("显示思考过程", value=True, key="data_show_thinking")
    with col3:
        options["confidence_threshold"] = st.slider("置信度阈值", 0.1, 1.0, 0.7, key="data_confidence")
    
    # RAG 相关参数
    st.markdown("**RAG设置**")
    col4, col5, col6 = st.columns(3)
    with col4:
        options["use_rag"] = st.checkbox("启用RAG", value=True, key="data_use_rag")
    with col5:
        options["use_reranker"] = st.checkbox("启用重排", value=True, key="data_use_reranker")
    with col6:
        options["rag_top_k"] = st.slider("RAG TopK", 4, 20, 8, key="data_rag_top_k")
    
    options["rag_rerank_top_n"] = st.slider("重排后片段数", 2, 10, 4, key="data_rag_rerank_n")
    
    return options
