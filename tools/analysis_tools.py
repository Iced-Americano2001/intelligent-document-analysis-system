"""
数据分析相关工具
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import json

from .base_tool import BaseTool, register_tool
from mcp_services.models import ToolParameter, ToolParameterType


@register_tool
class DataAnalysisTool(BaseTool):
    """数据分析工具"""
    
    def get_name(self) -> str:
        return "data_analysis"
    
    def get_description(self) -> str:
        return "对结构化数据进行分析，生成统计信息和洞察"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "data": ToolParameter(
                type=ToolParameterType.STRING,
                description="JSON格式的数据或CSV文件路径",
                required=True
            ),
            "analysis_type": ToolParameter(
                type=ToolParameterType.STRING,
                description="分析类型",
                enum=["summary", "correlation", "trend", "comprehensive"],
                default="comprehensive"
            ),
            "data_format": ToolParameter(
                type=ToolParameterType.STRING,
                description="数据格式",
                enum=["json", "csv", "auto"],
                default="auto"
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["data"]
    
    async def execute(self, data: str, analysis_type: str = "comprehensive", 
                     data_format: str = "auto") -> Dict[str, Any]:
        """执行数据分析"""
        try:
            # 解析数据
            df = await self._parse_data(data, data_format)
            
            result = {
                "analysis_type": analysis_type,
                "data_shape": df.shape,
                "columns": list(df.columns),
                "data_types": df.dtypes.to_dict()
            }
            
            # 基础统计分析
            if analysis_type in ["summary", "comprehensive"]:
                result["summary"] = await self._generate_summary(df)
            
            # 相关性分析
            if analysis_type in ["correlation", "comprehensive"]:
                result["correlation"] = await self._generate_correlation(df)
            
            # 趋势分析
            if analysis_type in ["trend", "comprehensive"]:
                result["trend"] = await self._generate_trend(df)
            
            # 生成AI洞察
            if analysis_type == "comprehensive":
                from utils.llm_utils import llm_manager
                
                insights_prompt = f"""基于以下数据分析结果，请提供3-5个关键洞察：

数据概况：{df.shape[0]}行，{df.shape[1]}列
列名：{list(df.columns)}
数据类型：{df.dtypes.to_dict()}

统计摘要：{result.get('summary', {})}

