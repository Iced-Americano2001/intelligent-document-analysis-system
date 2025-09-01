import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, BinaryIO
import logging
import json
from datetime import datetime
from .base_service import BaseMCPService, MCPRequest, MCPResponse

logger = logging.getLogger(__name__)

class FileOperationsService(BaseMCPService):
    """文件操作服务"""
    
    def __init__(self):
        super().__init__("file_operations")
        self.temp_dir = Path("temp")
        self.upload_dir = Path("uploads")
        self.output_dir = Path("outputs")
        
        # 确保目录存在
        for directory in [self.temp_dir, self.upload_dir, self.output_dir]:
            directory.mkdir(exist_ok=True)
    
    async def initialize(self) -> bool:
        """初始化服务"""
        try:
            # 注册工具
            self.register_tool(
                name="read_file",
                description="读取文件内容",
                handler=self._read_file,
                schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "文件编码",
                            "default": "utf-8"
                        }
                    },
                    "required": ["file_path"]
                }
            )
            
            self.register_tool(
                name="write_file",
                description="写入文件内容",
                handler=self._write_file,
                schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        },
                        "content": {
                            "type": "string",
                            "description": "文件内容"
                        },
                        "encoding": {
                            "type": "string",
                            "description": "文件编码",
                            "default": "utf-8"
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "是否覆盖已存在的文件",
                            "default": False
                        }
                    },
                    "required": ["file_path", "content"]
                }
            )
            
            self.register_tool(
                name="copy_file",
                description="复制文件",
                handler=self._copy_file,
                schema={
                    "type": "object",
                    "properties": {
                        "source_path": {
                            "type": "string",
                            "description": "源文件路径"
                        },
                        "destination_path": {
                            "type": "string",
                            "description": "目标文件路径"
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "是否覆盖已存在的文件",
                            "default": False
                        }
                    },
                    "required": ["source_path", "destination_path"]
                }
            )
            
            self.register_tool(
                name="move_file",
                description="移动文件",
                handler=self._move_file,
                schema={
                    "type": "object",
                    "properties": {
                        "source_path": {
                            "type": "string",
                            "description": "源文件路径"
                        },
                        "destination_path": {
                            "type": "string",
                            "description": "目标文件路径"
                        },
                        "overwrite": {
                            "type": "boolean",
                            "description": "是否覆盖已存在的文件",
                            "default": False
                        }
                    },
                    "required": ["source_path", "destination_path"]
                }
            )
            
            self.register_tool(
                name="delete_file",
                description="删除文件",
                handler=self._delete_file,
                schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        },
                        "safe": {
                            "type": "boolean",
                            "description": "安全删除（忽略不存在的文件）",
                            "default": True
                        }
                    },
                    "required": ["file_path"]
                }
            )
            
            self.register_tool(
                name="list_directory",
                description="列出目录内容",
                handler=self._list_directory,
                schema={
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "pattern": {
                            "type": "string",
                            "description": "文件模式匹配",
                            "default": "*"
                        },
                        "recursive": {
                            "type": "boolean",
                            "description": "是否递归列出",
                            "default": False
                        }
                    },
                    "required": ["directory_path"]
                }
            )
            
            self.register_tool(
                name="get_file_info",
                description="获取文件信息",
                handler=self._get_file_info,
                schema={
                    "type": "object",
                    "properties": {
                        "file_path": {
                            "type": "string",
                            "description": "文件路径"
                        }
                    },
                    "required": ["file_path"]
                }
            )
            
            self.register_tool(
                name="create_directory",
                description="创建目录",
                handler=self._create_directory,
                schema={
                    "type": "object",
                    "properties": {
                        "directory_path": {
                            "type": "string",
                            "description": "目录路径"
                        },
                        "parents": {
                            "type": "boolean",
                            "description": "创建父目录",
                            "default": True
                        }
                    },
                    "required": ["directory_path"]
                }
            )
            
            # 注册资源
            self.register_resource(
                uri="file://temp_directory",
                name="临时目录",
                description="临时文件存储目录",
                mime_type="inode/directory"
            )
            
            self.register_resource(
                uri="file://upload_directory",
                name="上传目录",
                description="文件上传目录",
                mime_type="inode/directory"
            )
            
            self.register_resource(
                uri="file://output_directory",
                name="输出目录",
                description="文件输出目录",
                mime_type="inode/directory"
            )
            
            logger.info("文件操作服务初始化完成")
            return True
        except Exception as e:
            logger.error(f"文件操作服务初始化失败: {e}")
            return False
    
    async def handle_request(self, request: MCPRequest) -> MCPResponse:
        """处理请求"""
        method = request.method
        params = request.params
        
        try:
            if method == "read_file":
                result = await self._read_file(params)
            elif method == "write_file":
                result = await self._write_file(params)
            elif method == "copy_file":
                result = await self._copy_file(params)
            elif method == "move_file":
                result = await self._move_file(params)
            elif method == "delete_file":
                result = await self._delete_file(params)
            elif method == "list_directory":
                result = await self._list_directory(params)
            elif method == "get_file_info":
                result = await self._get_file_info(params)
            elif method == "create_directory":
                result = await self._create_directory(params)
            else:
                return self.create_error_response(
                    code=404,
                    message=f"未知方法: {method}",
                    request_id=request.id
                )
            
            return self.create_success_response(result, request.id)
        
        except Exception as e:
            logger.error(f"文件操作服务错误: {e}")
            return self.create_error_response(
                code=500,
                message=str(e),
                request_id=request.id
            )
    
    async def _read_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """读取文件"""
        file_path = params.get("file_path")
        encoding = params.get("encoding", "utf-8")
        
        if not file_path:
            raise ValueError("file_path参数是必需的")
        
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not path.is_file():
            raise IsADirectoryError(f"路径是目录而不是文件: {file_path}")
        
        try:
            with open(path, 'r', encoding=encoding) as f:
                content = f.read()
            
            return {
                "file_path": str(path.absolute()),
                "content": content,
                "size": len(content),
                "encoding": encoding
            }
        except UnicodeDecodeError as e:
            raise ValueError(f"文件编码错误: {e}")
    
    async def _write_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """写入文件"""
        file_path = params.get("file_path")
        content = params.get("content")
        encoding = params.get("encoding", "utf-8")
        overwrite = params.get("overwrite", False)
        
        if not file_path:
            raise ValueError("file_path参数是必需的")
        
        if content is None:
            raise ValueError("content参数是必需的")
        
        path = Path(file_path)
        
        # 检查是否覆盖
        file_existed = path.exists()
        if file_existed and not overwrite:
            raise FileExistsError(f"文件已存在且不允许覆盖: {file_path}")
        
        # 确保父目录存在
        path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            with open(path, 'w', encoding=encoding) as f:
                f.write(content)
            
            return {
                "file_path": str(path.absolute()),
                "bytes_written": len(content.encode(encoding)),
                "encoding": encoding,
                "created": not file_existed
            }
        except Exception as e:
            raise Exception(f"写入文件失败: {e}")
    
    async def _copy_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """复制文件"""
        source_path = params.get("source_path")
        destination_path = params.get("destination_path")
        overwrite = params.get("overwrite", False)
        
        if not source_path or not destination_path:
            raise ValueError("source_path和destination_path参数是必需的")
        
        src = Path(source_path)
        dst = Path(destination_path)
        
        if not src.exists():
            raise FileNotFoundError(f"源文件不存在: {source_path}")
        
        if not src.is_file():
            raise IsADirectoryError(f"源路径是目录而不是文件: {source_path}")
        
        if dst.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在且不允许覆盖: {destination_path}")
        
        # 确保目标目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.copy2(src, dst)
            
            return {
                "source_path": str(src.absolute()),
                "destination_path": str(dst.absolute()),
                "size": dst.stat().st_size,
                "operation": "copy"
            }
        except Exception as e:
            raise Exception(f"复制文件失败: {e}")
    
    async def _move_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """移动文件"""
        source_path = params.get("source_path")
        destination_path = params.get("destination_path")
        overwrite = params.get("overwrite", False)
        
        if not source_path or not destination_path:
            raise ValueError("source_path和destination_path参数是必需的")
        
        src = Path(source_path)
        dst = Path(destination_path)
        
        if not src.exists():
            raise FileNotFoundError(f"源文件不存在: {source_path}")
        
        if dst.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在且不允许覆盖: {destination_path}")
        
        # 确保目标目录存在
        dst.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            shutil.move(str(src), str(dst))
            
            return {
                "source_path": str(src.absolute()),
                "destination_path": str(dst.absolute()),
                "operation": "move"
            }
        except Exception as e:
            raise Exception(f"移动文件失败: {e}")
    
    async def _delete_file(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """删除文件"""
        file_path = params.get("file_path")
        safe = params.get("safe", True)
        
        if not file_path:
            raise ValueError("file_path参数是必需的")
        
        path = Path(file_path)
        
        if not path.exists():
            if safe:
                return {
                    "file_path": str(path.absolute()),
                    "deleted": False,
                    "message": "文件不存在"
                }
            else:
                raise FileNotFoundError(f"文件不存在: {file_path}")
        
        if not path.is_file():
            raise IsADirectoryError(f"路径是目录而不是文件: {file_path}")
        
        try:
            path.unlink()
            
            return {
                "file_path": str(path.absolute()),
                "deleted": True,
                "operation": "delete"
            }
        except Exception as e:
            if safe:
                return {
                    "file_path": str(path.absolute()),
                    "deleted": False,
                    "error": str(e)
                }
            else:
                raise Exception(f"删除文件失败: {e}")
    
    async def _list_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """列出目录内容"""
        directory_path = params.get("directory_path")
        pattern = params.get("pattern", "*")
        recursive = params.get("recursive", False)
        
        if not directory_path:
            raise ValueError("directory_path参数是必需的")
        
        path = Path(directory_path)
        
        if not path.exists():
            raise FileNotFoundError(f"目录不存在: {directory_path}")
        
        if not path.is_dir():
            raise NotADirectoryError(f"路径不是目录: {directory_path}")
        
        try:
            files = []
            directories = []
            
            if recursive:
                items = path.rglob(pattern)
            else:
                items = path.glob(pattern)
            
            for item in items:
                item_info = {
                    "name": item.name,
                    "path": str(item.absolute()),
                    "size": item.stat().st_size if item.is_file() else None,
                    "modified": item.stat().st_mtime,
                    "is_file": item.is_file(),
                    "is_directory": item.is_dir()
                }
                
                if item.is_file():
                    files.append(item_info)
                elif item.is_dir():
                    directories.append(item_info)
            
            return {
                "directory_path": str(path.absolute()),
                "pattern": pattern,
                "recursive": recursive,
                "files": files,
                "directories": directories,
                "file_count": len(files),
                "directory_count": len(directories)
            }
        except Exception as e:
            raise Exception(f"列出目录失败: {e}")
    
    async def _get_file_info(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """获取文件信息"""
        file_path = params.get("file_path")
        
        if not file_path:
            raise ValueError("file_path参数是必需的")
        
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            stat = path.stat()
            
            info = {
                "name": path.name,
                "path": str(path.absolute()),
                "parent": str(path.parent.absolute()),
                "extension": path.suffix.lower(),
                "size": stat.st_size,
                "created": stat.st_ctime,
                "modified": stat.st_mtime,
                "accessed": stat.st_atime,
                "is_file": path.is_file(),
                "is_directory": path.is_dir(),
                "is_symlink": path.is_symlink(),
                "permissions": oct(stat.st_mode)[-3:]
            }
            
            # 对于文件，添加额外信息
            if path.is_file():
                info.update({
                    "size_human": self._format_size(stat.st_size),
                    "mime_type": self._guess_mime_type(path)
                })
            
            return info
        except Exception as e:
            raise Exception(f"获取文件信息失败: {e}")
    
    async def _create_directory(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """创建目录"""
        directory_path = params.get("directory_path")
        parents = params.get("parents", True)
        
        if not directory_path:
            raise ValueError("directory_path参数是必需的")
        
        path = Path(directory_path)
        
        if path.exists():
            if path.is_dir():
                return {
                    "directory_path": str(path.absolute()),
                    "created": False,
                    "message": "目录已存在"
                }
            else:
                raise FileExistsError(f"路径已存在但不是目录: {directory_path}")
        
        try:
            path.mkdir(parents=parents, exist_ok=False)
            
            return {
                "directory_path": str(path.absolute()),
                "created": True,
                "parents": parents,
                "operation": "create_directory"
            }
        except Exception as e:
            raise Exception(f"创建目录失败: {e}")
    
    def _format_size(self, size_bytes: int) -> str:
        """格式化文件大小"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024.0 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    def _guess_mime_type(self, path: Path) -> str:
        """猜测MIME类型"""
        extension = path.suffix.lower()
        mime_map = {
            '.txt': 'text/plain',
            '.json': 'application/json',
            '.xml': 'application/xml',
            '.csv': 'text/csv',
            '.pdf': 'application/pdf',
            '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            '.xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            '.pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.html': 'text/html',
            '.css': 'text/css',
            '.js': 'application/javascript',
            '.py': 'text/x-python'
        }
        return mime_map.get(extension, 'application/octet-stream')
