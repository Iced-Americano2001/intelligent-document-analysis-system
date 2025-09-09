"""
增强日志系统
提供详细的错误跟踪、性能监控和调试信息
"""

import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional
import functools
from loguru import logger
import streamlit as st

# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

# 移除默认的loguru处理器
logger.remove()

# 配置loguru日志系统
logger.add(
    sys.stdout,
    format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
    level="DEBUG",
    colorize=True
)

# 文件日志
logger.add(
    log_dir / "app_{time}.log",
    rotation="1 day",
    retention="7 days",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}",
    level="DEBUG"
)

# 错误日志专用文件
logger.add(
    log_dir / "errors_{time}.log",
    rotation="1 day", 
    retention="30 days",
    format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level: <8} | {name}:{function}:{line} - {message}\n{extra}",
    level="ERROR"
)


class MCPLogger:
    """MCP系统专用日志记录器"""
    
    def __init__(self, name: str = "MCP"):
        self.logger = logger.bind(name=name)
        self.context = {}
    
    def set_context(self, **kwargs):
        """设置日志上下文信息"""
        self.context.update(kwargs)
        self.logger = self.logger.bind(**self.context)
    
    def info(self, message: str, **kwargs):
        """信息日志"""
        self.logger.info(message, **kwargs)
        self._show_in_streamlit("info", message)
    
    def debug(self, message: str, **kwargs):
        """调试日志"""
        self.logger.debug(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """警告日志"""
        self.logger.warning(message, **kwargs)
        self._show_in_streamlit("warning", message)
    
    def error(self, message: str, error: Exception = None, **kwargs):
        """错误日志"""
        if error:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            tb_str = "".join(tb)
            self.logger.error(f"{message}\n错误详情: {str(error)}\n堆栈跟踪:\n{tb_str}", **kwargs)
            self._show_in_streamlit("error", f"{message}: {str(error)}")
        else:
            self.logger.error(message, **kwargs)
            self._show_in_streamlit("error", message)
    
    def critical(self, message: str, error: Exception = None, **kwargs):
        """严重错误日志"""
        if error:
            tb = traceback.format_exception(type(error), error, error.__traceback__)
            tb_str = "".join(tb)
            self.logger.critical(f"{message}\n错误详情: {str(error)}\n堆栈跟踪:\n{tb_str}", **kwargs)
        else:
            self.logger.critical(message, **kwargs)
        self._show_in_streamlit("error", f"严重错误: {message}")
    
    def log_function_call(self, func_name: str, args: tuple = None, kwargs: dict = None):
        """记录函数调用"""
        args_str = str(args) if args else "()"
        kwargs_str = str(kwargs) if kwargs else "{}"
        self.debug(f"调用函数: {func_name} | args={args_str} | kwargs={kwargs_str}")
    
    def log_performance(self, operation: str, duration: float, **details):
        """记录性能指标"""
        self.info(f"性能监控: {operation} 耗时 {duration:.3f}s", **details)
    
    def log_mcp_event(self, event_type: str, details: Dict[str, Any]):
        """记录MCP特定事件"""
        self.info(f"MCP事件: {event_type}", **details)
    
    def _show_in_streamlit(self, level: str, message: str):
        """在Streamlit界面显示重要日志"""
        try:
            # 只在有Streamlit上下文时显示
            if hasattr(st, 'get_option') and st.get_option('global.developmentMode'):
                return
            
            # 在侧边栏显示最新日志
            with st.sidebar:
                if level == "error":
                    st.error(f"🔴 {message}")
                elif level == "warning":
                    st.warning(f"🟡 {message}")
                elif level == "info":
                    st.info(f"🔵 {message}")
        except:
            # 忽略Streamlit相关错误，避免影响核心功能
            pass


def log_exceptions(logger_instance: MCPLogger = None):
    """异常日志装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger_instance or mcp_logger
            _logger.log_function_call(func.__name__, args, kwargs)
            
            try:
                start_time = datetime.now()
                result = func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                _logger.log_performance(func.__name__, duration)
                return result
                
            except Exception as e:
                _logger.error(f"函数 {func.__name__} 执行失败", error=e)
                raise
        
        return wrapper
    return decorator


def log_async_exceptions(logger_instance: MCPLogger = None):
    """异步函数异常日志装饰器"""
    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            _logger = logger_instance or mcp_logger
            _logger.log_function_call(func.__name__, args, kwargs)
            
            try:
                start_time = datetime.now()
                result = await func(*args, **kwargs)
                duration = (datetime.now() - start_time).total_seconds()
                _logger.log_performance(func.__name__, duration)
                return result
                
            except Exception as e:
                _logger.error(f"异步函数 {func.__name__} 执行失败", error=e)
                raise
        
        return wrapper
    return decorator


def log_async_generator(logger_instance: MCPLogger = None):
    """异步生成器日志装饰器"""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            _logger = logger_instance or mcp_logger
            _logger.log_function_call(func.__name__, args, kwargs)
            
            try:
                start_time = datetime.now()
                # 调用原函数获取异步生成器
                async_gen = func(*args, **kwargs)
                _logger.debug(f"异步生成器 {func.__name__} 创建成功")
                
                # 包装异步生成器以添加日志记录
                async def logged_generator():
                    try:
                        count = 0
                        async for item in async_gen:
                            count += 1
                            _logger.debug(f"异步生成器 {func.__name__} 产出第 {count} 个项目")
                            yield item
                        
                        duration = (datetime.now() - start_time).total_seconds()
                        _logger.log_performance(f"{func.__name__}_generator", duration)
                        _logger.info(f"异步生成器 {func.__name__} 完成，共产出 {count} 个项目")
                        
                    except Exception as e:
                        _logger.error(f"异步生成器 {func.__name__} 执行失败", error=e)
                        raise
                
                return logged_generator()
                
            except Exception as e:
                _logger.error(f"异步生成器函数 {func.__name__} 创建失败", error=e)
                raise
        
        return wrapper
    return decorator


# 全局日志实例
mcp_logger = MCPLogger("MCP")
ui_logger = MCPLogger("UI")
agent_logger = MCPLogger("Agent")
tool_logger = MCPLogger("Tool")


def get_logger(name: str) -> MCPLogger:
    """获取指定名称的日志记录器"""
    return MCPLogger(name)


def setup_debug_logging():
    """设置调试模式日志"""
    logger.remove()
    logger.add(
        sys.stdout,
        format="<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>{message}</level>",
        level="DEBUG",
        colorize=True
    )


# def log_system_info():
#     """记录系统信息"""
#     import platform
#     import psutil
    
#     mcp_logger.info(f"系统信息: {platform.system()} {platform.release()}")
#     mcp_logger.info(f"Python版本: {sys.version}")
#     mcp_logger.info(f"内存使用: {psutil.virtual_memory().percent}%")
#     mcp_logger.info(f"CPU使用: {psutil.cpu_percent()}%")


# # 启动时记录系统信息
# try:
#     log_system_info()
# except ImportError:
#     mcp_logger.warning("psutil未安装，无法获取系统性能信息")