请提供简洁明了的分析洞察："""

                insights_response = await llm_manager.generate_completion(insights_prompt, max_tokens=800)
                if insights_response.get("success"):
                    result["ai_insights"] = insights_response.get("response", "").strip()
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    async def _parse_data(self, data: str, data_format: str) -> pd.DataFrame:
        """解析输入数据"""
        if data_format == "auto":
            # 自动判断数据格式
            if data.strip().startswith(('[', '{')):
                data_format = "json"
            elif data.endswith('.csv'):
                data_format = "csv"
            else:
                try:
                    json.loads(data)
                    data_format = "json"
                except:
                    data_format = "csv"
        
        if data_format == "json":
            # 解析JSON数据
            try:
                json_data = json.loads(data)
                if isinstance(json_data, list):
                    df = pd.DataFrame(json_data)
                elif isinstance(json_data, dict):
                    df = pd.DataFrame([json_data])
                else:
                    raise ValueError("JSON数据必须是对象或对象数组")
            except json.JSONDecodeError:
                raise ValueError("无效的JSON格式")
        
        elif data_format == "csv":
            # 读取CSV文件或解析CSV字符串
            if data.endswith('.csv'):
                df = pd.read_csv(data)
            else:
                from io import StringIO
                df = pd.read_csv(StringIO(data))
        
        else:
            raise ValueError(f"不支持的数据格式: {data_format}")
        
        return df
    
    async def _generate_summary(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成数据摘要"""
        summary = {}
        
        # 数值型列的统计信息
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            numeric_summary = df[numeric_cols].describe()
            summary["numeric_summary"] = {
                col: {
                    "count": int(numeric_summary.loc['count', col]),
                    "mean": float(numeric_summary.loc['mean', col]),
                    "std": float(numeric_summary.loc['std', col]),
                    "min": float(numeric_summary.loc['min', col]),
                    "max": float(numeric_summary.loc['max', col]),
                    "25%": float(numeric_summary.loc['25%', col]),
                    "50%": float(numeric_summary.loc['50%', col]),
                    "75%": float(numeric_summary.loc['75%', col])
                }
                for col in numeric_cols
            }
        
        # 分类型列的统计信息
        categorical_cols = df.select_dtypes(include=['object']).columns
        if len(categorical_cols) > 0:
            summary["categorical_summary"] = {}
            for col in categorical_cols:
                value_counts = df[col].value_counts().head(10)
                summary["categorical_summary"][col] = {
                    "unique_count": int(df[col].nunique()),
                    "top_values": value_counts.to_dict(),
                    "null_count": int(df[col].isnull().sum())
                }
        
        # 缺失值统计
        missing_values = df.isnull().sum()
        if missing_values.sum() > 0:
            summary["missing_values"] = {
                col: int(count) for col, count in missing_values.items() if count > 0
            }
        
        return summary
    
    async def _generate_correlation(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成相关性分析"""
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) < 2:
            return {"error": "至少需要2个数值型列进行相关性分析"}
        
        correlation_matrix = df[numeric_cols].corr()
        
        # 找出强相关关系
        strong_correlations = []
        for i in range(len(correlation_matrix.columns)):
            for j in range(i+1, len(correlation_matrix.columns)):
                corr_value = correlation_matrix.iloc[i, j]
                if abs(corr_value) > 0.7:  # 强相关阈值
                    strong_correlations.append({
                        "variable1": correlation_matrix.columns[i],
                        "variable2": correlation_matrix.columns[j],
                        "correlation": float(corr_value),
                        "strength": "强正相关" if corr_value > 0.7 else "强负相关"
                    })
        
        return {
            "correlation_matrix": correlation_matrix.round(3).to_dict(),
            "strong_correlations": strong_correlations,
            "analysis_note": f"分析了{len(numeric_cols)}个数值型变量之间的相关性"
        }
    
    async def _generate_trend(self, df: pd.DataFrame) -> Dict[str, Any]:
        """生成趋势分析"""
        numeric_cols = df.select_dtypes(include=['number']).columns
        
        if len(numeric_cols) == 0:
            return {"error": "没有数值型列进行趋势分析"}
        
        trends = {}
        
        for col in numeric_cols:
            series = df[col].dropna()
            if len(series) < 3:
                continue
                
            # 计算简单的趋势指标
            values = series.values
            n = len(values)
            
            # 线性趋势斜率
            import numpy as np
            x = np.arange(n)
            slope = np.polyfit(x, values, 1)[0]
            
            # 变化率
            start_value = values[0]
            end_value = values[-1]
            change_rate = (end_value - start_value) / start_value * 100 if start_value != 0 else 0
            
            # 波动性
            volatility = float(series.std())
            
            trends[col] = {
                "slope": float(slope),
                "trend_direction": "上升" if slope > 0 else "下降" if slope < 0 else "平稳",
                "change_rate_percent": round(change_rate, 2),
                "volatility": round(volatility, 3),
                "start_value": float(start_value),
                "end_value": float(end_value)
            }
        
        return {
            "trends": trends,
            "analysis_note": f"分析了{len(trends)}个数值型变量的趋势"
        }


@register_tool
class StatisticalTestTool(BaseTool):
    """统计检验工具"""
    
    def get_name(self) -> str:
        return "statistical_test"
    
    def get_description(self) -> str:
        return "执行基本的统计检验，如t检验、卡方检验等"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "test_type": ToolParameter(
                type=ToolParameterType.STRING,
                description="统计检验类型",
                enum=["t_test", "chi_square", "normality", "correlation"],
                required=True
            ),
            "data1": ToolParameter(
                type=ToolParameterType.STRING,
                description="第一组数据（JSON数组格式）",
                required=True
            ),
            "data2": ToolParameter(
                type=ToolParameterType.STRING,
                description="第二组数据（JSON数组格式，某些检验需要）",
                required=False
            ),
            "alpha": ToolParameter(
                type=ToolParameterType.NUMBER,
                description="显著性水平",
                default=0.05
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["test_type", "data1"]
    
    async def execute(self, test_type: str, data1: str, data2: str = None, 
                     alpha: float = 0.05) -> Dict[str, Any]:
        """执行统计检验"""
        try:
            # 解析数据
            import json
            import numpy as np
            from scipy import stats
            
            array1 = np.array(json.loads(data1))
            array2 = np.array(json.loads(data2)) if data2 else None
            
            result = {
                "test_type": test_type,
                "alpha": alpha,
                "sample1_size": len(array1),
                "sample2_size": len(array2) if array2 is not None else 0
            }
            
            if test_type == "t_test":
                if array2 is None:
                    # 单样本t检验
                    statistic, p_value = stats.ttest_1samp(array1, 0)
                    test_name = "单样本t检验"
                else:
                    # 双样本t检验
                    statistic, p_value = stats.ttest_ind(array1, array2)
                    test_name = "独立样本t检验"
                
                result.update({
                    "test_name": test_name,
                    "statistic": float(statistic),
                    "p_value": float(p_value),
                    "significant": p_value < alpha,
                    "interpretation": "拒绝原假设" if p_value < alpha else "接受原假设"
                })
            
            elif test_type == "normality":
                # 正态性检验
                statistic, p_value = stats.shapiro(array1)
                
                result.update({
                    "test_name": "Shapiro-Wilk正态性检验",
                    "statistic": float(statistic),
                    "p_value": float(p_value),
                    "is_normal": p_value > alpha,
                    "interpretation": "数据符合正态分布" if p_value > alpha else "数据不符合正态分布"
                })
            
            elif test_type == "correlation":
                if array2 is None:
                    raise ValueError("相关性检验需要两组数据")
                
                correlation, p_value = stats.pearsonr(array1, array2)
                
                result.update({
                    "test_name": "Pearson相关性检验",
                    "correlation": float(correlation),
                    "p_value": float(p_value),
                    "significant": p_value < alpha,
                    "correlation_strength": self._interpret_correlation(correlation),
                    "interpretation": "相关性显著" if p_value < alpha else "相关性不显著"
                })
            
            else:
                raise ValueError(f"不支持的检验类型: {test_type}")
            
            return result
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _interpret_correlation(self, correlation: float) -> str:
        """解释相关性强度"""
        abs_corr = abs(correlation)
        if abs_corr < 0.3:
            return "弱相关"
        elif abs_corr < 0.7:
            return "中等相关"
        else:
            return "强相关"


@register_tool
class DataVisualizationTool(BaseTool):
    """数据可视化工具"""
    
    def get_name(self) -> str:
        return "data_visualization"
    
    def get_description(self) -> str:
        return "生成数据可视化图表的配置和建议"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "data": ToolParameter(
                type=ToolParameterType.STRING,
                description="JSON格式的数据",
                required=True
            ),
            "chart_type": ToolParameter(
                type=ToolParameterType.STRING,
                description="图表类型",
                enum=["auto", "bar", "line", "scatter", "histogram", "box", "heatmap"],
                default="auto"
            ),
            "x_column": ToolParameter(
                type=ToolParameterType.STRING,
                description="X轴列名",
                required=False
            ),
            "y_column": ToolParameter(
                type=ToolParameterType.STRING,
                description="Y轴列名",
                required=False
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["data"]
    
    async def execute(self, data: str, chart_type: str = "auto", 
                     x_column: str = None, y_column: str = None) -> Dict[str, Any]:
        """生成可视化建议"""
        try:
            # 解析数据
            import json
            json_data = json.loads(data)
            df = pd.DataFrame(json_data)
            
            recommendations = []
            
            # 自动推荐图表类型
            if chart_type == "auto":
                recommendations.extend(self._auto_recommend_charts(df))
            else:
                config = self._generate_chart_config(df, chart_type, x_column, y_column)
                if config:
                    recommendations.append(config)
            
            return {
                "data_shape": df.shape,
                "columns": list(df.columns),
                "data_types": df.dtypes.to_dict(),
                "chart_recommendations": recommendations,
                "total_recommendations": len(recommendations)
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _auto_recommend_charts(self, df: pd.DataFrame) -> List[Dict[str, Any]]:
        """自动推荐图表"""
        recommendations = []
        
        numeric_cols = df.select_dtypes(include=['number']).columns
        categorical_cols = df.select_dtypes(include=['object']).columns
        
        # 直方图推荐（数值型列）
        for col in numeric_cols:
            recommendations.append({
                "chart_type": "histogram",
                "title": f"{col}的分布",
                "description": f"显示{col}的数据分布情况",
                "config": {
                    "x": col,
                    "bins": 20,
                    "title": f"{col}分布直方图"
                }
            })
        
        # 散点图推荐（两个数值型列）
        if len(numeric_cols) >= 2:
            for i in range(len(numeric_cols)):
                for j in range(i+1, len(numeric_cols)):
                    col1, col2 = numeric_cols[i], numeric_cols[j]
                    recommendations.append({
                        "chart_type": "scatter",
                        "title": f"{col1} vs {col2}",
                        "description": f"显示{col1}和{col2}之间的关系",
                        "config": {
                            "x": col1,
                            "y": col2,
                            "title": f"{col1} vs {col2}散点图"
                        }
                    })
        
        # 条形图推荐（分类型列）
        for col in categorical_cols:
            if df[col].nunique() <= 20:  # 不超过20个类别
                recommendations.append({
                    "chart_type": "bar",
                    "title": f"{col}的分布",
                    "description": f"显示{col}各类别的频次",
                    "config": {
                        "x": col,
                        "title": f"{col}分布条形图"
                    }
                })
        
        # 相关性热力图推荐
        if len(numeric_cols) >= 3:
            recommendations.append({
                "chart_type": "heatmap",
                "title": "数值变量相关性热力图",
                "description": "显示数值型变量之间的相关性",
                "config": {
                    "data": "correlation_matrix",
                    "title": "变量相关性热力图"
                }
            })
        
        return recommendations[:8]  # 最多返回8个推荐
    
    def _generate_chart_config(self, df: pd.DataFrame, chart_type: str, 
                             x_column: str = None, y_column: str = None) -> Optional[Dict[str, Any]]:
        """生成特定图表配置"""
        if x_column and x_column not in df.columns:
            return None
        if y_column and y_column not in df.columns:
            return None
        
        config = {
            "chart_type": chart_type,
            "config": {
                "title": f"{chart_type.title()}图表"
            }
        }
        
        if x_column:
            config["config"]["x"] = x_column
        if y_column:
            config["config"]["y"] = y_column
        
        return config