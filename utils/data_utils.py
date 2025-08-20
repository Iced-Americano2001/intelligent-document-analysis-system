import pandas as pd
from typing import Dict, Any, List, Optional
import plotly.express as px
from scipy import stats

class DataProcessor:
    """数据预处理器"""
    def __init__(self):
        self.data: Optional[pd.DataFrame] = None
        self.source: str = "unknown"

    def load_data(self, data: Any, source: str = "unknown"):
        if isinstance(data, pd.DataFrame):
            self.data = data.copy()
        elif isinstance(data, list) and all(isinstance(i, dict) for i in data):
            self.data = pd.DataFrame(data)
        else:
            raise ValueError("不支持的数据格式。请提供Pandas DataFrame或字典列表。")
        self.source = source

    def clean_data(self):
        if self.data is None: return
        # 自动推断数据类型以优化内存和分析
        self.data = self.data.convert_dtypes()
        # 简单处理：用前向填充处理缺失值（可根据策略调整）
        self.data.fillna(method='ffill', inplace=True)
        self.data.fillna(method='bfill', inplace=True)

    def get_summary(self) -> Dict[str, Any]:
        """获取增强版数据摘要，包括对类别列的分析"""
        if self.data is None: return {}
        
        summary = {
            "基本信息": {
                "行数": len(self.data),
                "列数": len(self.data.columns),
                "数据源": self.source,
                "内存占用": f"{self.data.memory_usage(deep=True).sum() / 1024**2:.2f} MB"
            },
            "列信息": {},
            "统计信息": self.data.describe().to_dict()
        }
        
        for col in self.data.columns:
            col_info = {
                "数据类型": str(self.data[col].dtype),
                "缺失值数量": int(self.data[col].isnull().sum()),
                "缺失率": f"{self.data[col].isnull().mean():.2%}",
                "唯一值数量": self.data[col].nunique()
            }
            # 对类别/对象类型列进行额外分析
            if self.data[col].dtype in ['object', 'category', 'string']:
                top_value = self.data[col].mode()
                if not top_value.empty:
                    col_info["最常见值"] = top_value[0]
            summary["列信息"][col] = col_info
            
        return summary

class DataAnalyzer:
    """数据分析器"""
    def __init__(self, processor: DataProcessor):
        if processor.data is None:
            raise ValueError("DataProcessor中的数据为空")
        self.processor = processor

    def descriptive_analysis(self) -> Dict[str, Any]:
        return self.processor.data.describe().to_dict()

    def correlation_analysis(self) -> Dict[str, Any]:
        numeric_df = self.processor.data.select_dtypes(include=['number'])
        corr_matrix = numeric_df.corr()
        
        # 找出强相关对
        strong_correlations = {}
        for i in range(len(corr_matrix.columns)):
            for j in range(i):
                if abs(corr_matrix.iloc[i, j]) > 0.7:
                    col1, col2 = corr_matrix.columns[i], corr_matrix.columns[j]
                    strong_correlations[f"{col1} & {col2}"] = corr_matrix.iloc[i, j]
        
        return {"correlation_matrix": corr_matrix.to_dict(), "strong_correlations": strong_correlations}

    def trend_analysis(self, target_column: str, time_column: Optional[str] = None) -> Dict[str, Any]:
        """执行更精确的趋势分析"""
        df = self.processor.data.copy()
        
        if target_column not in df.columns or not pd.api.types.is_numeric_dtype(df[target_column]):
            return {"错误": f"目标列 '{target_column}' 不是数值类型或不存在"}
        
        x_axis = pd.Series(range(len(df)))
        if time_column and time_column in df.columns:
            try:
                # 尝试将时间列转换为数值（例如，时间戳）
                x_axis = pd.to_datetime(df[time_column]).astype('int64') // 10**9
            except Exception:
                pass # 如果转换失败，则回退到使用索引

        slope, intercept, r_value, p_value, std_err = stats.linregress(x_axis, df[target_column])
        
        direction = "趋势不明显"
        if p_value < 0.05: # 统计上显著
            if slope > 0: direction = "显著上升趋势"
            elif slope < 0: direction = "显著下降趋势"
            
        return {
            "分析列": target_column,
            "时间轴": time_column or "数据索引",
            "趋势方向": direction,
            "趋势斜率": f"{slope:.4f}",
            "R平方值": f"{r_value**2:.4f}"
        }

class DataVisualizer:
    """数据可视化工具"""
    def __init__(self, data: pd.DataFrame):
        self.data = data
    
    def get_plottable_columns(self, dtype: str, max_count: int = 5) -> List[str]:
        """获取适合绘图的列名"""
        if dtype == 'numeric':
            return self.data.select_dtypes(include=['number']).columns.tolist()[:max_count]
        elif dtype == 'categorical':
            return self.data.select_dtypes(include=['object', 'category']).columns.tolist()[:max_count]
        return []

    def generate_distribution_chart(self, column: str):
        fig = px.histogram(self.data, x=column, title=f"'{column}' 的数值分布直方图", template="plotly_white")
        return fig

    def generate_correlation_heatmap(self):
        numeric_df = self.data.select_dtypes(include=['number'])
        corr_matrix = numeric_df.corr()
        fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", title="数值变量相关性热力图", template="plotly_white")
        return fig
    
    def generate_trend_chart(self, target_column: str, time_column: Optional[str] = None):
        x = time_column if time_column and time_column in self.data.columns else self.data.index
        fig = px.scatter(self.data, x=x, y=target_column, trendline="ols",
                         title=f"'{target_column}' 趋势分析", template="plotly_white",
                         labels={"x": time_column or "时间/索引", "y": target_column})
        fig.update_traces(trendline_color="red")
        return fig