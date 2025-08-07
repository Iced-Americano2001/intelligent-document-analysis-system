from typing import Dict, Any, List, Optional, Union
import logging
from .base_agent import BaseAgent
from config.settings import get_prompt_template

logger = logging.getLogger(__name__)

class QAAgent(BaseAgent):
    """文档问答智能体"""
    
    def __init__(self):
        super().__init__(
            name="QA_Agent",
            description="基于文档内容进行智能问答的智能体"
        )
        self.add_capability("document_qa")
        self.add_capability("context_understanding")
        self.add_capability("question_answering")
        self.max_context_length = 6000
        self.temperature = 0.7
        
        # 使用第三方API作为默认提供商
        from config.settings import is_third_party_enabled
        if is_third_party_enabled():
            self.llm_provider = "third_party"
        else:
            self.llm_provider = "openai"  # 备选方案
    
    async def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理文档问答请求"""
        if not isinstance(input_data, dict):
            raise ValueError("输入数据必须是字典格式")
        
        document_content = input_data.get("document_content", "")
        question = input_data.get("question", "")
        document_type = input_data.get("document_type", "unknown")
        
        if not document_content:
            raise ValueError("文档内容不能为空")
        
        if not question:
            raise ValueError("问题不能为空")
        
        # 记录处理开始
        self.add_memory({
            "type": "qa_start",
            "question": question,
            "document_type": document_type,
            "content_length": len(document_content)
        })
        
        try:
            # 截断文档内容以适应上下文限制
            truncated_content = self._truncate_text(document_content, 4000)
            
            # 构建提示词
            prompt = self._build_qa_prompt(truncated_content, question, document_type)
            
            # 获取LLM响应
            answer = await self._get_llm_response(prompt, max_tokens=1500)
            
            # 分析答案置信度
            confidence = await self._analyze_confidence(question, document_content, answer)
            
            # 提取相关段落
            relevant_passages = self._extract_relevant_passages(document_content, question)
            
            result = {
                "question": question,
                "answer": answer,
                "confidence": confidence,
                "relevant_passages": relevant_passages,
                "document_type": document_type,
                "content_length": len(document_content),
                "answer_length": len(answer)
            }
            
            # 记录成功处理
            self.add_memory({
                "type": "qa_success",
                "question": question[:100],
                "answer_length": len(answer),
                "confidence": confidence
            })
            
            return result
            
        except Exception as e:
            logger.error(f"QA处理失败: {e}")
            self.add_memory({
                "type": "qa_error",
                "question": question[:100],
                "error": str(e)
            })
            raise
    
    def _build_qa_prompt(self, document_content: str, question: str, document_type: str) -> str:
        """构建问答提示词"""
        # 获取基础模板
        base_template = get_prompt_template("document_qa")
        
        if base_template:
            return base_template.format(
                document_content=document_content,
                question=question
            )
        
        # 如果没有模板，使用默认提示词
        return f"""你是一个专业的文档分析助手。请基于以下文档内容回答用户的问题。

文档类型: {document_type}

文档内容:
{document_content}

用户问题: {question}

请提供准确、详细的回答。如果文档中没有直接相关的信息，请明确说明并基于相关内容进行合理推测。

要求:
1. 回答要基于文档内容
2. 如果信息不足，请明确指出
3. 提供具体的引用或参考
4. 保持客观和专业

回答:"""
    
    async def _analyze_confidence(self, question: str, document_content: str, answer: str) -> float:
        """分析答案置信度"""
        try:
            confidence_prompt = f"""请评估以下回答的置信度（0-1之间的分数）:

问题: {question}
回答: {answer}

评估标准:
- 回答是否直接基于文档内容
- 回答的完整性和准确性
- 回答是否包含推测或不确定内容

