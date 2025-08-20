"""
流式UI交互组件
使用现代化的Streamlit API实现实时流式显示
"""

import streamlit as st
import time
import json
import traceback
from typing import AsyncIterator, Dict, Any, Optional, List
from datetime import datetime

from mcp_services.models import ThoughtProcess, ThoughtType
from utils.logger import ui_logger, log_exceptions


class StreamingChatInterface:
    """流式聊天界面组件"""
    
    def __init__(self, container_key: str = "main_chat"):
        self.container_key = container_key
        self.thinking_container = None
        self.tool_call_container = None
        self.answer_container = None
        self.status_container = None
        
        # 初始化容器
        self._initialize_containers()
    
    def _initialize_containers(self):
        """初始化UI容器"""
        # 创建主要的容器区域
        st.markdown("### 🤖 AI助手工作过程")
        
        # 状态显示区
        self.status_container = st.empty()
        
        # 思考过程区
        st.markdown("#### 💭 思考过程")
        self.thinking_container = st.container()
        
        # 工具调用区  
        st.markdown("#### 🔧 工具调用")
        self.tool_call_container = st.container()
        
        # 最终答案区
        st.markdown("#### 🎯 答案")
        self.answer_container = st.container()
    
    @log_exceptions(ui_logger)
    async def display_thought_stream(self, thought_stream: AsyncIterator[ThoughtProcess]) -> str:
        """显示思考过程流"""
        final_answer = ""
        thought_count = 0
        tool_calls = []
        
        ui_logger.info("开始显示思考过程流")
        
        try:
            async for thought in thought_stream:
                thought_count += 1
                ui_logger.debug(f"处理第 {thought_count} 个思考步骤", 
                               thought_type=thought.type, 
                               content_preview=thought.content[:100] if thought.content else "")
                
                # 验证thought对象
                if not isinstance(thought, ThoughtProcess):
                    ui_logger.error(f"无效的思考对象类型: {type(thought)}")
                    continue
                
                # 更新状态
                self._update_status(f"处理中... (步骤 {thought_count})")
                
                # 安全处理思考类型
                thought_type = thought.type
                if hasattr(thought_type, 'value'):
                    thought_type_str = thought_type.value
                elif isinstance(thought_type, str):
                    thought_type_str = thought_type
                else:
                    thought_type_str = str(thought_type)
                
                ui_logger.debug(f"处理思考类型: {thought_type_str}")
                
                if thought_type_str == "thinking" or thought_type == ThoughtType.THINKING:
                    self._display_thinking_step(thought, thought_count)
                
                elif thought_type_str == "tool_call" or thought_type == ThoughtType.TOOL_CALL:
                    self._display_tool_call(thought)
                    tool_calls.append(thought)
                
                elif thought_type_str == "tool_result" or thought_type == ThoughtType.TOOL_RESULT:
                    self._display_tool_result(thought)
                
                elif thought_type_str == "final_answer" or thought_type == ThoughtType.FINAL_ANSWER:
                    final_answer = thought.content or ""
                    ui_logger.info(f"收到最终答案，长度: {len(final_answer)}")
                    await self._display_final_answer_stream(final_answer)
                
                elif thought_type_str == "error" or thought_type == ThoughtType.ERROR:
                    ui_logger.warning(f"处理思考错误: {thought.content}")
                    self._display_error(thought)
                
                else:
                    ui_logger.warning(f"未知的思考类型: {thought_type_str}")
                
                # 小延迟以便用户看到过程
                time.sleep(0.1)
            
            # 更新最终状态
            self._update_status("✅ 处理完成")
            ui_logger.info(f"思考流处理完成，共 {thought_count} 个步骤，最终答案长度: {len(final_answer)}")
            
        except Exception as e:
            error_msg = f"流式处理出错: {str(e)}"
            ui_logger.error(error_msg, error=e)
            ui_logger.error(f"错误堆栈: {traceback.format_exc()}")
            self._display_error_message(error_msg)
        
        return final_answer
    
    def _display_thinking_step(self, thought: ThoughtProcess, step: int):
        """显示思考步骤"""
        with self.thinking_container:
            with st.expander(f"🤔 思考步骤 {step}", expanded=True):
                st.write(thought.content)
                
                # 显示置信度
                if thought.confidence:
                    st.progress(
                        thought.confidence,
                        text=f"思考置信度: {thought.confidence:.1%}"
                    )
                
                # 显示时间戳
                timestamp = datetime.now().strftime("%H:%M:%S")
                st.caption(f"时间: {timestamp}")
    
    def _display_tool_call(self, thought: ThoughtProcess):
        """显示工具调用"""
        with self.tool_call_container:
            with st.expander(f"🔧 调用工具: {thought.tool_name}", expanded=False):
                st.info(f"**工具**: {thought.tool_name}")
                
                if thought.parameters:
                    st.markdown("**参数**:")
                    st.json(thought.parameters)
                
                # 显示调用状态
                st.spinner("工具执行中...")
    
    def _display_tool_result(self, thought: ThoughtProcess):
        """显示工具执行结果"""
        with self.tool_call_container:
            # 找到对应的工具调用展开区，更新其内容
            if thought.tool_name and thought.result:
                success = thought.result.get("success", True)
                
                if success:
                    st.success("✅ 工具执行成功")
                    
                    # 显示执行结果
                    if "error" not in thought.result:
                        with st.expander("📊 执行结果", expanded=False):
                            # 格式化显示结果
                            formatted_result = self._format_tool_result(thought.result)
                            st.write(formatted_result)
                else:
                    st.error(f"❌ 工具执行失败: {thought.result.get('error', '未知错误')}")
    
    def _format_tool_result(self, result: Dict[str, Any]) -> str:
        """格式化工具执行结果"""
        if not result:
            return "无结果"
        
        # 移除系统字段，只显示用户关心的内容
        display_result = {k: v for k, v in result.items() 
                         if k not in ['success', 'tool_name', 'timestamp']}
        
        if not display_result:
            return "执行成功"
        
        # 格式化为易读的文本
        formatted_lines = []
        for key, value in display_result.items():
            if isinstance(value, (dict, list)):
                formatted_lines.append(f"**{key}**:")
                formatted_lines.append(f"```json\n{json.dumps(value, ensure_ascii=False, indent=2)}\n```")
            else:
                formatted_lines.append(f"**{key}**: {value}")
        
        return "\n\n".join(formatted_lines)
    
    async def _display_final_answer_stream(self, answer: str):
        """流式显示最终答案"""
        with self.answer_container:
            # 创建一个占位符用于流式显示
            answer_placeholder = st.empty()
            
            # 模拟流式输出
            words = answer.split()
            displayed_text = ""
            
            for i, word in enumerate(words):
                displayed_text += word + " "
                
                # 每隔几个词更新一次显示
                if i % 3 == 0 or i == len(words) - 1:
                    answer_placeholder.markdown(displayed_text)
                    time.sleep(0.05)  # 控制流式速度
            
            # 最终完整显示
            answer_placeholder.markdown(answer)
    
    def _display_error(self, thought: ThoughtProcess):
        """显示错误信息"""
        with st.container():
            st.error(f"❌ 执行错误: {thought.content}")
    
    def _display_error_message(self, message: str):
        """显示错误消息"""
        with st.container():
            st.error(f"❌ {message}")
    
    def _update_status(self, status: str):
        """更新状态显示"""
        if self.status_container:
            with self.status_container:
                st.info(f"📊 状态: {status}")


