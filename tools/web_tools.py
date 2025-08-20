"""
网络相关工具
"""

from typing import Dict, Any, List
import asyncio
import httpx
from bs4 import BeautifulSoup

from .base_tool import BaseTool, register_tool
from mcp_services.models import ToolParameter, ToolParameterType


# 删除了 WebSearchTool。请使用外部MCP提供的搜索工具。


@register_tool
class WebScrapeTool(BaseTool):
    """网页抓取工具"""
    
    def get_name(self) -> str:
        return "web_scrape"
    
    def get_description(self) -> str:
        return "抓取指定URL的网页内容并提取文本信息"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "url": ToolParameter(
                type=ToolParameterType.STRING,
                description="要抓取的网页URL",
                required=True
            ),
            "extract_text": ToolParameter(
                type=ToolParameterType.BOOLEAN,
                description="是否提取纯文本内容",
                default=True
            ),
            "extract_links": ToolParameter(
                type=ToolParameterType.BOOLEAN,
                description="是否提取页面链接",
                default=False
            ),
            "max_content_length": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="最大内容长度",
                default=5000
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["url"]
    
    async def execute(self, url: str, extract_text: bool = True, 
                     extract_links: bool = False, max_content_length: int = 5000) -> Dict[str, Any]:
        """执行网页抓取"""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(url, follow_redirects=True)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                result = {
                    "url": url,
                    "status_code": response.status_code,
                    "title": soup.title.string if soup.title else "",
                    "success": True
                }
                
                if extract_text:
                    # 移除脚本和样式元素
                    for script in soup(["script", "style"]):
                        script.decompose()
                    
                    # 提取文本
                    text = soup.get_text()
                    lines = (line.strip() for line in text.splitlines())
                    chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
                    text = ' '.join(chunk for chunk in chunks if chunk)
                    
                    # 限制长度
                    if len(text) > max_content_length:
                        text = text[:max_content_length] + "..."
                    
                    result["content"] = text
                    result["content_length"] = len(text)
                
                if extract_links:
                    links = []
                    for link in soup.find_all('a', href=True):
                        href = link['href']
                        text = link.get_text().strip()
                        if href and text:
                            links.append({"url": href, "text": text})
                    
                    result["links"] = links[:20]  # 最多20个链接
                    result["links_count"] = len(links)
                
                return result
                
        except Exception as e:
            return {
                "url": url,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


@register_tool
class URLValidatorTool(BaseTool):
    """URL验证工具"""
    
    def get_name(self) -> str:
        return "url_validator"
    
    def get_description(self) -> str:
        return "验证URL的有效性和可访问性"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "url": ToolParameter(
                type=ToolParameterType.STRING,
                description="要验证的URL",
                required=True
            ),
            "timeout": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="超时时间（秒）",
                default=10
            ),
            "check_ssl": ToolParameter(
                type=ToolParameterType.BOOLEAN,
                description="是否检查SSL证书",
                default=True
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["url"]
    
    async def execute(self, url: str, timeout: int = 10, check_ssl: bool = True) -> Dict[str, Any]:
        """执行URL验证"""
        try:
            import time
            start_time = time.time()
            
            async with httpx.AsyncClient(timeout=timeout, verify=check_ssl) as client:
                response = await client.head(url, follow_redirects=True)
                
                response_time = time.time() - start_time
                
                return {
                    "url": url,
                    "valid": True,
                    "status_code": response.status_code,
                    "response_time": round(response_time, 3),
                    "final_url": str(response.url),
                    "redirected": str(response.url) != url,
                    "headers": dict(list(response.headers.items())[:10]),  # 只返回前10个头部
                    "ssl_valid": check_ssl
                }
                
        except httpx.TimeoutException:
            return {
                "url": url,
                "valid": False,
                "error": "请求超时",
                "error_type": "timeout"
            }
        except httpx.SSLError:
            return {
                "url": url,
                "valid": False,
                "error": "SSL证书无效",
                "error_type": "ssl_error"
            }
        except Exception as e:
            return {
                "url": url,
                "valid": False,
                "error": str(e),
                "error_type": type(e).__name__
            }