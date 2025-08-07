from typing import Dict, Any, List, Optional, Union
import logging
from pathlib import Path
from .base_workflow import BaseWorkflow, WorkflowStep
from mcp_services.base_service import handle_mcp_request
from agents.base_agent import agent_coordinator

logger = logging.getLogger(__name__)

class DocumentAnalysisWorkflow(BaseWorkflow):
    """文档分析工作流"""
    
    def __init__(self):
        super().__init__(
            name="document_analysis",
            description="完整的文档分析工作流：从文档解析到问答分析"
        )
    
    async def setup_workflow(self):
        """设置工作流步骤"""
        # 步骤1: 文档解析
        parse_step = WorkflowStep(
            name="document_parsing",
            handler=self._parse_document,
            retry_count=2,
            timeout=120,
            critical=True
        )
        
        # 步骤2: 文本提取
        extract_step = WorkflowStep(
            name="text_extraction", 
            handler=self._extract_text,
            dependencies=["document_parsing"],
            retry_count=1,
            timeout=60,
            critical=True
        )
        
        # 步骤3: 问答处理
        qa_step = WorkflowStep(
            name="question_answering",
            handler=self._process_qa,
            dependencies=["text_extraction"],
            retry_count=2,
            timeout=180,
            critical=False
        )
        
        # 步骤4: 结果整合
        integration_step = WorkflowStep(
            name="result_integration",
            handler=self._integrate_results,
            dependencies=["question_answering"],
            retry_count=1,
            timeout=30,
            critical=True
        )
        
        # 添加步骤到工作流
        self.add_step(parse_step)
        self.add_step(extract_step)
        self.add_step(qa_step)
        self.add_step(integration_step)
        
        # 设置执行顺序
        self.set_execution_order([
            "document_parsing",
            "text_extraction", 
            "question_answering",
            "result_integration"
        ])
    
    async def _parse_document(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """解析文档"""
        input_data = context.get("input_data", {})
        file_path = input_data.get("file_path", "")
        extract_tables = input_data.get("extract_tables", True)
        extract_images = input_data.get("extract_images", False)
        
        if not file_path or not Path(file_path).exists():
            raise FileNotFoundError(f"文档文件不存在: {file_path}")
        
        logger.info(f"开始解析文档: {file_path}")
        
        # 调用MCP文档解析服务
        parse_result = await handle_mcp_request(
            method="document_parser/parse_document",
            params={
                "file_path": file_path,
                "extract_tables": extract_tables,
                "extract_images": extract_images
            }
        )
        
        if not parse_result.get("result", {}).get("success", False):
            error = parse_result.get("error", {}).get("message", "文档解析失败")
            raise Exception(f"文档解析失败: {error}")
        
        parsed_data = parse_result["result"]["result"]
        
        logger.info(f"文档解析完成: {file_path}")
        
        return {
            "parsed_document": parsed_data,
            "file_path": file_path,
            "file_type": parsed_data.get("file_type", "unknown")
        }
    
    async def _extract_text(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """提取文本内容"""
        parsed_document = context.get("parsed_document", {})
        file_path = context.get("file_path", "")
        
        if not parsed_document:
            raise ValueError("没有解析的文档数据")
        
        logger.info("开始提取文本内容")
        
        # 从解析结果中获取文本内容
        text_content = parsed_document.get("text_content", "")
        
        if not text_content:
            # 如果解析结果中没有文本，尝试直接提取
            extract_result = await handle_mcp_request(
                method="document_parser/extract_text",
                params={"file_path": file_path}
            )
            
            if extract_result.get("result", {}).get("success", False):
                text_content = extract_result["result"]["result"]["text_content"]
        
        if not text_content:
            raise ValueError("无法提取文档文本内容")
        
        # 提取表格数据
        tables = parsed_document.get("tables", [])
        
        logger.info(f"文本提取完成，长度: {len(text_content)} 字符")
        
        return {
            "text_content": text_content,
            "tables": tables,
            "content_length": len(text_content),
            "table_count": len(tables)
        }
    
    async def _process_qa(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理问答"""
        input_data = context.get("input_data", {})
        text_content = context.get("text_content", "")
        file_type = context.get("file_type", "unknown")
        
        question = input_data.get("question", "")
        
        if not question:
            # 如果没有具体问题，生成默认分析问题
            question = "请总结这个文档的主要内容和关键信息。"
        
        if not text_content:
            raise ValueError("没有可用的文本内容进行问答")
        
        logger.info(f"开始问答处理，问题: {question[:50]}...")
        
        # 使用QA智能体处理问答
        qa_input = {
            "document_content": text_content,
            "question": question,
            "document_type": file_type
        }
        
        qa_result = await agent_coordinator.execute_agent(
            "QA_Agent",
            qa_input,
            context
        )
        
        if not qa_result.get("success", False):
            error = qa_result.get("error", "问答处理失败")
            raise Exception(f"问答处理失败: {error}")
        
        qa_data = qa_result["result"]
        
        logger.info("问答处理完成")
        
        return {
            "qa_result": qa_data,
            "question": question,
            "answer": qa_data.get("answer", ""),
            "confidence": qa_data.get("confidence", 0)
        }
    
    async def _integrate_results(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """整合结果"""
        logger.info("开始整合结果")
        
        # 收集所有处理结果
        parsed_document = context.get("parsed_document", {})
        text_content = context.get("text_content", "")
        tables = context.get("tables", [])
        qa_result = context.get("qa_result", {})
        
        # 构建最终结果
        final_result = {
            "workflow": "document_analysis",
            "file_info": {
                "file_path": context.get("file_path", ""),
                "file_type": context.get("file_type", "unknown"),
                "content_length": context.get("content_length", 0),
                "table_count": context.get("table_count", 0)
            },
            "document_content": {
                "text": text_content,
                "tables": tables,
                "metadata": parsed_document.get("metadata", {})
            },
            "analysis_result": {
                "question": context.get("question", ""),
                "answer": context.get("answer", ""),
                "confidence": context.get("confidence", 0),
                "relevant_passages": qa_result.get("relevant_passages", [])
            },
            "processing_summary": {
                "steps_completed": len([k for k in context.keys() if k.endswith("_result") or k.endswith("_content")]),
                "success": True,
                "total_processing_time": context.get("execution_time", 0)
            }
        }
        
        logger.info("结果整合完成")
        
        return final_result

class MultiDocumentAnalysisWorkflow(BaseWorkflow):
    """多文档分析工作流"""
    
    def __init__(self):
        super().__init__(
            name="multi_document_analysis",
            description="多文档联合分析工作流：处理多个文档并进行综合分析"
        )
    
    async def setup_workflow(self):
        """设置工作流步骤"""
        # 步骤1: 批量文档解析
        batch_parse_step = WorkflowStep(
            name="batch_document_parsing",
            handler=self._batch_parse_documents,
            retry_count=2,
            timeout=300,
            critical=True
        )
        
        # 步骤2: 批量文本提取
        batch_extract_step = WorkflowStep(
            name="batch_text_extraction",
            handler=self._batch_extract_text,
            dependencies=["batch_document_parsing"],
            retry_count=1,
            timeout=180,
            critical=True
        )
        
        # 步骤3: 多文档问答
        multi_qa_step = WorkflowStep(
            name="multi_document_qa",
            handler=self._process_multi_qa,
            dependencies=["batch_text_extraction"],
            retry_count=2,
            timeout=300,
            critical=False
        )
        
        # 步骤4: 综合分析
        synthesis_step = WorkflowStep(
            name="synthesis_analysis",
            handler=self._synthesize_analysis,
            dependencies=["multi_document_qa"],
            retry_count=1,
            timeout=120,
            critical=True
        )
        
        # 添加步骤
        self.add_step(batch_parse_step)
        self.add_step(batch_extract_step)
        self.add_step(multi_qa_step)
        self.add_step(synthesis_step)
        
        # 设置执行顺序
        self.set_execution_order([
            "batch_document_parsing",
            "batch_text_extraction",
            "multi_document_qa", 
            "synthesis_analysis"
        ])
    
    async def _batch_parse_documents(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """批量解析文档"""
        input_data = context.get("input_data", {})
        file_paths = input_data.get("file_paths", [])
        
        if not file_paths:
            raise ValueError("没有提供文档文件路径")
        
        logger.info(f"开始批量解析 {len(file_paths)} 个文档")
        
        parsed_documents = []
        failed_files = []
        
        for file_path in file_paths:
            try:
                if not Path(file_path).exists():
                    failed_files.append({"file_path": file_path, "error": "文件不存在"})
                    continue
                
                # 解析单个文档
                parse_result = await handle_mcp_request(
                    method="document_parser/parse_document",
                    params={
                        "file_path": file_path,
                        "extract_tables": True,
                        "extract_images": False
                    }
                )
                
                if parse_result.get("result", {}).get("success", False):
                    parsed_data = parse_result["result"]["result"]
                    parsed_data["source_file"] = file_path
                    parsed_documents.append(parsed_data)
                else:
                    error = parse_result.get("error", {}).get("message", "解析失败")
                    failed_files.append({"file_path": file_path, "error": error})
                    
            except Exception as e:
                failed_files.append({"file_path": file_path, "error": str(e)})
        
        if not parsed_documents:
            raise Exception("没有成功解析任何文档")
        
        logger.info(f"批量解析完成: 成功 {len(parsed_documents)} 个，失败 {len(failed_files)} 个")
        
        return {
            "parsed_documents": parsed_documents,
            "failed_files": failed_files,
            "success_count": len(parsed_documents),
            "failure_count": len(failed_files)
        }
    
    async def _batch_extract_text(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """批量提取文本"""
        parsed_documents = context.get("parsed_documents", [])
        
        if not parsed_documents:
            raise ValueError("没有解析的文档数据")
        
        logger.info(f"开始批量提取 {len(parsed_documents)} 个文档的文本")
        
        extracted_texts = []
        total_length = 0
        
        for doc in parsed_documents:
            text_content = doc.get("text_content", "")
            tables = doc.get("tables", [])
            source_file = doc.get("source_file", "unknown")
            
            extracted_texts.append({
                "source_file": source_file,
                "content": text_content,
                "tables": tables,
                "length": len(text_content),
                "table_count": len(tables)
            })
            
            total_length += len(text_content)
        
        logger.info(f"批量文本提取完成，总长度: {total_length} 字符")
        
        return {
            "extracted_texts": extracted_texts,
            "document_count": len(extracted_texts),
            "total_length": total_length
        }
    
    async def _process_multi_qa(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """处理多文档问答"""
        input_data = context.get("input_data", {})
        extracted_texts = context.get("extracted_texts", [])
        
        question = input_data.get("question", "请综合分析这些文档的主要内容和关键信息。")
        
        if not extracted_texts:
            raise ValueError("没有提取的文本内容")
        
        logger.info(f"开始多文档问答处理，问题: {question[:50]}...")
        
        # 准备多文档QA输入
        documents = []
        for text_data in extracted_texts:
            documents.append({
                "name": Path(text_data["source_file"]).name,
                "content": text_data["content"],
                "type": "document"
            })
        
        multi_qa_input = {
            "documents": documents,
            "question": question
        }
        
        # 使用多文档QA智能体
        qa_result = await agent_coordinator.execute_agent(
            "MultiDocument_QA_Agent",
            multi_qa_input,
            context
        )
        
        if not qa_result.get("success", False):
            error = qa_result.get("error", "多文档问答处理失败")
            raise Exception(f"多文档问答失败: {error}")
        
        qa_data = qa_result["result"]
        
        logger.info("多文档问答处理完成")
        
        return {
            "multi_qa_result": qa_data,
            "question": question,
            "synthesized_answer": qa_data.get("synthesized_answer", ""),
            "individual_answers": qa_data.get("individual_answers", []),
            "confidence": qa_data.get("confidence", 0)
        }
    
    async def _synthesize_analysis(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """综合分析"""
        logger.info("开始综合分析")
        
        # 收集所有结果
        extracted_texts = context.get("extracted_texts", [])
        multi_qa_result = context.get("multi_qa_result", {})
        
        # 构建综合分析结果
        synthesis_result = {
            "workflow": "multi_document_analysis",
            "summary": {
                "document_count": context.get("document_count", 0),
                "total_content_length": context.get("total_length", 0),
                "processing_success": True
            },
            "documents": [
                {
                    "name": Path(text["source_file"]).name,
                    "path": text["source_file"],
                    "content_length": text["length"],
                    "table_count": text["table_count"]
                }
                for text in extracted_texts
            ],
            "analysis": {
                "question": context.get("question", ""),
                "synthesized_answer": context.get("synthesized_answer", ""),
                "confidence": context.get("confidence", 0),
                "individual_answers": context.get("individual_answers", [])
            },
            "insights": {
                "cross_document_patterns": self._identify_patterns(extracted_texts),
                "document_similarities": self._calculate_similarities(extracted_texts),
                "key_findings": self._extract_key_findings(multi_qa_result)
            }
        }
        
        logger.info("综合分析完成")
        
        return synthesis_result
    
    def _identify_patterns(self, extracted_texts: List[Dict[str, Any]]) -> List[str]:
        """识别跨文档模式"""
        patterns = []
        
        try:
            # 简单的关键词模式识别
            all_texts = " ".join([text["content"] for text in extracted_texts])
            common_words = []
            
            # 这里可以实现更复杂的模式识别逻辑
            patterns.append(f"共处理 {len(extracted_texts)} 个文档")
            patterns.append(f"总文本长度: {len(all_texts)} 字符")
            
        except Exception as e:
            logger.warning(f"模式识别失败: {e}")
            patterns.append("模式识别暂不可用")
        
        return patterns
    
    def _calculate_similarities(self, extracted_texts: List[Dict[str, Any]]) -> Dict[str, float]:
        """计算文档相似度"""
        similarities = {}
        
        try:
            # 简单的相似度计算（基于长度比较）
            if len(extracted_texts) >= 2:
                lengths = [text["length"] for text in extracted_texts]
                avg_length = sum(lengths) / len(lengths)
                
                for i, text in enumerate(extracted_texts):
                    similarity = 1 - abs(text["length"] - avg_length) / avg_length
                    similarities[f"文档{i+1}"] = round(similarity, 3)
                    
        except Exception as e:
            logger.warning(f"相似度计算失败: {e}")
        
        return similarities
    
    def _extract_key_findings(self, multi_qa_result: Dict[str, Any]) -> List[str]:
        """提取关键发现"""
        findings = []
        
        try:
            synthesized_answer = multi_qa_result.get("synthesized_answer", "")
            individual_answers = multi_qa_result.get("individual_answers", [])
            
            if synthesized_answer:
                findings.append(f"综合分析: {synthesized_answer[:100]}...")
            
            if individual_answers:
                findings.append(f"单独分析了 {len(individual_answers)} 个文档")
                
        except Exception as e:
            logger.warning(f"关键发现提取失败: {e}")
            findings.append("关键发现提取暂不可用")
        
        return findings