class ThoughtProcessDisplay:
    """思考过程展示组件"""
    
    def __init__(self):
        self.thoughts: List[ThoughtProcess] = []
        self.current_step = 0
    
    def add_thought(self, thought: ThoughtProcess):
        """添加思考过程"""
        self.thoughts.append(thought)
        self.current_step += 1
    
    def display_summary(self):
        """显示思考过程摘要"""
        if not self.thoughts:
            st.info("暂无思考过程")
            return
        
        st.markdown("### 📋 思考过程摘要")
        
        # 统计信息
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "总步骤数", 
                len(self.thoughts)
            )
        
        with col2:
            thinking_count = sum(1 for t in self.thoughts if t.type == ThoughtType.THINKING)
            st.metric("思考次数", thinking_count)
        
        with col3:
            tool_calls = sum(1 for t in self.thoughts if t.type == ThoughtType.TOOL_CALL)
            st.metric("工具调用", tool_calls)
        
        with col4:
            errors = sum(1 for t in self.thoughts if t.type == ThoughtType.ERROR)
            st.metric("错误次数", errors)
        
        # 详细过程
        st.markdown("#### 详细过程")
        
        for i, thought in enumerate(self.thoughts, 1):
            self._display_thought_item(i, thought)
    
    def _display_thought_item(self, step: int, thought: ThoughtProcess):
        """显示单个思考项"""
        if thought.type == ThoughtType.THINKING:
            icon = "🤔"
            title = f"思考 {step}"
            color = "blue"
        elif thought.type == ThoughtType.TOOL_CALL:
            icon = "🔧"
            title = f"工具调用 {step}: {thought.tool_name}"
            color = "orange"
        elif thought.type == ThoughtType.TOOL_RESULT:
            icon = "📊"
            title = f"工具结果 {step}"
            color = "green"
        elif thought.type == ThoughtType.FINAL_ANSWER:
            icon = "🎯"
            title = f"最终答案 {step}"
            color = "success"
        elif thought.type == ThoughtType.ERROR:
            icon = "❌"
            title = f"错误 {step}"
            color = "red"
        else:
            icon = "📝"
            title = f"步骤 {step}"
            color = "gray"
        
        with st.expander(f"{icon} {title}", expanded=False):
            st.markdown(thought.content)
            
            if thought.parameters:
                st.markdown("**参数**:")
                st.json(thought.parameters)
            
            if thought.result:
                st.markdown("**结果**:")
                st.json(thought.result)
            
            if thought.confidence:
                st.progress(thought.confidence, text=f"置信度: {thought.confidence:.1%}")


