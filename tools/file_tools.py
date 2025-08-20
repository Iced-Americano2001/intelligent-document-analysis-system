"""
文件操作相关工具
"""

from typing import Dict, Any, List
from pathlib import Path
import shutil
import json

from .base_tool import BaseTool, register_tool
from mcp_services.models import ToolParameter, ToolParameterType
from utils.file_utils import FileUtils


@register_tool
class FileOperationTool(BaseTool):
    """文件操作工具"""
    
    def get_name(self) -> str:
        return "file_operations"
    
    def get_description(self) -> str:
        return "执行文件和目录的基本操作，如复制、移动、删除等"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "operation": ToolParameter(
                type=ToolParameterType.STRING,
                description="操作类型",
                enum=["copy", "move", "delete", "create_dir", "list_dir", "get_info"],
                required=True
            ),
            "source_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="源文件或目录路径",
                required=False
            ),
            "target_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="目标文件或目录路径",
                required=False
            ),
            "overwrite": ToolParameter(
                type=ToolParameterType.BOOLEAN,
                description="是否覆盖现有文件",
                default=False
            ),
            "recursive": ToolParameter(
                type=ToolParameterType.BOOLEAN,
                description="是否递归操作（用于目录操作）",
                default=False
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["operation"]
    
    async def execute(self, operation: str, source_path: str = None, target_path: str = None,
                     overwrite: bool = False, recursive: bool = False) -> Dict[str, Any]:
        """执行文件操作"""
        try:
            if operation == "copy":
                if not source_path or not target_path:
                    raise ValueError("复制操作需要source_path和target_path参数")
                
                result_path = FileUtils.copy_file(source_path, target_path, overwrite)
                return {
                    "operation": "copy",
                    "source": source_path,
                    "target": str(result_path),
                    "success": True
                }
            
            elif operation == "move":
                if not source_path or not target_path:
                    raise ValueError("移动操作需要source_path和target_path参数")
                
                result_path = FileUtils.move_file(source_path, target_path, overwrite)
                return {
                    "operation": "move",
                    "source": source_path,
                    "target": str(result_path),
                    "success": True
                }
            
            elif operation == "delete":
                if not source_path:
                    raise ValueError("删除操作需要source_path参数")
                
                success = FileUtils.delete_file(source_path, safe=True)
                return {
                    "operation": "delete",
                    "path": source_path,
                    "success": success
                }
            
            elif operation == "create_dir":
                if not source_path:
                    raise ValueError("创建目录操作需要source_path参数")
                
                result_path = FileUtils.ensure_directory(source_path)
                return {
                    "operation": "create_dir",
                    "path": str(result_path),
                    "success": True
                }
            
            elif operation == "list_dir":
                if not source_path:
                    raise ValueError("列出目录操作需要source_path参数")
                
                files = FileUtils.list_files(source_path, recursive=recursive)
                file_info = []
                
                for file_path in files:
                    try:
                        info = FileUtils.get_file_info(file_path)
                        file_info.append({
                            "name": info["name"],
                            "path": str(file_path),
                            "size": info["size"],
                            "size_human": info["size_human"],
                            "extension": info["extension"],
                            "is_file": file_path.is_file()
                        })
                    except:
                        continue
                
                return {
                    "operation": "list_dir",
                    "directory": source_path,
                    "file_count": len(file_info),
                    "files": file_info[:50],  # 最多返回50个文件
                    "recursive": recursive
                }
            
            elif operation == "get_info":
                if not source_path:
                    raise ValueError("获取信息操作需要source_path参数")
                
                info = FileUtils.get_file_info(source_path)
                return {
                    "operation": "get_info",
                    "path": source_path,
                    "info": info,
                    "success": True
                }
            
            else:
                raise ValueError(f"不支持的操作类型: {operation}")
                
        except Exception as e:
            return {
                "operation": operation,
                "success": False,
                "error": str(e),
                "source_path": source_path,
                "target_path": target_path
            }


@register_tool
class FileContentTool(BaseTool):
    """文件内容操作工具"""
    
    def get_name(self) -> str:
        return "file_content"
    
    def get_description(self) -> str:
        return "读取、写入和搜索文件内容"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "operation": ToolParameter(
                type=ToolParameterType.STRING,
                description="操作类型",
                enum=["read", "write", "append", "search"],
                required=True
            ),
            "file_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="文件路径",
                required=True
            ),
            "content": ToolParameter(
                type=ToolParameterType.STRING,
                description="要写入或搜索的内容",
                required=False
            ),
            "encoding": ToolParameter(
                type=ToolParameterType.STRING,
                description="文件编码",
                default="utf-8"
            ),
            "max_size": ToolParameter(
                type=ToolParameterType.INTEGER,
                description="最大读取大小（字节）",
                default=1048576  # 1MB
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["operation", "file_path"]
    
    async def execute(self, operation: str, file_path: str, content: str = None,
                     encoding: str = "utf-8", max_size: int = 1048576) -> Dict[str, Any]:
        """执行文件内容操作"""
        try:
            file_path_obj = Path(file_path)
            
            if operation == "read":
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"文件不存在: {file_path}")
                
                # 检查文件大小
                file_size = file_path_obj.stat().st_size
                if file_size > max_size:
                    raise ValueError(f"文件过大: {file_size} 字节，最大限制: {max_size} 字节")
                
                with open(file_path_obj, 'r', encoding=encoding) as f:
                    file_content = f.read()
                
                return {
                    "operation": "read",
                    "file_path": file_path,
                    "content": file_content,
                    "content_length": len(file_content),
                    "encoding": encoding,
                    "success": True
                }
            
            elif operation == "write":
                if content is None:
                    raise ValueError("写入操作需要content参数")
                
                # 确保父目录存在
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path_obj, 'w', encoding=encoding) as f:
                    f.write(content)
                
                return {
                    "operation": "write",
                    "file_path": file_path,
                    "bytes_written": len(content.encode(encoding)),
                    "encoding": encoding,
                    "success": True
                }
            
            elif operation == "append":
                if content is None:
                    raise ValueError("追加操作需要content参数")
                
                # 确保父目录存在
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                with open(file_path_obj, 'a', encoding=encoding) as f:
                    f.write(content)
                
                return {
                    "operation": "append",
                    "file_path": file_path,
                    "bytes_appended": len(content.encode(encoding)),
                    "encoding": encoding,
                    "success": True
                }
            
            elif operation == "search":
                if content is None:
                    raise ValueError("搜索操作需要content参数")
                
                if not file_path_obj.exists():
                    raise FileNotFoundError(f"文件不存在: {file_path}")
                
                with open(file_path_obj, 'r', encoding=encoding) as f:
                    file_content = f.read()
                
                # 搜索内容
                matches = []
                lines = file_content.split('\n')
                
                for line_num, line in enumerate(lines, 1):
                    if content.lower() in line.lower():
                        matches.append({
                            "line_number": line_num,
                            "line_content": line.strip(),
                            "match_position": line.lower().find(content.lower())
                        })
                
                return {
                    "operation": "search",
                    "file_path": file_path,
                    "search_term": content,
                    "matches_found": len(matches),
                    "matches": matches[:20],  # 最多返回20个匹配
                    "success": True
                }
            
            else:
                raise ValueError(f"不支持的操作类型: {operation}")
                
        except Exception as e:
            return {
                "operation": operation,
                "file_path": file_path,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }


