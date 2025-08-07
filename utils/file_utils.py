import os
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO
import magic
import hashlib
from loguru import logger

class FileUtils:
    """文件处理工具类"""
    
    @staticmethod
    def ensure_directory(directory: Union[str, Path]) -> Path:
        """确保目录存在，如果不存在则创建"""
        dir_path = Path(directory)
        dir_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"确保目录存在: {dir_path}")
        return dir_path
    
    @staticmethod
    def get_file_size(file_path: Union[str, Path]) -> int:
        """获取文件大小（字节）"""
        return Path(file_path).stat().st_size
    
    @staticmethod
    def get_file_hash(file_path: Union[str, Path], algorithm: str = "md5") -> str:
        """计算文件哈希值"""
        hash_obj = hashlib.new(algorithm)
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()
    
    @staticmethod
    def get_file_info(file_path: Union[str, Path]) -> Dict:
        """获取文件详细信息"""
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"文件不存在: {file_path}")
        
        stat = path.stat()
        return {
            "name": path.name,
            "extension": path.suffix.lower(),
            "size": stat.st_size,
            "size_human": FileUtils.format_file_size(stat.st_size),
            "created": stat.st_ctime,
            "modified": stat.st_mtime,
            "absolute_path": str(path.absolute()),
            "mime_type": FileUtils.get_mime_type(file_path),
            "hash": FileUtils.get_file_hash(file_path),
        }
    
    @staticmethod
    def format_file_size(size_bytes: int) -> str:
        """格式化文件大小为人类可读格式"""
        if size_bytes == 0:
            return "0B"
        
        size_names = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        while size_bytes >= 1024.0 and i < len(size_names) - 1:
            size_bytes /= 1024.0
            i += 1
        
        return f"{size_bytes:.1f}{size_names[i]}"
    
    @staticmethod
    def get_mime_type(file_path: Union[str, Path]) -> str:
        """获取文件MIME类型"""
        try:
            return magic.from_file(str(file_path), mime=True)
        except Exception as e:
            logger.warning(f"无法获取文件MIME类型: {e}")
            return "application/octet-stream"
    
    @staticmethod
    def is_valid_file_type(file_path: Union[str, Path], allowed_extensions: List[str]) -> bool:
        """检查文件类型是否有效"""
        extension = Path(file_path).suffix.lower()
        return extension in [ext.lower() for ext in allowed_extensions]
    
    @staticmethod
    def clean_filename(filename: str) -> str:
        """清理文件名，移除特殊字符"""
        import re
        # 移除或替换不安全的字符
        cleaned = re.sub(r'[<>:"/\\|?*]', '_', filename)
        # 移除多余的空格和点
        cleaned = re.sub(r'\s+', ' ', cleaned).strip(' .')
        return cleaned
    
    @staticmethod
    def copy_file(src: Union[str, Path], dst: Union[str, Path], 
                  overwrite: bool = False) -> Path:
        """复制文件"""
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src}")
        
        if dst_path.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在: {dst}")
        
        # 确保目标目录存在
        FileUtils.ensure_directory(dst_path.parent)
        
        shutil.copy2(src_path, dst_path)
        logger.info(f"文件复制完成: {src} -> {dst}")
        return dst_path
    
    @staticmethod
    def move_file(src: Union[str, Path], dst: Union[str, Path], 
                  overwrite: bool = False) -> Path:
        """移动文件"""
        src_path = Path(src)
        dst_path = Path(dst)
        
        if not src_path.exists():
            raise FileNotFoundError(f"源文件不存在: {src}")
        
        if dst_path.exists() and not overwrite:
            raise FileExistsError(f"目标文件已存在: {dst}")
        
        # 确保目标目录存在
        FileUtils.ensure_directory(dst_path.parent)
        
        shutil.move(str(src_path), str(dst_path))
        logger.info(f"文件移动完成: {src} -> {dst}")
        return dst_path
    
    @staticmethod
    def delete_file(file_path: Union[str, Path], safe: bool = True) -> bool:
        """删除文件"""
        path = Path(file_path)
        
        if not path.exists():
            if safe:
                logger.warning(f"文件不存在，跳过删除: {file_path}")
                return False
            else:
                raise FileNotFoundError(f"文件不存在: {file_path}")
        
        try:
            path.unlink()
            logger.info(f"文件删除成功: {file_path}")
            return True
        except Exception as e:
            logger.error(f"文件删除失败: {file_path}, 错误: {e}")
            if not safe:
                raise
            return False
    
    @staticmethod
    def list_files(directory: Union[str, Path], 
                   pattern: str = "*", 
                   recursive: bool = False) -> List[Path]:
        """列出目录中的文件"""
        dir_path = Path(directory)
        
        if not dir_path.exists():
            raise FileNotFoundError(f"目录不存在: {directory}")
        
        if not dir_path.is_dir():
            raise NotADirectoryError(f"不是目录: {directory}")
        
        if recursive:
            return list(dir_path.rglob(pattern))
        else:
            return list(dir_path.glob(pattern))
    
    @staticmethod
    def get_temp_filename(prefix: str = "temp_", suffix: str = "", 
                         directory: Optional[Union[str, Path]] = None) -> Path:
        """生成临时文件名"""
        import tempfile
        import uuid
        
        if directory:
            FileUtils.ensure_directory(directory)
            temp_dir = str(directory)
        else:
            temp_dir = tempfile.gettempdir()
        
        unique_id = str(uuid.uuid4())[:8]
        filename = f"{prefix}{unique_id}{suffix}"
        return Path(temp_dir) / filename
    
    @staticmethod
    def read_file_chunks(file_path: Union[str, Path], chunk_size: int = 8192):
        """分块读取文件"""
        with open(file_path, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                yield chunk
    
    @staticmethod
    def validate_file_upload(file_obj: BinaryIO, 
                           max_size: int = 50 * 1024 * 1024,  # 50MB
                           allowed_types: Optional[List[str]] = None) -> Dict:
        """验证上传的文件"""
        # 获取文件大小
        file_obj.seek(0, 2)  # 移到文件末尾
        size = file_obj.tell()
        file_obj.seek(0)  # 重置到开头
        
        # 检查文件大小
        if size > max_size:
            return {
                "valid": False,
                "error": f"文件过大，最大允许 {FileUtils.format_file_size(max_size)}"
            }
        
        # 检查文件类型（如果指定）
        if allowed_types and hasattr(file_obj, 'name'):
            extension = Path(file_obj.name).suffix.lower()
            if extension not in [ext.lower() for ext in allowed_types]:
                return {
                    "valid": False,
                    "error": f"不支持的文件类型，允许的类型: {', '.join(allowed_types)}"
                }
        
        return {
            "valid": True,
            "size": size,
            "size_human": FileUtils.format_file_size(size)
        }

    @staticmethod
    def is_file_supported(filename: str) -> bool:
        """检查文件格式是否受支持"""
        from config.settings import get_supported_formats
        file_ext = Path(filename).suffix.lower()
        return file_ext in get_supported_formats()
