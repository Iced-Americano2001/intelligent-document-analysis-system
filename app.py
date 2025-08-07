import streamlit as st
import asyncio
from pathlib import Path
from typing import Dict, Any
import logging

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
    from utils.llm_utils import llm_manager
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
        qa_agent = QAAgent()
        agent_coordinator.register_agent(qa_agent)
        
        logger.info("文档解析服务和智能体初始化完成")
        return True
    except Exception as e:
        logger.error(f"服务初始化失败: {e}")
        import traceback
        traceback.print_exc()
        return False

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

async def process_document_qa(uploaded_file, question, answer_style="detailed", include_quotes=True, confidence_threshold=0.7):
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
            
            progress_bar.progress(75, text="🤖 AI正在思考答案...")
            
            # 执行问答
            qa_input = {
                "document_content": text_content,
                "question": question,
                "document_type": Path(uploaded_file.name).suffix,
                "answer_style": answer_style,
                "include_quotes": include_quotes,
                "confidence_threshold": confidence_threshold
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

def main():
    st.title("🤖 智能文档问答系统")
    st.write("上传文档后，您可以用自然语言提问，AI助手将基于文档内容为您提供准确答案。")
    
    # 侧边栏
    st.sidebar.title("设置")
    st.sidebar.markdown("---")
    st.sidebar.write("当前版本: v2.0.0 (简化版)")
    
    # 初始化服务
    if not initialize_services():
        st.error("系统初始化失败，请检查配置")
        st.stop()
    
    # 主界面
    st.markdown("### 📁 文档上传")
    
    # 获取支持的文件格式
    file_config = get_config("file")
    supported_formats = [fmt.lstrip('.') for fmt in file_config.get("supported_formats", ["pdf", "txt", "docx"])]
    
    uploaded_file = st.file_uploader(
        "选择需要问答的文档",
        type=supported_formats,
        help="支持PDF、Word、文本等格式"
    )
    
    if uploaded_file is not None:
        # 文件信息
        st.success(f"✅ 文档已加载: **{uploaded_file.name}**")
        
        col1, col2 = st.columns(2)
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
        
        # 问答按钮
        if st.button("🔍 开始问答", type="primary", use_container_width=True):
            if not question:
                st.error("请输入问题内容！")
                return
                
            with st.spinner("🔄 AI正在分析文档并准备答案..."):
                run_async_in_streamlit(
                    process_document_qa(uploaded_file, question, answer_style, include_quotes, confidence_threshold)
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

if __name__ == "__main__":
    main()