请只返回一个0-1之间的数字，表示置信度。"""
            
            confidence_response = await self._get_llm_response(confidence_prompt, max_tokens=10)
            
            # 尝试解析置信度数值
            try:
                confidence = float(confidence_response.strip())
                return max(0.0, min(1.0, confidence))
            except ValueError:
                # 如果无法解析，使用基于关键词的简单评估
                return self._simple_confidence_analysis(question, document_content, answer)
                
        except Exception as e:
            logger.warning(f"置信度分析失败: {e}")
            return self._simple_confidence_analysis(question, document_content, answer)
    
    def _simple_confidence_analysis(self, question: str, document_content: str, answer: str) -> float:
        """简单的置信度分析"""
        confidence = 0.5  # 基础置信度
        
        # 检查回答中是否包含"不确定"、"可能"等词汇
        uncertainty_words = ["不确定", "可能", "也许", "推测", "估计", "大概", "似乎"]
        uncertainty_count = sum(1 for word in uncertainty_words if word in answer)
        confidence -= uncertainty_count * 0.1
        
        # 检查问题关键词在文档中的覆盖率
        question_words = set(question.split())
        document_words = set(document_content.split())
        coverage = len(question_words & document_words) / len(question_words) if question_words else 0
        confidence += coverage * 0.3
        
        # 检查回答长度合理性
        if len(answer) < 20:
            confidence -= 0.2
        elif len(answer) > 500:
            confidence += 0.1
        
        return max(0.0, min(1.0, confidence))
    
    def _extract_relevant_passages(self, document_content: str, question: str, max_passages: int = 3) -> List[str]:
        """提取相关段落"""
        try:
            # 将文档分割成段落
            paragraphs = [p.strip() for p in document_content.split('\n') if p.strip() and len(p.strip()) > 50]
            
            if not paragraphs:
                return []
            
            # 简单的相关性评分（基于关键词匹配）
            question_words = set(question.lower().split())
            scored_paragraphs = []
            
            for paragraph in paragraphs:
                paragraph_words = set(paragraph.lower().split())
                score = len(question_words & paragraph_words)
                if score > 0:
                    scored_paragraphs.append((score, paragraph))
            
            # 按分数排序并返回前N个
            scored_paragraphs.sort(key=lambda x: x[0], reverse=True)
            return [para for _, para in scored_paragraphs[:max_passages]]
            
        except Exception as e:
            logger.warning(f"段落提取失败: {e}")
            return []
    
    async def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        if not isinstance(input_data, dict):
            return False
        
        required_fields = ["document_content", "question"]
        return all(field in input_data and input_data[field] for field in required_fields)
    
    async def preprocess(self, input_data: Any) -> Any:
        """预处理输入数据"""
        # 清理和标准化文本
        if isinstance(input_data, dict):
            processed_data = input_data.copy()
            
            # 清理文档内容
            if "document_content" in processed_data:
                content = processed_data["document_content"]
                # 移除多余的空白字符
                content = ' '.join(content.split())
                processed_data["document_content"] = content
            
            # 清理问题
            if "question" in processed_data:
                question = processed_data["question"].strip()
                processed_data["question"] = question
            
            return processed_data
        
        return input_data

class MultiDocumentQAAgent(QAAgent):
    """多文档问答智能体"""
    
    def __init__(self):
        super().__init__()
        self.name = "MultiDocument_QA_Agent"
        self.description = "支持多文档联合问答的智能体"
        self.add_capability("multi_document_qa")
        self.add_capability("document_synthesis")
        self.max_context_length = 8000
    
    async def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理多文档问答请求"""
        if not isinstance(input_data, dict):
            raise ValueError("输入数据必须是字典格式")
        
        documents = input_data.get("documents", [])
        question = input_data.get("question", "")
        
        if not documents:
            raise ValueError("文档列表不能为空")
        
        if not question:
            raise ValueError("问题不能为空")
        
        try:
            # 对每个文档进行问答
            document_answers = []
            total_content_length = 0
            
            for i, doc in enumerate(documents):
                if isinstance(doc, dict):
                    doc_content = doc.get("content", "")
                    doc_name = doc.get("name", f"文档{i+1}")
                    doc_type = doc.get("type", "unknown")
                else:
                    doc_content = str(doc)
                    doc_name = f"文档{i+1}"
                    doc_type = "text"
                
                if not doc_content:
                    continue
                
                total_content_length += len(doc_content)
                
                # 单文档问答
                single_qa_input = {
                    "document_content": doc_content,
                    "question": question,
                    "document_type": doc_type
                }
                
                single_result = await super().process(single_qa_input, context)
                single_result["document_name"] = doc_name
                document_answers.append(single_result)
            
            # 综合所有答案
            synthesized_answer = await self._synthesize_answers(question, document_answers)
            
            result = {
                "question": question,
                "document_count": len(documents),
                "total_content_length": total_content_length,
                "individual_answers": document_answers,
                "synthesized_answer": synthesized_answer,
                "confidence": await self._calculate_overall_confidence(document_answers)
            }
            
            self.add_memory({
                "type": "multi_qa_success",
                "question": question[:100],
                "document_count": len(documents),
                "total_length": total_content_length
            })
            
            return result
            
        except Exception as e:
            logger.error(f"多文档QA处理失败: {e}")
            self.add_memory({
                "type": "multi_qa_error",
                "question": question[:100],
                "error": str(e)
            })
            raise
    
    async def _synthesize_answers(self, question: str, document_answers: List[Dict[str, Any]]) -> str:
        """综合多个文档的答案"""
        if not document_answers:
            return "未找到相关信息。"
        
        if len(document_answers) == 1:
            return document_answers[0]["answer"]
        
        try:
            # 构建综合提示词
            synthesis_prompt = f"""基于以下多个文档的回答，请提供一个综合的答案：

问题: {question}

各文档的回答:
"""
            
            for i, doc_answer in enumerate(document_answers, 1):
                doc_name = doc_answer.get("document_name", f"文档{i}")
                answer = doc_answer.get("answer", "")
                confidence = doc_answer.get("confidence", 0)
                
                synthesis_prompt += f"\n{doc_name} (置信度: {confidence:.2f}):\n{answer}\n"
            
            synthesis_prompt += """
请提供一个综合的回答，要求：
1. 整合所有相关信息
2. 解决可能的矛盾
3. 指出信息的来源
4. 如果文档间有分歧，请说明

综合回答:"""
            
            return await self._get_llm_response(synthesis_prompt, max_tokens=2000)
            
        except Exception as e:
            logger.error(f"答案综合失败: {e}")
            # 降级为简单拼接
            return self._simple_answer_combination(document_answers)
    
    def _simple_answer_combination(self, document_answers: List[Dict[str, Any]]) -> str:
        """简单的答案合并"""
        combined_parts = []
        
        for i, doc_answer in enumerate(document_answers, 1):
            doc_name = doc_answer.get("document_name", f"文档{i}")
            answer = doc_answer.get("answer", "")
            
            if answer and answer not in ["", "未找到相关信息。"]:
                combined_parts.append(f"根据{doc_name}: {answer}")
        
        if not combined_parts:
            return "在提供的文档中未找到相关信息。"
        
        return "\n\n".join(combined_parts)
    
    async def _calculate_overall_confidence(self, document_answers: List[Dict[str, Any]]) -> float:
        """计算整体置信度"""
        if not document_answers:
            return 0.0
        
        confidences = [doc.get("confidence", 0) for doc in document_answers]
        valid_confidences = [c for c in confidences if c > 0]
        
        if not valid_confidences:
            return 0.0
        
        # 使用加权平均，置信度高的文档权重更大
        weights = [c for c in valid_confidences]
        weighted_sum = sum(c * w for c, w in zip(valid_confidences, weights))
        weight_sum = sum(weights)
        
        return weighted_sum / weight_sum if weight_sum > 0 else 0.0