class ProgressTracker:
    """进度追踪组件"""
    
    def __init__(self, total_steps: int = 100):
        self.total_steps = total_steps
        self.current_step = 0
        self.progress_bar = st.progress(0)
        self.status_text = st.empty()
    
    def update(self, step: int, message: str = ""):
        """更新进度"""
        self.current_step = min(step, self.total_steps)
        progress = self.current_step / self.total_steps
        
        self.progress_bar.progress(progress)
        
        if message:
            self.status_text.text(f"进度: {self.current_step}/{self.total_steps} - {message}")
        else:
            self.status_text.text(f"进度: {self.current_step}/{self.total_steps}")
    
    def complete(self, message: str = "完成"):
        """标记完成"""
        self.progress_bar.progress(1.0)
        self.status_text.success(f"✅ {message}")


class InteractiveElements:
    """交互式元素组件"""
    
    @staticmethod
    def show_json_viewer(data: Dict[str, Any], title: str = "数据查看器"):
        """JSON数据查看器"""
        with st.expander(f"📋 {title}", expanded=False):
            st.json(data)
    
    @staticmethod
    def show_code_block(code: str, language: str = "python", title: str = "代码"):
        """代码块显示"""
        st.markdown(f"**{title}**")
        st.code(code, language=language)
    
    @staticmethod
    def show_metrics_grid(metrics: Dict[str, Any], columns: int = 4):
        """指标网格显示"""
        cols = st.columns(columns)
        
        for i, (key, value) in enumerate(metrics.items()):
            with cols[i % columns]:
                if isinstance(value, (int, float)):
                    st.metric(key, value)
                else:
                    st.metric(key, str(value))
    
    @staticmethod
    def show_warning_box(message: str, title: str = "注意"):
        """警告框"""
        st.warning(f"⚠️ **{title}**: {message}")
    
    @staticmethod
    def show_info_box(message: str, title: str = "信息"):
        """信息框"""
        st.info(f"ℹ️ **{title}**: {message}")
    
    @staticmethod
    def show_success_box(message: str, title: str = "成功"):
        """成功框"""
        st.success(f"✅ **{title}**: {message}")
    
    @staticmethod
    def show_error_box(message: str, title: str = "错误"):
        """错误框"""
        st.error(f"❌ **{title}**: {message}")