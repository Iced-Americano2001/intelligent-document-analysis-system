"""
异步操作工具模块
"""
import asyncio
import logging
import streamlit as st
import concurrent.futures

logger = logging.getLogger(__name__)

def run_async_in_streamlit(coro):
    """在Streamlit环境中安全运行异步代码"""
    try:
        # 方法1: 直接运行（如果没有运行中的事件循环）
        return asyncio.run(coro)
    except RuntimeError as e:
        if "cannot be called from a running event loop" in str(e):
            # 方法2: 在新线程中运行
            try:
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
