"""
结果显示模块
"""
import streamlit as st
import pandas as pd
from typing import Dict, Any

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

def display_file_info(uploaded_file):
    """显示文件信息"""
    from pathlib import Path
    
    st.success(f"✅ 文档已加载: **{uploaded_file.name}**")
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("文件大小", f"{uploaded_file.size:,} 字节")
    with col2:
        st.metric("文件类型", Path(uploaded_file.name).suffix.upper())
    with col3:
        # 这个需要从外部传入agent_type
        pass

def display_upload_prompt(content_type="document"):
    """显示上传提示界面"""
    if content_type == "document":
        st.markdown("""
        <div style="border: 2px dashed #ccc; border-radius: 10px; padding: 3rem; text-align: center; margin: 2rem 0;">
            <h3 style="color: #666;">🤖 智能问答助手</h3>
            <p style="color: #888;">上传文档后即可开始智能问答</p>
            <p style="font-size: 0.9rem; color: #aaa;">支持复杂问题和多轮对话</p>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown("""
        <div style="border: 2px dashed #ccc; border-radius: 10px; padding: 3rem; text-align: center; margin: 2rem 0;">
            <h3 style="color: #666;">📊 智能数据分析</h3>
            <p style="color: #888;">上传数据文件后即可开始智能数据分析</p>
            <p style="font-size: 0.9rem; color: #aaa;">支持复杂分析和多轮推理</p>
        </div>
        """, unsafe_allow_html=True)

def display_examples(example_type="qa"):
    """显示示例"""
    if example_type == "qa":
        st.markdown("#### 💡 问答示例")
        examples = [
            "这个文档的主要内容是什么？",
            "文档中提到了哪些重要数据？",
            "作者的主要观点和结论是什么？", 
            "有什么重要的建议或推荐？"
        ]
        
        for example in examples:
            st.info(f"**问题示例**: {example}")
    else:
        st.markdown("#### 💡 数据分析示例")
        examples = [
            "帮我分析销售额和广告投入的关系",
            "找出哪些产品的利润率最高",
            "分析数据中的趋势和异常值",
            "预测下个季度的销售增长",
        ]
        
        for example in examples:
            st.info(f"**分析示例**: {example}")

def display_agent_features(agent_type):
    """显示Agent特性"""
    if agent_type == "MCP智能助手":
        st.markdown("#### 🧠 MCP智能助手特性")
        st.info("""
        **MCP智能助手具备以下能力：**
        - 🤔 **深度思考**：多轮分析推理过程
        - 🔧 **工具调用**：自动使用文档分析、搜索等工具
        - 📊 **过程透明**：实时显示思考和执行过程
        - 🎯 **智能决策**：根据问题复杂度自动选择处理策略
        """)
