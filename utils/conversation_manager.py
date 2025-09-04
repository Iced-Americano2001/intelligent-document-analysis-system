"""
对话历史管理器
用于管理和存储对话历史记录
"""
import streamlit as st
import logging
from typing import Dict, Any, List
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class ConversationHistoryManager:
    """对话历史管理器"""
    
    def __init__(self):
        self.session_key_qa = "conversation_history_qa"
        self.session_key_data = "conversation_history_data"
        self.max_history_length = 100  # 最大历史记录数量
    
    def add_conversation(self, question: str, answer: str, conversation_type: str = "document_qa", 
                        metadata: Dict = None):
        """
        添加对话记录
        
        Args:
            question: 用户问题
            answer: 系统回答
            conversation_type: 对话类型 ('document_qa' 或 'data_analysis')
            metadata: 附加元数据
        """
        try:
            session_key = self.session_key_qa if conversation_type == "document_qa" else self.session_key_data
            
            # 初始化session state
            if session_key not in st.session_state:
                st.session_state[session_key] = []
            
            timestamp = datetime.now().isoformat()
            
            # 添加问题记录
            question_record = {
                "type": "question",
                "content": question,
                "timestamp": timestamp,
                "metadata": metadata or {}
            }
            
            # 添加回答记录
            answer_record = {
                "type": "answer", 
                "content": answer,
                "timestamp": timestamp,
                "metadata": metadata or {}
            }
            
            # 添加到历史记录
            st.session_state[session_key].extend([question_record, answer_record])
            
            # 限制历史记录长度
            if len(st.session_state[session_key]) > self.max_history_length:
                st.session_state[session_key] = st.session_state[session_key][-self.max_history_length:]
            
            logger.info(f"已添加{conversation_type}对话记录")
            
        except Exception as e:
            logger.error(f"添加对话记录失败: {e}", exc_info=True)
    
    def get_conversation_history(self, conversation_type: str = "document_qa") -> List[Dict]:
        """
        获取对话历史
        
        Args:
            conversation_type: 对话类型
            
        Returns:
            List of conversation records
        """
        session_key = self.session_key_qa if conversation_type == "document_qa" else self.session_key_data
        return st.session_state.get(session_key, [])
    
    def clear_conversation_history(self, conversation_type: str = "document_qa"):
        """清空对话历史"""
        session_key = self.session_key_qa if conversation_type == "document_qa" else self.session_key_data
        st.session_state[session_key] = []
        logger.info(f"已清空{conversation_type}对话历史")
    
    def export_conversation_history(self, conversation_type: str = "document_qa", 
                                  format_type: str = "json") -> Dict[str, Any]:
        """
        导出对话历史
        
        Args:
            conversation_type: 对话类型
            format_type: 导出格式
            
        Returns:
            Dict containing export result
        """
        try:
            history = self.get_conversation_history(conversation_type)
            
            if not history:
                return {
                    "success": False,
                    "error": "没有对话历史可导出"
                }
            
            # 准备导出数据
            export_data = {
                "export_info": {
                    "conversation_type": conversation_type,
                    "export_time": datetime.now().isoformat(),
                    "total_records": len(history),
                    "format": format_type
                },
                "conversations": history
            }
            
            if format_type == "json":
                return {
                    "success": True,
                    "data": export_data,
                    "format": "json"
                }
            else:
                return {
                    "success": False,
                    "error": f"不支持的导出格式: {format_type}"
                }
                
        except Exception as e:
            logger.error(f"导出对话历史失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"导出失败: {str(e)}"
            }
    
    def get_conversation_statistics(self, conversation_type: str = "document_qa") -> Dict[str, Any]:
        """获取对话统计信息"""
        try:
            history = self.get_conversation_history(conversation_type)
            
            if not history:
                return {
                    "total_conversations": 0,
                    "total_questions": 0,
                    "total_answers": 0,
                    "avg_question_length": 0,
                    "avg_answer_length": 0,
                    "first_conversation": None,
                    "last_conversation": None
                }
            
            questions = [conv for conv in history if conv.get("type") == "question"]
            answers = [conv for conv in history if conv.get("type") == "answer"]
            
            # 计算平均长度
            avg_question_length = 0
            avg_answer_length = 0
            
            if questions:
                total_question_length = sum(len(q.get("content", "")) for q in questions)
                avg_question_length = total_question_length / len(questions)
            
            if answers:
                total_answer_length = sum(len(a.get("content", "")) for a in answers)
                avg_answer_length = total_answer_length / len(answers)
            
            # 获取时间范围
            timestamps = [conv.get("timestamp") for conv in history if conv.get("timestamp")]
            first_conversation = min(timestamps) if timestamps else None
            last_conversation = max(timestamps) if timestamps else None
            
            return {
                "total_conversations": len(history) // 2,  # 问答对数量
                "total_questions": len(questions),
                "total_answers": len(answers),
                "avg_question_length": round(avg_question_length, 2),
                "avg_answer_length": round(avg_answer_length, 2),
                "first_conversation": first_conversation,
                "last_conversation": last_conversation
            }
            
        except Exception as e:
            logger.error(f"获取对话统计失败: {e}", exc_info=True)
            return {}
    
    def search_conversations(self, keyword: str, conversation_type: str = "document_qa") -> List[Dict]:
        """
        搜索对话记录
        
        Args:
            keyword: 搜索关键词
            conversation_type: 对话类型
            
        Returns:
            List of matching conversation records
        """
        try:
            history = self.get_conversation_history(conversation_type)
            matching_conversations = []
            
            for conv in history:
                content = conv.get("content", "").lower()
                if keyword.lower() in content:
                    matching_conversations.append(conv)
            
            return matching_conversations
            
        except Exception as e:
            logger.error(f"搜索对话记录失败: {e}", exc_info=True)
            return []
    
    def get_recent_conversations(self, limit: int = 10, 
                               conversation_type: str = "document_qa") -> List[Dict]:
        """获取最近的对话记录"""
        history = self.get_conversation_history(conversation_type)
        return history[-limit:] if history else []
    
    def backup_conversation_history(self, conversation_type: str = "document_qa", 
                                  backup_dir: str = None) -> Dict[str, Any]:
        """
        备份对话历史到文件
        
        Args:
            conversation_type: 对话类型
            backup_dir: 备份目录
            
        Returns:
            Dict containing backup result
        """
        try:
            history = self.get_conversation_history(conversation_type)
            
            if not history:
                return {
                    "success": False,
                    "error": "没有对话历史可备份"
                }
            
            # 设置备份目录
            if not backup_dir:
                backup_dir = Path("outputs/backups")
            else:
                backup_dir = Path(backup_dir)
            
            backup_dir.mkdir(parents=True, exist_ok=True)
            
            # 生成备份文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_filename = f"conversation_backup_{conversation_type}_{timestamp}.json"
            backup_path = backup_dir / backup_filename
            
            # 准备备份数据
            backup_data = {
                "backup_info": {
                    "conversation_type": conversation_type,
                    "backup_time": datetime.now().isoformat(),
                    "total_records": len(history)
                },
                "conversations": history
            }
            
            # 写入文件
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(backup_data, f, ensure_ascii=False, indent=2)
            
            return {
                "success": True,
                "backup_path": str(backup_path),
                "total_records": len(history),
                "file_size": backup_path.stat().st_size
            }
            
        except Exception as e:
            logger.error(f"备份对话历史失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"备份失败: {str(e)}"
            }
    
    def restore_conversation_history(self, backup_file_path: str, 
                                   conversation_type: str = "document_qa",
                                   merge: bool = False) -> Dict[str, Any]:
        """
        从备份文件恢复对话历史
        
        Args:
            backup_file_path: 备份文件路径
            conversation_type: 对话类型
            merge: 是否与现有历史合并
            
        Returns:
            Dict containing restore result
        """
        try:
            backup_path = Path(backup_file_path)
            
            if not backup_path.exists():
                return {
                    "success": False,
                    "error": "备份文件不存在"
                }
            
            # 读取备份文件
            with open(backup_path, "r", encoding="utf-8") as f:
                backup_data = json.load(f)
            
            conversations = backup_data.get("conversations", [])
            
            if not conversations:
                return {
                    "success": False,
                    "error": "备份文件中没有对话记录"
                }
            
            session_key = self.session_key_qa if conversation_type == "document_qa" else self.session_key_data
            
            if merge:
                # 与现有历史合并
                existing_history = st.session_state.get(session_key, [])
                st.session_state[session_key] = existing_history + conversations
            else:
                # 完全替换
                st.session_state[session_key] = conversations
            
            # 限制历史记录长度
            if len(st.session_state[session_key]) > self.max_history_length:
                st.session_state[session_key] = st.session_state[session_key][-self.max_history_length:]
            
            return {
                "success": True,
                "restored_records": len(conversations),
                "total_records": len(st.session_state[session_key])
            }
            
        except Exception as e:
            logger.error(f"恢复对话历史失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"恢复失败: {str(e)}"
            }

# 创建全局实例
conversation_manager = ConversationHistoryManager()
