"""
图表转换工具
用于在报告中处理图表的不同格式转换
"""
import logging
from typing import Dict, Any, Optional
import json
import base64
import io
from pathlib import Path

logger = logging.getLogger(__name__)

class ChartConverter:
    """图表转换器"""
    
    def __init__(self):
        self.supported_formats = ["png", "svg", "html", "json"]
    
    def chart_to_image(self, chart_json: str, format_type: str = "png", 
                      width: int = 800, height: int = 600) -> Optional[str]:
        """
        将图表转换为图片格式
        
        Args:
            chart_json: 图表的JSON字符串
            format_type: 输出格式 ('png', 'svg')
            width: 图片宽度
            height: 图片高度
            
        Returns:
            Base64编码的图片数据，如果失败返回None
        """
        try:
            import plotly.graph_objects as go
            import plotly.io as pio
            
            # 重建图表对象
            chart_data = json.loads(chart_json)
            fig = go.Figure(chart_data)
            
            # 设置图片尺寸
            fig.update_layout(width=width, height=height)
            
            # 转换为图片
            if format_type == "png":
                img_bytes = pio.to_image(fig, format="png", width=width, height=height)
            elif format_type == "svg":
                img_bytes = pio.to_image(fig, format="svg", width=width, height=height)
            else:
                logger.error(f"不支持的图片格式: {format_type}")
                return None
            
            # 编码为base64
            img_b64 = base64.b64encode(img_bytes).decode()
            return img_b64
            
        except Exception as e:
            logger.error(f"图表转换为图片失败: {e}")
            return None
    
    def chart_to_html(self, chart_json: str, div_id: str = None, 
                     include_plotlyjs: str = 'inline') -> Optional[str]:
        """
        将图表转换为HTML格式
        
        Args:
            chart_json: 图表的JSON字符串
            div_id: HTML div的ID
            include_plotlyjs: Plotly JS的包含方式
            
        Returns:
            HTML字符串，如果失败返回None
        """
        try:
            import plotly.graph_objects as go
            import plotly.io as pio
            
            # 重建图表对象
            chart_data = json.loads(chart_json)
            fig = go.Figure(chart_data)
            
            # 转换为HTML
            html = pio.to_html(
                fig, 
                include_plotlyjs=include_plotlyjs,
                div_id=div_id,
                config={'displayModeBar': True, 'responsive': True}
            )
            
            return html
            
        except Exception as e:
            logger.error(f"图表转换为HTML失败: {e}")
            return None
    
    def save_chart_as_file(self, chart_json: str, output_path: str, 
                          format_type: str = "png", width: int = 800, 
                          height: int = 600) -> bool:
        """
        将图表保存为文件
        
        Args:
            chart_json: 图表的JSON字符串
            output_path: 输出文件路径
            format_type: 文件格式
            width: 图片宽度（仅图片格式）
            height: 图片高度（仅图片格式）
            
        Returns:
            是否保存成功
        """
        try:
            import plotly.graph_objects as go
            import plotly.io as pio
            
            # 重建图表对象
            chart_data = json.loads(chart_json)
            fig = go.Figure(chart_data)
            
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if format_type in ["png", "svg", "pdf"]:
                # 保存为图片
                fig.update_layout(width=width, height=height)
                pio.write_image(fig, str(output_path), format=format_type, 
                              width=width, height=height)
            elif format_type == "html":
                # 保存为HTML
                pio.write_html(fig, str(output_path), 
                             include_plotlyjs='inline',
                             config={'displayModeBar': True, 'responsive': True})
            elif format_type == "json":
                # 保存为JSON
                with open(output_path, 'w', encoding='utf-8') as f:
                    f.write(chart_json)
            else:
                logger.error(f"不支持的保存格式: {format_type}")
                return False
            
            logger.info(f"图表已保存到: {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"保存图表文件失败: {e}")
            return False
    
    def extract_chart_summary(self, chart_json: str) -> Dict[str, Any]:
        """
        提取图表摘要信息
        
        Args:
            chart_json: 图表的JSON字符串
            
        Returns:
            包含图表摘要信息的字典
        """
        try:
            chart_data = json.loads(chart_json)
            
            # 提取基本信息
            summary = {
                "chart_type": "未知",
                "title": "",
                "x_axis": "",
                "y_axis": "", 
                "data_points": 0,
                "traces": 0
            }
            
            # 获取图表数据
            if "data" in chart_data:
                summary["traces"] = len(chart_data["data"])
                
                # 分析第一个trace来确定图表类型
                if chart_data["data"]:
                    first_trace = chart_data["data"][0]
                    trace_type = first_trace.get("type", "scatter")
                    
                    if trace_type == "scatter":
                        mode = first_trace.get("mode", "")
                        if "lines" in mode and "markers" in mode:
                            summary["chart_type"] = "线性散点图"
                        elif "lines" in mode:
                            summary["chart_type"] = "折线图"
                        elif "markers" in mode:
                            summary["chart_type"] = "散点图"
                        else:
                            summary["chart_type"] = "散点图"
                    elif trace_type == "bar":
                        summary["chart_type"] = "柱状图"
                    elif trace_type == "histogram":
                        summary["chart_type"] = "直方图"
                    elif trace_type == "box":
                        summary["chart_type"] = "箱线图"
                    elif trace_type == "violin":
                        summary["chart_type"] = "小提琴图"
                    elif trace_type == "heatmap":
                        summary["chart_type"] = "热力图"
                    else:
                        summary["chart_type"] = trace_type
                    
                    # 获取数据点数量
                    if "x" in first_trace:
                        summary["data_points"] = len(first_trace["x"])
            
            # 获取布局信息
            if "layout" in chart_data:
                layout = chart_data["layout"]
                summary["title"] = layout.get("title", {}).get("text", "") if isinstance(layout.get("title"), dict) else layout.get("title", "")
                
                if "xaxis" in layout:
                    summary["x_axis"] = layout["xaxis"].get("title", {}).get("text", "") if isinstance(layout["xaxis"].get("title"), dict) else layout["xaxis"].get("title", "")
                
                if "yaxis" in layout:
                    summary["y_axis"] = layout["yaxis"].get("title", {}).get("text", "") if isinstance(layout["yaxis"].get("title"), dict) else layout["yaxis"].get("title", "")
            
            return summary
            
        except Exception as e:
            logger.error(f"提取图表摘要失败: {e}")
            return {
                "chart_type": "解析失败",
                "title": "",
                "x_axis": "",
                "y_axis": "",
                "data_points": 0,
                "traces": 0,
                "error": str(e)
            }
    
    def validate_chart_json(self, chart_json: str) -> bool:
        """
        验证图表JSON是否有效
        
        Args:
            chart_json: 图表的JSON字符串
            
        Returns:
            是否有效
        """
        try:
            chart_data = json.loads(chart_json)
            
            # 基本结构检查
            if not isinstance(chart_data, dict):
                return False
            
            # 检查必要的字段
            if "data" not in chart_data:
                return False
            
            if not isinstance(chart_data["data"], list):
                return False
            
            # 检查是否有数据
            if len(chart_data["data"]) == 0:
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"图表JSON验证失败: {e}")
            return False
