"""
文档处理相关工具
"""

from typing import Dict, Any, List
from pathlib import Path

from .base_tool import BaseTool, register_tool
from mcp_services.models import ToolParameter, ToolParameterType
from mcp_services.document_parser import DocumentParserService
from utils.file_utils import FileUtils



@register_tool
class DocumentParserTool(BaseTool):
    """文档解析工具"""
    
    def get_name(self) -> str:
        return "document_parser"
    
    def get_description(self) -> str:
        return "解析各种格式的文档并提取文本内容，支持DOCX、PPTX、XLSX、PDF、TXT格式"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "file_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="文档文件路径",
                required=True
            ),
            "extract_tables": ToolParameter(
                type=ToolParameterType.BOOLEAN,
                description="是否提取表格数据",
                default=False
            ),
            "extract_images": ToolParameter(
                type=ToolParameterType.BOOLEAN,
                description="是否提取图片信息",
                default=False
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["file_path"]
    
    async def execute(self, file_path: str, extract_tables: bool = False, 
                     extract_images: bool = False) -> Dict[str, Any]:
        """执行文档解析"""
        # 初始化文档解析服务
        parser_service = DocumentParserService()
        await parser_service.initialize()
        
        # 执行解析
        if extract_tables or extract_images:
            result = await parser_service._parse_document({
                "file_path": file_path,
                "extract_tables": extract_tables,
                "extract_images": extract_images
            })
        else:
            result = await parser_service._extract_text({"file_path": file_path})
        
        return {
            "file_path": file_path,
            "parsed_content": result,
            "file_info": FileUtils.get_file_info(file_path)
        }


@register_tool  
class DocumentAnalysisTool(BaseTool):
    """文档分析工具"""
    
    def get_name(self) -> str:
        return "document_analyzer"
    
    def get_description(self) -> str:
        return "对文档内容进行深度分析，提取关键信息、摘要和结构化数据"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "document_content": ToolParameter(
                type=ToolParameterType.STRING,
                description="文档文本内容",
                required=True
            ),
            "analysis_type": ToolParameter(
                type=ToolParameterType.STRING,
                description="分析类型",
                enum=["summary", "keywords", "structure", "entities", "comprehensive"],
                default="comprehensive"
            ),
            "language": ToolParameter(
                type=ToolParameterType.STRING,
                description="文档语言",
                default="zh"
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["document_content"]
    
    async def execute(self, document_content: str, analysis_type: str = "comprehensive", 
                     language: str = "zh") -> Dict[str, Any]:
        """执行文档分析"""
        from utils.llm_utils import llm_manager
        
        result = {
            "analysis_type": analysis_type,
            "content_length": len(document_content),
            "language": language
        }
        
        if analysis_type in ["summary", "comprehensive"]:
            # 生成摘要
            summary_prompt = f"""请为以下文档内容生成一个简洁的摘要（200字以内）：

{document_content[:3000]}

摘要："""
            
            summary_response = await llm_manager.generate_completion(summary_prompt, max_tokens=500)
            if summary_response.get("success"):
                result["summary"] = summary_response.get("response", "").strip()
        
        if analysis_type in ["keywords", "comprehensive"]:
            # 提取关键词
            keywords_prompt = f"""请从以下文档中提取5-10个关键词，用逗号分隔：

{document_content[:2000]}

关键词："""
            
            keywords_response = await llm_manager.generate_completion(keywords_prompt, max_tokens=200)
            if keywords_response.get("success"):
                keywords_text = keywords_response.get("response", "").strip()
                result["keywords"] = [kw.strip() for kw in keywords_text.split(",")]
        
        if analysis_type in ["structure", "comprehensive"]:
            # 分析文档结构
            paragraphs = [p.strip() for p in document_content.split('\n') if p.strip()]
            result["structure"] = {
                "total_paragraphs": len(paragraphs),
                "avg_paragraph_length": sum(len(p) for p in paragraphs) / len(paragraphs) if paragraphs else 0,
                "has_headings": any(p.strip().endswith(':') or len(p) < 100 for p in paragraphs[:5]),
                "estimated_reading_time": len(document_content.split()) // 200  # 假设每分钟200词
            }
        
        if analysis_type in ["entities", "comprehensive"]:
            # 简单的实体识别（可以后续用NER模型增强）
            import re
            
            # 提取可能的实体
            numbers = re.findall(r'\d+(?:\.\d+)?%?', document_content)
            dates = re.findall(r'\d{4}[年\-/]\d{1,2}[月\-/]\d{1,2}日?', document_content)
            
            result["entities"] = {
                "numbers": list(set(numbers))[:10],  # 最多10个
                "dates": list(set(dates))[:5],       # 最多5个
                "entity_count": len(set(numbers + dates))
            }
        
        return result


@register_tool
class DocumentSearchTool(BaseTool):
    """文档搜索工具"""
    
    def get_name(self) -> str:
        return "document_search"
    
    def get_description(self) -> str:
        return "在文档内容中搜索特定信息并返回相关段落"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "document_content": ToolParameter(
                type=ToolParameterType.STRING,
                description="文档文本内容",
                required=True
            ),
            "query": ToolParameter(
                type=ToolParameterType.STRING,
                description="搜索查询",
                required=True
            ),
            "max_results": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="最大返回结果数",
                default=3
            ),
            "context_size": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="上下文字符数",
                default=200
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["document_content", "query"]
    
    async def execute(self, document_content: str, query: str, 
                     max_results: int = 3, context_size: int = 200) -> Dict[str, Any]:
        """执行文档搜索"""
        import re
        
        query_lower = query.lower()
        query_words = query_lower.split()
        
        # 分割文档为段落
        paragraphs = [p.strip() for p in document_content.split('\n') if p.strip()]
        
        # 计算每个段落的相关性分数
        scored_paragraphs = []
        
        for i, paragraph in enumerate(paragraphs):
            paragraph_lower = paragraph.lower()
            score = 0
            
            # 完全匹配加分
            if query_lower in paragraph_lower:
                score += 10
            
            # 词汇匹配加分
            for word in query_words:
                if word in paragraph_lower:
                    score += 2
                    
            # 模糊匹配加分
            for word in query_words:
                if any(word in w for w in paragraph_lower.split()):
                    score += 1
            
            if score > 0:
                scored_paragraphs.append({
                    "paragraph": paragraph,
                    "score": score,
                    "index": i,
                    "preview": paragraph[:context_size] + ("..." if len(paragraph) > context_size else "")
                })
        
        # 排序并返回最佳匹配
        scored_paragraphs.sort(key=lambda x: x["score"], reverse=True)
        top_results = scored_paragraphs[:max_results]
        
        return {
            "query": query,
            "total_matches": len(scored_paragraphs),
            "results": top_results,
            "search_summary": f"在文档中找到 {len(scored_paragraphs)} 个相关段落，返回前 {min(max_results, len(scored_paragraphs))} 个"
        }