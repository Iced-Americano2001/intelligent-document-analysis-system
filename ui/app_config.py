"""
应用配置和页面设置模块
"""
import streamlit as st
import nest_asyncio
import asyncio
import logging

def setup_page_config():
    """设置Streamlit页面配置"""
    st.set_page_config(
        page_title="智能文档问答",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded"
    )

def setup_asyncio():
    """设置异步事件循环支持"""
    try:
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

def setup_logging():
    """设置日志配置"""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)

def setup_session_state():
    """初始化session state"""
    if 'active_tab' not in st.session_state:
        st.session_state.active_tab = "🤖 智能文档问答"
