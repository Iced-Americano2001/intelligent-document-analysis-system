"""
报告生成智能体
用于整合对话历史并生成报告
"""
import logging
from typing import Dict, Any, List
from datetime import datetime
import json
from pathlib import Path

logger = logging.getLogger(__name__)

class ReportAgent:
    """报告生成智能体"""
    
    def __init__(self):
        self.name = "Report_Agent"
        self.description = "智能报告生成助手，专门用于整合对话历史并生成结构化报告"
    
    async def generate_conversation_report(self, conversation_history: List[Dict], 
                                         analysis_type: str = "document_qa", 
                                         user_preferences: Dict = None) -> Dict[str, Any]:
        """
        生成对话报告
        
        Args:
            conversation_history: 对话历史列表
            analysis_type: 分析类型 ('document_qa' 或 'data_analysis')
            user_preferences: 用户偏好设置
            
        Returns:
            Dict containing the generated report
        """
        try:
            logger.info(f"开始生成{analysis_type}类型的对话报告")
            
            if not conversation_history:
                return {
                    "success": False,
                    "error": "对话历史为空，无法生成报告"
                }
            
            # 设置默认偏好
            preferences = user_preferences or {}
            include_metadata = preferences.get("include_metadata", True)
            report_style = preferences.get("report_style", "detailed")  # detailed, summary, bullet_points
            include_statistics = preferences.get("include_statistics", True)
            
            # 分析对话历史
            analysis_result = self._analyze_conversation(conversation_history, analysis_type)
            
            # 生成报告内容
            report_content = await self._generate_report_content(
                conversation_history, 
                analysis_result, 
                analysis_type, 
                preferences
            )
            
            # 构建完整报告
            report = {
                "success": True,
                "report": {
                    "metadata": {
                        "generated_at": datetime.now().isoformat(),
                        "analysis_type": analysis_type,
                        "conversation_count": len(conversation_history),
                        "report_style": report_style,
                        "generator": "智能文档分析系统 - 报告生成器"
                    },
                    "content": report_content,
                    "statistics": analysis_result["statistics"] if include_statistics else None
                },
                "export_formats": ["html", "docx", "pdf", "json"]
            }
            
            logger.info("对话报告生成成功")
            return report
            
        except Exception as e:
            logger.error(f"生成对话报告失败: {e}", exc_info=True)
            return {
                "success": False,
                "error": f"报告生成失败: {str(e)}"
            }
    
    def _analyze_conversation(self, conversation_history: List[Dict], analysis_type: str) -> Dict[str, Any]:
        """分析对话历史"""
        try:
            total_questions = 0
            total_answers = 0
            question_types = {}
            avg_response_length = 0
            response_lengths = []
            
            topics = set()
            keywords = set()
            
            for conv in conversation_history:
                if conv.get("type") == "question":
                    total_questions += 1
                    question_text = conv.get("content", "")
                    
                    # 分析问题类型
                    question_type = self._classify_question_type(question_text, analysis_type)
                    question_types[question_type] = question_types.get(question_type, 0) + 1
                    
                    # 提取关键词和主题
                    extracted_keywords = self._extract_keywords(question_text)
                    keywords.update(extracted_keywords)
                    
                elif conv.get("type") == "answer":
                    total_answers += 1
                    answer_text = conv.get("content", "")
                    response_lengths.append(len(answer_text))
                    
                    # 提取主题
                    extracted_topics = self._extract_topics(answer_text)
                    topics.update(extracted_topics)
            
            if response_lengths:
                avg_response_length = sum(response_lengths) / len(response_lengths)
            
            return {
                "statistics": {
                    "total_questions": total_questions,
                    "total_answers": total_answers,
                    "question_types": question_types,
                    "avg_response_length": round(avg_response_length, 2),
                    "topics_covered": len(topics),
                    "keywords_extracted": len(keywords)
                },
                "topics": list(topics),
                "keywords": list(keywords),
                "question_types_detail": question_types
            }
            
        except Exception as e:
            logger.error(f"分析对话历史失败: {e}")
            return {"statistics": {}, "topics": [], "keywords": [], "question_types_detail": {}}
    
    def _classify_question_type(self, question: str, analysis_type: str) -> str:
        """分类问题类型"""
        question_lower = question.lower()
        
        if analysis_type == "document_qa":
            if any(word in question_lower for word in ["总结", "概述", "核心", "主要"]):
                return "总结类问题"
            elif any(word in question_lower for word in ["解释", "什么", "如何", "为什么"]):
                return "解释类问题"
            elif any(word in question_lower for word in ["数据", "统计", "数字", "比例"]):
                return "数据查询问题"
            elif any(word in question_lower for word in ["建议", "方案", "策略", "方法"]):
                return "建议类问题"
            else:
                return "其他问题"
        else:  # data_analysis
            if any(word in question_lower for word in ["趋势", "变化", "增长", "下降"]):
                return "趋势分析问题"
            elif any(word in question_lower for word in ["关系", "相关", "影响", "关联"]):
                return "关系分析问题"
            elif any(word in question_lower for word in ["异常", "极值", "最大", "最小"]):
                return "异常检测问题"
            elif any(word in question_lower for word in ["预测", "预估", "预计", "未来"]):
                return "预测类问题"
            else:
                return "其他分析问题"
    
    def _extract_keywords(self, text: str) -> List[str]:
        """提取关键词"""
        # 简单的关键词提取逻辑
        keywords = []
        common_words = {"是", "的", "在", "和", "有", "个", "这", "那", "什么", "如何", "为什么", "吗", "呢"}
        
        words = text.replace("？", "").replace("。", "").replace("，", "").split()
        for word in words:
            if len(word) > 1 and word not in common_words:
                keywords.append(word)
        
        return keywords[:10]  # 返回前10个关键词
    
    def _extract_topics(self, text: str) -> List[str]:
        """提取主题"""
        # 简单的主题提取逻辑
        topics = []
        
        # 检查常见主题关键词
        topic_indicators = {
            "数据分析": ["数据", "分析", "统计", "图表", "趋势"],
            "文档内容": ["文档", "内容", "章节", "段落", "要点"],
            "技术问题": ["技术", "方法", "实现", "算法", "流程"],
            "业务问题": ["业务", "商业", "市场", "销售", "客户"],
            "策略建议": ["建议", "策略", "方案", "措施", "计划"]
        }
        
        text_lower = text.lower()
        for topic, indicators in topic_indicators.items():
            if any(indicator in text_lower for indicator in indicators):
                topics.append(topic)
        
        return topics
    
    async def _generate_report_content(self, conversation_history: List[Dict], 
                                     analysis_result: Dict, analysis_type: str, 
                                     preferences: Dict) -> Dict[str, Any]:
        """生成报告内容"""
        try:
            report_style = preferences.get("report_style", "detailed")
            
            # 生成报告标题
            title = self._generate_report_title(analysis_type, len(conversation_history))
            
            # 生成执行摘要
            executive_summary = self._generate_executive_summary(
                conversation_history, analysis_result, analysis_type
            )
            
            # 生成详细内容
            if report_style == "detailed":
                detailed_content = self._generate_detailed_content(conversation_history, analysis_result)
            elif report_style == "summary":
                detailed_content = self._generate_summary_content(conversation_history, analysis_result)
            else:  # bullet_points
                detailed_content = self._generate_bullet_points_content(conversation_history, analysis_result)
            
            # 生成结论和建议
            conclusions = self._generate_conclusions(conversation_history, analysis_result, analysis_type)
            
            return {
                "title": title,
                "executive_summary": executive_summary,
                "main_content": detailed_content,
                "conclusions": conclusions,
                "appendix": {
                    "conversation_timeline": self._create_timeline(conversation_history),
                    "key_topics": analysis_result.get("topics", []),
                    "keywords": analysis_result.get("keywords", [])
                }
            }
            
        except Exception as e:
            logger.error(f"生成报告内容失败: {e}")
            return {"error": f"内容生成失败: {str(e)}"}
    
    def _generate_report_title(self, analysis_type: str, conversation_count: int) -> str:
        """生成报告标题"""
        type_name = "文档问答" if analysis_type == "document_qa" else "数据分析"
        date_str = datetime.now().strftime("%Y年%m月%d日")
        return f"{type_name}对话报告 - {date_str} ({conversation_count}轮对话)"
    
    def _generate_executive_summary(self, conversation_history: List[Dict], 
                                  analysis_result: Dict, analysis_type: str) -> str:
        """生成执行摘要"""
        stats = analysis_result.get("statistics", {})
        topics = analysis_result.get("topics", [])
        
        type_name = "文档问答" if analysis_type == "document_qa" else "数据分析"
        
        summary = f"""
本报告总结了{type_name}会话中的主要内容和发现。

**会话概况：**
- 总问题数：{stats.get('total_questions', 0)}个
- 总回答数：{stats.get('total_answers', 0)}个
- 平均回答长度：{stats.get('avg_response_length', 0)}字符
- 涉及主题：{len(topics)}个

**主要发现：**
"""
        
        # 添加主要主题
        if topics:
            summary += f"- 主要讨论主题包括：{', '.join(topics[:5])}\n"
        
        # 添加问题类型分析
        question_types = analysis_result.get("question_types_detail", {})
        if question_types:
            most_common_type = max(question_types.items(), key=lambda x: x[1])
            summary += f"- 最常见的问题类型是：{most_common_type[0]} ({most_common_type[1]}次)\n"
        
        return summary.strip()
    
    def _generate_detailed_content(self, conversation_history: List[Dict], 
                                 analysis_result: Dict) -> List[Dict]:
        """生成详细内容"""
        content_sections = []
        
        # 对话内容章节
        qa_pairs = []
        current_question = None
        
        for conv in conversation_history:
            if conv.get("type") == "question":
                if current_question and not qa_pairs:
                    qa_pairs.append({
                        "question": current_question,
                        "answer": "未找到对应回答"
                    })
                current_question = conv.get("content", "")
            elif conv.get("type") == "answer" and current_question:
                qa_pairs.append({
                    "question": current_question,
                    "answer": conv.get("content", "")
                })
                current_question = None
        
        content_sections.append({
            "title": "问答详情",
            "type": "qa_pairs",
            "content": qa_pairs
        })
        
        # 主题分析章节
        topics = analysis_result.get("topics", [])
        if topics:
            content_sections.append({
                "title": "主题分析",
                "type": "topics",
                "content": topics
            })
        
        # 关键词章节
        keywords = analysis_result.get("keywords", [])
        if keywords:
            content_sections.append({
                "title": "关键词提取",
                "type": "keywords", 
                "content": keywords
            })
        
        return content_sections
    
    def _generate_summary_content(self, conversation_history: List[Dict], 
                                analysis_result: Dict) -> List[Dict]:
        """生成摘要内容"""
        # 生成简化版的内容
        content_sections = []
        
        # 主要问题摘要
        questions = [conv.get("content", "") for conv in conversation_history if conv.get("type") == "question"]
        if questions:
            content_sections.append({
                "title": "主要问题",
                "type": "bullet_list",
                "content": questions[:10]  # 最多显示10个问题
            })
        
        # 关键发现
        topics = analysis_result.get("topics", [])
        if topics:
            content_sections.append({
                "title": "关键发现",
                "type": "bullet_list",
                "content": [f"涉及{topic}相关内容" for topic in topics[:5]]
            })
        
        return content_sections
    
    def _generate_bullet_points_content(self, conversation_history: List[Dict], 
                                      analysis_result: Dict) -> List[Dict]:
        """生成要点内容"""
        content_sections = []
        
        # 问题要点
        questions = [conv.get("content", "") for conv in conversation_history if conv.get("type") == "question"]
        if questions:
            content_sections.append({
                "title": "问题要点",
                "type": "numbered_list",
                "content": questions
            })
        
        # 主题要点  
        topics = analysis_result.get("topics", [])
        if topics:
            content_sections.append({
                "title": "主题要点",
                "type": "bullet_list",
                "content": topics
            })
        
        return content_sections
    
    def _generate_conclusions(self, conversation_history: List[Dict], 
                            analysis_result: Dict, analysis_type: str) -> Dict[str, Any]:
        """生成结论和建议"""
        stats = analysis_result.get("statistics", {})
        
        conclusions = {
            "summary": "",
            "key_insights": [],
            "recommendations": []
        }
        
        # 生成总结
        total_interactions = stats.get('total_questions', 0)
        type_name = "文档问答" if analysis_type == "document_qa" else "数据分析"
        
        conclusions["summary"] = f"本次{type_name}会话共进行了{total_interactions}轮交互，用户关注的重点主要集中在" + \
                               f"{', '.join(analysis_result.get('topics', [])[:3])}等方面。"
        
        # 生成关键洞察
        question_types = analysis_result.get("question_types_detail", {})
        if question_types:
            most_common = max(question_types.items(), key=lambda x: x[1])
            conclusions["key_insights"].append(f"用户最关心的是{most_common[0]}，共提出{most_common[1]}次相关问题")
        
        if stats.get('avg_response_length', 0) > 500:
            conclusions["key_insights"].append("系统提供了详细全面的回答，平均回答长度较长")
        
        # 生成建议
        if analysis_type == "document_qa":
            conclusions["recommendations"].extend([
                "建议继续深入探讨文档中的核心观点",
                "可以针对具体细节提出更多问题",
                "建议将重要信息整理成结构化的知识点"
            ])
        else:
            conclusions["recommendations"].extend([
                "建议对发现的数据趋势进行进一步验证",
                "可以探索更多数据维度的分析",
                "建议将分析结果应用到实际业务决策中"
            ])
        
        return conclusions
    
    def _create_timeline(self, conversation_history: List[Dict]) -> List[Dict]:
        """创建对话时间线"""
        timeline = []
        
        for i, conv in enumerate(conversation_history):
            timeline.append({
                "sequence": i + 1,
                "type": conv.get("type", "unknown"),
                "timestamp": conv.get("timestamp", ""),
                "content_preview": conv.get("content", "")[:100] + "..." if len(conv.get("content", "")) > 100 else conv.get("content", "")
            })
        
        return timeline