@register_tool
class FileCompressionTool(BaseTool):
    """文件压缩工具"""
    
    def get_name(self) -> str:
        return "file_compression"
    
    def get_description(self) -> str:
        return "压缩和解压缩文件"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "operation": ToolParameter(
                type=ToolParameterType.STRING,
                description="操作类型",
                enum=["compress", "extract"],
                required=True
            ),
            "source_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="源文件或目录路径",
                required=True
            ),
            "target_path": ToolParameter(
                type=ToolParameterType.STRING,
                description="目标压缩文件或解压目录路径",
                required=True
            ),
            "format": ToolParameter(
                type=ToolParameterType.STRING,
                description="压缩格式",
                enum=["zip", "tar", "gztar"],
                default="zip"
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["operation", "source_path", "target_path"]
    
    async def execute(self, operation: str, source_path: str, target_path: str,
                     format: str = "zip") -> Dict[str, Any]:
        """执行文件压缩操作"""
        try:
            source_path_obj = Path(source_path)
            target_path_obj = Path(target_path)
            
            if operation == "compress":
                if not source_path_obj.exists():
                    raise FileNotFoundError(f"源路径不存在: {source_path}")
                
                # 确保目标目录存在
                target_path_obj.parent.mkdir(parents=True, exist_ok=True)
                
                # 创建压缩文件
                if format == "zip":
                    import zipfile
                    with zipfile.ZipFile(target_path_obj, 'w', zipfile.ZIP_DEFLATED) as zipf:
                        if source_path_obj.is_file():
                            zipf.write(source_path_obj, source_path_obj.name)
                        else:
                            for file_path in source_path_obj.rglob('*'):
                                if file_path.is_file():
                                    zipf.write(file_path, file_path.relative_to(source_path_obj))
                else:
                    # 使用shutil进行tar压缩
                    base_name = str(target_path_obj).replace(f'.{format}', '')
                    shutil.make_archive(base_name, format, source_path_obj)
                
                compressed_size = target_path_obj.stat().st_size
                
                return {
                    "operation": "compress",
                    "source": source_path,
                    "target": str(target_path_obj),
                    "format": format,
                    "compressed_size": compressed_size,
                    "compressed_size_human": FileUtils.format_file_size(compressed_size),
                    "success": True
                }
            
            elif operation == "extract":
                if not source_path_obj.exists():
                    raise FileNotFoundError(f"压缩文件不存在: {source_path}")
                
                # 确保目标目录存在
                target_path_obj.mkdir(parents=True, exist_ok=True)
                
                # 解压文件
                if format == "zip":
                    import zipfile
                    with zipfile.ZipFile(source_path_obj, 'r') as zipf:
                        zipf.extractall(target_path_obj)
                        extracted_files = zipf.namelist()
                else:
                    # 使用shutil进行tar解压
                    shutil.unpack_archive(source_path_obj, target_path_obj, format)
                    extracted_files = list(target_path_obj.rglob('*'))
                    extracted_files = [str(f.relative_to(target_path_obj)) for f in extracted_files if f.is_file()]
                
                return {
                    "operation": "extract",
                    "source": source_path,
                    "target": str(target_path_obj),
                    "format": format,
                    "extracted_files_count": len(extracted_files),
                    "extracted_files": extracted_files[:20],  # 最多显示20个文件
                    "success": True
                }
            
            else:
                raise ValueError(f"不支持的操作类型: {operation}")
                
        except Exception as e:
            return {
                "operation": operation,
                "source_path": source_path,
                "target_path": target_path,
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }