import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any, List, Optional, Union, Tuple
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

class DataProcessor:
    """数据处理器类"""
    
    def __init__(self):
        self.data = None
        self.metadata = {}
    
    def load_data(self, data: Union[pd.DataFrame, Dict, List], source: str = "unknown"):
        """加载数据"""
        if isinstance(data, pd.DataFrame):
            self.data = data
        elif isinstance(data, dict):
            self.data = pd.DataFrame([data])
        elif isinstance(data, list):
            self.data = pd.DataFrame(data)
        else:
            raise ValueError(f"不支持的数据类型: {type(data)}")
        
        self.metadata = {
            "source": source,
            "shape": self.data.shape,
            "columns": list(self.data.columns),
            "dtypes": self.data.dtypes.to_dict(),
            "memory_usage": self.data.memory_usage(deep=True).sum(),
        }
        
        logger.info(f"数据加载完成: {self.metadata['shape']} 行列")
        return self
    
    def get_summary(self) -> Dict[str, Any]:
        """获取数据摘要"""
        if self.data is None:
            return {"error": "没有加载数据"}
        
        summary = {
            "基本信息": {
                "行数": len(self.data),
                "列数": len(self.data.columns),
                "内存使用": f"{self.metadata.get('memory_usage', 0) / 1024 / 1024:.2f} MB",
                "数据源": self.metadata.get('source', 'unknown')
            },
            "列信息": {},
            "统计信息": {},
            "缺失值": {},
            "数据类型": {}
        }
        
        # 列信息和缺失值
        for col in self.data.columns:
            col_data = self.data[col]
            summary["列信息"][col] = {
                "非空值": col_data.notna().sum(),
                "缺失值": col_data.isna().sum(),
                "缺失率": f"{col_data.isna().sum() / len(col_data) * 100:.1f}%",
                "数据类型": str(col_data.dtype),
                "唯一值": col_data.nunique()
            }
            
            # 数值型列的统计信息
            if pd.api.types.is_numeric_dtype(col_data):
                summary["统计信息"][col] = {
                    "平均值": round(col_data.mean(), 2) if not col_data.isna().all() else None,
                    "中位数": round(col_data.median(), 2) if not col_data.isna().all() else None,
                    "标准差": round(col_data.std(), 2) if not col_data.isna().all() else None,
                    "最小值": col_data.min() if not col_data.isna().all() else None,
                    "最大值": col_data.max() if not col_data.isna().all() else None,
                }
        
        return summary
    
    def clean_data(self, operations: List[str] = None) -> 'DataProcessor':
        """清理数据"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        if operations is None:
            operations = ["remove_duplicates", "fill_numeric_na", "strip_strings"]
        
        original_shape = self.data.shape
        
        for operation in operations:
            if operation == "remove_duplicates":
                before = len(self.data)
                self.data = self.data.drop_duplicates()
                logger.info(f"移除重复行: {before - len(self.data)} 行")
            
            elif operation == "fill_numeric_na":
                numeric_cols = self.data.select_dtypes(include=[np.number]).columns
                for col in numeric_cols:
                    if self.data[col].isna().any():
                        fill_value = self.data[col].median()
                        self.data[col].fillna(fill_value, inplace=True)
                logger.info(f"数值列缺失值填充完成: {len(numeric_cols)} 列")
            
            elif operation == "strip_strings":
                string_cols = self.data.select_dtypes(include=['object']).columns
                for col in string_cols:
                    self.data[col] = self.data[col].astype(str).str.strip()
                logger.info(f"字符串列去空格完成: {len(string_cols)} 列")
            
            elif operation == "remove_empty_rows":
                before = len(self.data)
                self.data = self.data.dropna(how='all')
                logger.info(f"移除空行: {before - len(self.data)} 行")
        
        logger.info(f"数据清理完成: {original_shape} -> {self.data.shape}")
        return self
    
    def filter_data(self, conditions: Dict[str, Any]) -> 'DataProcessor':
        """过滤数据"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        original_length = len(self.data)
        filtered_data = self.data.copy()
        
        for column, condition in conditions.items():
            if column not in filtered_data.columns:
                logger.warning(f"列 '{column}' 不存在，跳过过滤")
                continue
            
            if isinstance(condition, dict):
                if 'min' in condition:
                    filtered_data = filtered_data[filtered_data[column] >= condition['min']]
                if 'max' in condition:
                    filtered_data = filtered_data[filtered_data[column] <= condition['max']]
                if 'in' in condition:
                    filtered_data = filtered_data[filtered_data[column].isin(condition['in'])]
                if 'not_in' in condition:
                    filtered_data = filtered_data[~filtered_data[column].isin(condition['not_in'])]
            else:
                filtered_data = filtered_data[filtered_data[column] == condition]
        
        self.data = filtered_data
        logger.info(f"数据过滤完成: {original_length} -> {len(self.data)} 行")
        return self
    
    def aggregate_data(self, group_by: List[str], agg_funcs: Dict[str, Union[str, List[str]]]) -> pd.DataFrame:
        """聚合数据"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        try:
            result = self.data.groupby(group_by).agg(agg_funcs)
            logger.info(f"数据聚合完成: 按 {group_by} 分组")
            return result
        except Exception as e:
            logger.error(f"数据聚合失败: {e}")
            raise

class DataAnalyzer:
    """数据分析器类"""
    
    def __init__(self, data_processor: DataProcessor):
        self.processor = data_processor
        self.analysis_results = {}
    
    @property
    def data(self) -> pd.DataFrame:
        """获取数据"""
        return self.processor.data
    
    def descriptive_analysis(self, columns: Optional[List[str]] = None) -> Dict[str, Any]:
        """描述性分析"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        if columns is None:
            numeric_columns = self.data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            numeric_columns = [col for col in columns if col in self.data.columns 
                             and pd.api.types.is_numeric_dtype(self.data[col])]
        
        if not numeric_columns:
            return {"error": "没有找到数值型列"}
        
        analysis = {}
        for col in numeric_columns:
            col_data = self.data[col].dropna()
            
            analysis[col] = {
                "计数": len(col_data),
                "平均值": float(col_data.mean()),
                "中位数": float(col_data.median()),
                "标准差": float(col_data.std()),
                "最小值": float(col_data.min()),
                "最大值": float(col_data.max()),
                "25%分位数": float(col_data.quantile(0.25)),
                "75%分位数": float(col_data.quantile(0.75)),
                "偏度": float(col_data.skew()),
                "峰度": float(col_data.kurtosis()),
            }
        
        self.analysis_results["descriptive"] = analysis
        return analysis
    
    def correlation_analysis(self, columns: Optional[List[str]] = None, method: str = "pearson") -> Dict[str, Any]:
        """相关性分析"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        if columns is None:
            numeric_columns = self.data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            numeric_columns = [col for col in columns if col in self.data.columns 
                             and pd.api.types.is_numeric_dtype(self.data[col])]
        
        if len(numeric_columns) < 2:
            return {"error": "至少需要2个数值型列进行相关性分析"}
        
        correlation_matrix = self.data[numeric_columns].corr(method=method)
        
        # 转换为字典格式
        correlation_dict = {}
        for i, col1 in enumerate(numeric_columns):
            for j, col2 in enumerate(numeric_columns):
                if i < j:  # 只保留上三角
                    key = f"{col1} - {col2}"
                    correlation_dict[key] = round(correlation_matrix.loc[col1, col2], 3)
        
        # 找出强相关关系
        strong_correlations = {k: v for k, v in correlation_dict.items() if abs(v) > 0.7}
        
        analysis = {
            "correlation_matrix": correlation_matrix.round(3).to_dict(),
            "strong_correlations": strong_correlations,
            "method": method
        }
        
        self.analysis_results["correlation"] = analysis
        return analysis
    
    def trend_analysis(self, value_column: str, date_column: Optional[str] = None) -> Dict[str, Any]:
        """趋势分析"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        if value_column not in self.data.columns:
            raise ValueError(f"列 '{value_column}' 不存在")
        
        # 如果没有指定日期列，使用索引
        if date_column is None:
            data_for_trend = self.data[value_column].dropna()
        else:
            if date_column not in self.data.columns:
                raise ValueError(f"日期列 '{date_column}' 不存在")
            data_for_trend = self.data[[date_column, value_column]].dropna()
            data_for_trend = data_for_trend.set_index(date_column)[value_column]
        
        # 计算趋势指标
        values = data_for_trend.values
        n = len(values)
        
        if n < 2:
            return {"error": "数据点太少，无法进行趋势分析"}
        
        # 线性趋势
        x = np.arange(n)
        slope, intercept = np.polyfit(x, values, 1)
        
        # 移动平均
        window_size = min(5, n // 2)
        if window_size > 1:
            moving_avg = data_for_trend.rolling(window=window_size).mean()
        else:
            moving_avg = data_for_trend
        
        analysis = {
            "趋势斜率": round(slope, 4),
            "趋势方向": "上升" if slope > 0 else "下降" if slope < 0 else "平稳",
            "R平方": round(np.corrcoef(x, values)[0, 1] ** 2, 4),
            "数据点数": n,
            "起始值": round(float(values[0]), 2),
            "结束值": round(float(values[-1]), 2),
            "总变化": round(float(values[-1] - values[0]), 2),
            "变化率": round(float((values[-1] - values[0]) / values[0] * 100), 2) if values[0] != 0 else None,
        }
        
        self.analysis_results["trend"] = analysis
        return analysis

class DataVisualizer:
    """数据可视化器类"""
    
    def __init__(self, data_processor: DataProcessor):
        self.processor = data_processor
        self.figures = []
    
    @property
    def data(self) -> pd.DataFrame:
        """获取数据"""
        return self.processor.data
    
    def create_histogram(self, column: str, bins: int = 30, title: Optional[str] = None) -> go.Figure:
        """创建直方图"""
        if self.data is None or column not in self.data.columns:
            raise ValueError(f"无效的数据或列: {column}")
        
        fig = px.histogram(
            self.data, 
            x=column, 
            nbins=bins,
            title=title or f"{column} 分布直方图"
        )
        
        self.figures.append(fig)
        return fig
    
    def create_scatter_plot(self, x_column: str, y_column: str, 
                          color_column: Optional[str] = None,
                          title: Optional[str] = None) -> go.Figure:
        """创建散点图"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        required_columns = [x_column, y_column]
        if color_column:
            required_columns.append(color_column)
        
        for col in required_columns:
            if col not in self.data.columns:
                raise ValueError(f"列 '{col}' 不存在")
        
        fig = px.scatter(
            self.data,
            x=x_column,
            y=y_column,
            color=color_column,
            title=title or f"{x_column} vs {y_column} 散点图"
        )
        
        self.figures.append(fig)
        return fig
    
    def create_line_chart(self, x_column: str, y_column: str,
                         title: Optional[str] = None) -> go.Figure:
        """创建折线图"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        for col in [x_column, y_column]:
            if col not in self.data.columns:
                raise ValueError(f"列 '{col}' 不存在")
        
        fig = px.line(
            self.data,
            x=x_column,
            y=y_column,
            title=title or f"{y_column} 趋势图"
        )
        
        self.figures.append(fig)
        return fig
    
    def create_box_plot(self, column: str, group_by: Optional[str] = None,
                       title: Optional[str] = None) -> go.Figure:
        """创建箱线图"""
        if self.data is None or column not in self.data.columns:
            raise ValueError(f"无效的数据或列: {column}")
        
        fig = px.box(
            self.data,
            y=column,
            x=group_by,
            title=title or f"{column} 箱线图"
        )
        
        self.figures.append(fig)
        return fig
    
    def create_correlation_heatmap(self, columns: Optional[List[str]] = None,
                                 title: Optional[str] = None) -> go.Figure:
        """创建相关性热力图"""
        if self.data is None:
            raise ValueError("没有加载数据")
        
        if columns is None:
            numeric_columns = self.data.select_dtypes(include=[np.number]).columns.tolist()
        else:
            numeric_columns = [col for col in columns if col in self.data.columns 
                             and pd.api.types.is_numeric_dtype(self.data[col])]
        
        if len(numeric_columns) < 2:
            raise ValueError("至少需要2个数值型列")
        
        correlation_matrix = self.data[numeric_columns].corr()
        
        fig = px.imshow(
            correlation_matrix,
            title=title or "相关性热力图",
            color_continuous_scale="RdBu",
            aspect="auto"
        )
        
        self.figures.append(fig)
        return fig
    
    def save_figures(self, output_dir: Union[str, Path], format: str = "html"):
        """保存所有图表"""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        for i, fig in enumerate(self.figures):
            filename = f"chart_{i+1}.{format}"
            filepath = output_path / filename
            
            if format == "html":
                fig.write_html(str(filepath))
            elif format == "png":
                fig.write_image(str(filepath))
            elif format == "pdf":
                fig.write_image(str(filepath))
            else:
                raise ValueError(f"不支持的格式: {format}")
        
        logger.info(f"图表保存完成: {len(self.figures)} 个文件到 {output_path}")

def create_analysis_pipeline(data: Union[pd.DataFrame, Dict, List], 
                           source: str = "unknown") -> Tuple[DataProcessor, DataAnalyzer, DataVisualizer]:
    """创建完整的数据分析流水线"""
    processor = DataProcessor()
    processor.load_data(data, source)
    
    analyzer = DataAnalyzer(processor)
    visualizer = DataVisualizer(processor)
    
    return processor, analyzer, visualizer
