"""
对话状态管理器
管理UI状态、进度显示和用户反馈
"""

import streamlit as st
import time
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum

from mcp_services.models import ThoughtType, ConversationContext


class ConversationState(str, Enum):
    """对话状态枚举"""
    IDLE = "idle"
    THINKING = "thinking"
    TOOL_CALLING = "tool_calling"
    GENERATING = "generating"
    COMPLETED = "completed"
    ERROR = "error"


class ConversationStatusManager:
    """对话状态管理器"""
    
    def __init__(self):
        self.current_state = ConversationState.IDLE
        self.start_time: Optional[datetime] = None
        self.current_step = 0
        self.total_steps = 0
        self.status_messages: List[Dict[str, Any]] = []
        
        # UI容器
        self.status_container = st.empty()
        self.progress_container = st.empty()
        self.time_container = st.empty()
    
    def start_conversation(self, total_steps: int = 10):
        """开始对话"""
        self.current_state = ConversationState.THINKING
        self.start_time = datetime.now()
        self.total_steps = total_steps
        self.current_step = 0
        self.status_messages.clear()
        
        self._update_display()
    
    def update_step(self, step_type: ThoughtType, message: str, details: Optional[Dict] = None):
        """更新当前步骤"""
        self.current_step += 1
        
        # 更新状态
        if step_type == ThoughtType.THINKING:
            self.current_state = ConversationState.THINKING
        elif step_type == ThoughtType.TOOL_CALL:
            self.current_state = ConversationState.TOOL_CALLING
        elif step_type == ThoughtType.FINAL_ANSWER:
            self.current_state = ConversationState.GENERATING
        elif step_type == ThoughtType.ERROR:
            self.current_state = ConversationState.ERROR
        
        # 添加状态消息
        self.status_messages.append({
            "step": self.current_step,
            "type": step_type,
            "message": message,
            "details": details or {},
            "timestamp": datetime.now()
        })
        
        self._update_display()
    
    def complete_conversation(self, success: bool = True):
        """完成对话"""
        self.current_state = ConversationState.COMPLETED if success else ConversationState.ERROR
        self._update_display()
    
    def _update_display(self):
        """更新UI显示"""
        self._update_status_display()
        self._update_progress_display()
        self._update_time_display()
    
    def _update_status_display(self):
        """更新状态显示"""
        with self.status_container:
            status_icon, status_text, status_color = self._get_status_info()
            
            st.markdown(f"""
            <div style="
                padding: 10px; 
                border-radius: 5px; 
                border-left: 4px solid {status_color};
                background-color: {'#f0f8f0' if status_color == '#28a745' else 
                                  '#fff3cd' if status_color == '#ffc107' else 
                                  '#f8d7da' if status_color == '#dc3545' else '#d4edda'};
                margin: 5px 0;
            ">
                <strong>{status_icon} {status_text}</strong>
            </div>
            """, unsafe_allow_html=True)
    
    def _update_progress_display(self):
        """更新进度显示"""
        if self.total_steps > 0:
            with self.progress_container:
                progress = min(self.current_step / self.total_steps, 1.0)
                st.progress(
                    progress, 
                    text=f"进度: {self.current_step}/{self.total_steps} 步"
                )
    
    def _update_time_display(self):
        """更新时间显示"""
        if self.start_time:
            with self.time_container:
                elapsed = datetime.now() - self.start_time
                elapsed_str = self._format_duration(elapsed)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.caption(f"⏱️ 耗时: {elapsed_str}")
                
                with col2:
                    if self.current_state == ConversationState.COMPLETED:
                        st.caption("✅ 已完成")
                    elif self.current_state == ConversationState.ERROR:
                        st.caption("❌ 出现错误")
                    else:
                        st.caption("🔄 处理中...")
    
    def _get_status_info(self) -> tuple[str, str, str]:
        """获取状态信息"""
        if self.current_state == ConversationState.IDLE:
            return "⚪", "等待中", "#6c757d"
        elif self.current_state == ConversationState.THINKING:
            return "🤔", "AI正在思考...", "#007bff"
        elif self.current_state == ConversationState.TOOL_CALLING:
            return "🔧", "正在调用工具...", "#ffc107"
        elif self.current_state == ConversationState.GENERATING:
            return "✍️", "正在生成答案...", "#17a2b8"
        elif self.current_state == ConversationState.COMPLETED:
            return "✅", "处理完成", "#28a745"
        elif self.current_state == ConversationState.ERROR:
            return "❌", "处理出错", "#dc3545"
        else:
            return "❓", "未知状态", "#6c757d"
    
    def _format_duration(self, duration: timedelta) -> str:
        """格式化持续时间"""
        total_seconds = int(duration.total_seconds())
        
        if total_seconds < 60:
            return f"{total_seconds}秒"
        elif total_seconds < 3600:
            minutes = total_seconds // 60
            seconds = total_seconds % 60
            return f"{minutes}分{seconds}秒"
        else:
            hours = total_seconds // 3600
            minutes = (total_seconds % 3600) // 60
            return f"{hours}小时{minutes}分钟"
    
    def show_status_history(self):
        """显示状态历史"""
        if not self.status_messages:
            st.info("暂无状态历史")
            return
        
        st.markdown("#### 📋 执行历史")
        
        for msg in self.status_messages:
            timestamp = msg["timestamp"].strftime("%H:%M:%S")
            step = msg["step"]
            message = msg["message"]
            step_type = msg["type"]
            
            # 根据类型选择图标和颜色
            if step_type == ThoughtType.THINKING:
                icon = "🤔"
                color = "#007bff"
            elif step_type == ThoughtType.TOOL_CALL:
                icon = "🔧"
                color = "#ffc107"
            elif step_type == ThoughtType.TOOL_RESULT:
                icon = "📊"
                color = "#28a745"
            elif step_type == ThoughtType.FINAL_ANSWER:
                icon = "🎯"
                color = "#17a2b8"
            elif step_type == ThoughtType.ERROR:
                icon = "❌"
                color = "#dc3545"
            else:
                icon = "📝"
                color = "#6c757d"
            
            with st.expander(f"{icon} 步骤 {step}: {message} ({timestamp})", expanded=False):
                if msg["details"]:
                    st.json(msg["details"])
                else:
                    st.write("无详细信息")


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {
            "start_time": None,
            "end_time": None,
            "total_duration": 0,
            "step_durations": [],
            "tool_call_count": 0,
            "thinking_count": 0,
            "error_count": 0,
            "memory_usage": []
        }
        self.step_start_time: Optional[datetime] = None
    
    def start_monitoring(self):
        """开始监控"""
        self.metrics["start_time"] = datetime.now()
        self.step_start_time = datetime.now()
    
    def record_step(self, step_type: ThoughtType):
        """记录步骤"""
        if self.step_start_time:
            duration = (datetime.now() - self.step_start_time).total_seconds()
            self.metrics["step_durations"].append({
                "type": step_type,
                "duration": duration
            })
            self.step_start_time = datetime.now()
        
        # 统计步骤类型
        if step_type == ThoughtType.TOOL_CALL:
            self.metrics["tool_call_count"] += 1
        elif step_type == ThoughtType.THINKING:
            self.metrics["thinking_count"] += 1
        elif step_type == ThoughtType.ERROR:
            self.metrics["error_count"] += 1
    
    def end_monitoring(self):
        """结束监控"""
        self.metrics["end_time"] = datetime.now()
        if self.metrics["start_time"]:
            self.metrics["total_duration"] = (
                self.metrics["end_time"] - self.metrics["start_time"]
            ).total_seconds()
    
    def show_performance_report(self):
        """显示性能报告"""
        st.markdown("#### 📊 性能报告")
        
        if not self.metrics["start_time"]:
            st.info("暂无性能数据")
            return
        
        # 基础指标
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric(
                "总耗时", 
                f"{self.metrics['total_duration']:.2f}秒"
            )
        
        with col2:
            st.metric(
                "思考次数", 
                self.metrics["thinking_count"]
            )
        
        with col3:
            st.metric(
                "工具调用", 
                self.metrics["tool_call_count"]
            )
        
        with col4:
            st.metric(
                "错误次数", 
                self.metrics["error_count"],
                delta=None if self.metrics["error_count"] == 0 else "需要关注",
                delta_color="normal" if self.metrics["error_count"] == 0 else "inverse"
            )
        
        # 步骤耗时分布
        if self.metrics["step_durations"]:
            st.markdown("##### 步骤耗时分析")
            
            # 计算各类型步骤的平均耗时
            step_stats = {}
            for step in self.metrics["step_durations"]:
                step_type = step["type"]
                duration = step["duration"]
                
                if step_type not in step_stats:
                    step_stats[step_type] = {"total": 0, "count": 0, "durations": []}
                
                step_stats[step_type]["total"] += duration
                step_stats[step_type]["count"] += 1
                step_stats[step_type]["durations"].append(duration)
            
            # 显示统计结果
            for step_type, stats in step_stats.items():
                avg_duration = stats["total"] / stats["count"]
                max_duration = max(stats["durations"])
                min_duration = min(stats["durations"])
                
                with st.expander(f"📈 {step_type} 步骤分析", expanded=False):
                    subcol1, subcol2, subcol3 = st.columns(3)
                    
                    with subcol1:
                        st.metric("平均耗时", f"{avg_duration:.2f}秒")
                    with subcol2:
                        st.metric("最大耗时", f"{max_duration:.2f}秒")
                    with subcol3:
                        st.metric("最小耗时", f"{min_duration:.2f}秒")