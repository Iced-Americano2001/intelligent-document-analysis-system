"""
智能图表生成工具
为MCP智能体提供图表生成能力
"""

from typing import Dict, Any, List, Optional
import pandas as pd
import json
import logging
from tools.base_tool import BaseTool, ToolParameter, ToolParameterType, register_tool

logger = logging.getLogger(__name__)

@register_tool
class SmartChartGeneratorTool(BaseTool):
    """智能图表生成工具"""
    
    def get_name(self) -> str:
        return "smart_chart_generator"
    
    def get_description(self) -> str:
        return "基于数据分析结果智能生成适合的图表，支持趋势分析、分布分析、相关性分析等"
    
    def get_parameters(self) -> Dict[str, ToolParameter]:
        return {
            "data": ToolParameter(
                type=ToolParameterType.STRING,
                description="JSON格式的数据",
                required=True
            ),
            "analysis_context": ToolParameter(
                type=ToolParameterType.STRING,
                description="分析上下文和需求，用于智能选择图表类型",
                required=True
            ),
            "chart_preference": ToolParameter(
                type=ToolParameterType.STRING,
                description="图表偏好",
                enum=["auto", "trend", "distribution", "correlation", "comparison"],
                default="auto"
            )
        }
    
    def get_required_parameters(self) -> List[str]:
        return ["data", "analysis_context"]
    
    async def execute(self, data: str, analysis_context: str, 
                     chart_preference: str = "auto") -> Dict[str, Any]:
        """智能生成图表建议"""
        try:
            # 解析数据
            json_data = json.loads(data)
            df = pd.DataFrame(json_data)
            
            # 分析数据特征
            data_features = self._analyze_data_features(df)
            
            # 基于分析上下文选择图表
            chart_recommendations = self._smart_chart_selection(
                df, analysis_context, chart_preference, data_features
            )
            
            # 生成图表描述和代码
            chart_instructions = []
            for rec in chart_recommendations:
                instruction = self._generate_chart_instruction(rec)
                if instruction:
                    chart_instructions.append(instruction)
            
            return {
                "success": True,
                "data_features": data_features,
                "chart_recommendations": chart_recommendations,
                "chart_instructions": chart_instructions,
                "total_charts": len(chart_recommendations),
                "analysis_summary": self._generate_analysis_summary(
                    df, analysis_context, chart_recommendations
                )
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__
            }
    
    def _analyze_data_features(self, df: pd.DataFrame) -> Dict[str, Any]:
        """分析数据特征"""
        numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
        categorical_cols = df.select_dtypes(include=['object', 'category']).columns.tolist()
        datetime_cols = df.select_dtypes(include=['datetime64']).columns.tolist()
        
        features = {
            "shape": df.shape,
            "numeric_columns": numeric_cols,
            "categorical_columns": categorical_cols,
            "datetime_columns": datetime_cols,
            "numeric_count": len(numeric_cols),
            "categorical_count": len(categorical_cols),
            "datetime_count": len(datetime_cols),
            "has_missing_values": df.isnull().sum().sum() > 0,
            "data_range": "small" if df.shape[0] < 100 else "medium" if df.shape[0] < 1000 else "large"
        }
        
        # 检查时间序列特征
        features["likely_time_series"] = (
            len(datetime_cols) > 0 or 
            any(col.lower() in ['time', 'date', '时间', '日期', 'year', '年', 'month', '月'] 
                for col in df.columns)
        )
        
        # 检查相关性
        if len(numeric_cols) >= 2:
            corr_matrix = df[numeric_cols].corr()
            high_corr_pairs = []
            for i in range(len(corr_matrix.columns)):
                for j in range(i+1, len(corr_matrix.columns)):
                    corr_val = abs(corr_matrix.iloc[i, j])
                    if corr_val > 0.7:
                        high_corr_pairs.append((corr_matrix.columns[i], corr_matrix.columns[j], corr_val))
            features["high_correlation_pairs"] = high_corr_pairs
        
        return features
    
    def _smart_chart_selection(self, df: pd.DataFrame, analysis_context: str, 
                              chart_preference: str, data_features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """智能选择图表类型"""
        recommendations = []
        context_lower = analysis_context.lower()
        
        # 根据分析上下文和偏好选择图表
        if chart_preference == "trend" or any(word in context_lower for word in ['趋势', '变化', '时间', '增长', '下降', 'trend', 'change']):
            recommendations.extend(self._generate_trend_charts(df, data_features))
        
        if chart_preference == "distribution" or any(word in context_lower for word in ['分布', '直方图', '概率', 'distribution', 'histogram']):
            recommendations.extend(self._generate_distribution_charts(df, data_features))
        
        if chart_preference == "correlation" or any(word in context_lower for word in ['相关', '关系', '关联', 'correlation', 'relationship']):
            recommendations.extend(self._generate_correlation_charts(df, data_features))
        
        if chart_preference == "comparison" or any(word in context_lower for word in ['对比', '比较', '差异', 'compare', 'comparison']):
            recommendations.extend(self._generate_comparison_charts(df, data_features))
        
        # 如果是auto模式或没有匹配的特定类型，生成综合推荐
        if chart_preference == "auto" or not recommendations:
            recommendations.extend(self._generate_comprehensive_recommendations(df, data_features, context_lower))
        
        # 限制推荐数量并去重
        seen_types = set()
        unique_recommendations = []
        for rec in recommendations:
            rec_key = (rec['chart_type'], rec.get('x_column'), rec.get('y_column'))
            if rec_key not in seen_types:
                seen_types.add(rec_key)
                unique_recommendations.append(rec)
                if len(unique_recommendations) >= 6:  # 最多6个推荐
                    break
        
        return unique_recommendations
    
    def _generate_trend_charts(self, df: pd.DataFrame, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成趋势图表推荐"""
        charts = []
        numeric_cols = features["numeric_columns"]
        
        if numeric_cols:
            # 时间序列图
            time_col = None
            for col in df.columns:
                if any(keyword in col.lower() for keyword in ['time', 'date', '时间', '日期', 'year', '年']):
                    time_col = col
                    break
            
            for col in numeric_cols[:2]:  # 最多2个趋势图
                charts.append({
                    "chart_type": "line",
                    "x_column": time_col or "index",
                    "y_column": col,
                    "title": f"{col} 趋势分析",
                    "description": f"显示 {col} 随时间的变化趋势",
                    "priority": "high" if features["likely_time_series"] else "medium"
                })
        
        return charts
    
    def _generate_distribution_charts(self, df: pd.DataFrame, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成分布图表推荐"""
        charts = []
        numeric_cols = features["numeric_columns"]
        
        for col in numeric_cols[:3]:  # 最多3个分布图
            charts.append({
                "chart_type": "histogram",
                "x_column": col,
                "y_column": None,
                "title": f"{col} 分布分析",
                "description": f"显示 {col} 的数据分布情况",
                "priority": "high"
            })
        
        return charts
    
    def _generate_correlation_charts(self, df: pd.DataFrame, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成相关性图表推荐"""
        charts = []
        numeric_cols = features["numeric_columns"]
        
        if len(numeric_cols) >= 3:
            # 相关性热力图
            charts.append({
                "chart_type": "heatmap",
                "x_column": None,
                "y_column": None,
                "title": "变量相关性热力图",
                "description": "显示所有数值变量之间的相关性",
                "priority": "high"
            })
        
        # 散点图展示高相关性的变量对
        if "high_correlation_pairs" in features:
            for pair in features["high_correlation_pairs"][:2]:  # 最多2个高相关性散点图
                charts.append({
                    "chart_type": "scatter",
                    "x_column": pair[0],
                    "y_column": pair[1],
                    "title": f"{pair[0]} vs {pair[1]} 相关性分析",
                    "description": f"显示 {pair[0]} 和 {pair[1]} 的相关关系 (r={pair[2]:.2f})",
                    "priority": "high"
                })
        
        return charts
    
    def _generate_comparison_charts(self, df: pd.DataFrame, features: Dict[str, Any]) -> List[Dict[str, Any]]:
        """生成对比图表推荐"""
        charts = []
        numeric_cols = features["numeric_columns"]
        categorical_cols = features["categorical_columns"]
        
        # 分组对比
        if categorical_cols and numeric_cols:
            cat_col = categorical_cols[0]
            num_col = numeric_cols[0]
            
            if df[cat_col].nunique() <= 10:  # 类别不超过10个
                charts.append({
                    "chart_type": "box",
                    "x_column": cat_col,
                    "y_column": num_col,
                    "title": f"{num_col} 按 {cat_col} 分组对比",
                    "description": f"比较不同 {cat_col} 类别下 {num_col} 的分布",
                    "priority": "high"
                })
        
        return charts
    
    def _generate_comprehensive_recommendations(self, df: pd.DataFrame, features: Dict[str, Any], context: str) -> List[Dict[str, Any]]:
        """生成综合推荐"""
        charts = []
        
        # 根据数据特征自动推荐
        if features["numeric_count"] >= 1:
            charts.extend(self._generate_distribution_charts(df, features)[:2])
        
        if features["numeric_count"] >= 2:
            charts.extend(self._generate_correlation_charts(df, features)[:2])
        
        if features["likely_time_series"]:
            charts.extend(self._generate_trend_charts(df, features)[:1])
        
        if features["categorical_count"] >= 1 and features["numeric_count"] >= 1:
            charts.extend(self._generate_comparison_charts(df, features)[:1])
        
        return charts
    
    def _generate_chart_instruction(self, recommendation: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """生成图表指令"""
        chart_type = recommendation["chart_type"]
        
        instruction = {
            "type": chart_type,
            "title": recommendation["title"],
            "description": recommendation["description"],
            "priority": recommendation.get("priority", "medium")
        }
        
        if chart_type == "line":
            instruction["code_template"] = f"""
# 生成折线图
import plotly.express as px
fig = px.line(df, x='{recommendation.get("x_column", "index")}', y='{recommendation["y_column"]}', 
              title='{recommendation["title"]}', template='plotly_white', markers=True)
"""
        
        elif chart_type == "histogram":
            instruction["code_template"] = f"""
# 生成直方图
import plotly.express as px
fig = px.histogram(df, x='{recommendation["x_column"]}', title='{recommendation["title"]}', 
                   template='plotly_white', marginal='box')
"""
        
        elif chart_type == "scatter":
            instruction["code_template"] = f"""
# 生成散点图
import plotly.express as px
fig = px.scatter(df, x='{recommendation["x_column"]}', y='{recommendation["y_column"]}', 
                 title='{recommendation["title"]}', template='plotly_white', trendline='ols')
"""
        
        elif chart_type == "heatmap":
            instruction["code_template"] = f"""
# 生成热力图
import plotly.express as px
numeric_cols = df.select_dtypes(include=['number']).columns
corr_matrix = df[numeric_cols].corr()
fig = px.imshow(corr_matrix, text_auto=True, title='{recommendation["title"]}', template='plotly_white')
"""
        
        elif chart_type == "box":
            instruction["code_template"] = f"""
# 生成箱线图
import plotly.express as px
fig = px.box(df, x='{recommendation["x_column"]}', y='{recommendation["y_column"]}', 
             title='{recommendation["title"]}', template='plotly_white')
"""
        
        return instruction
    
    def _generate_analysis_summary(self, df: pd.DataFrame, analysis_context: str, 
                                 recommendations: List[Dict[str, Any]]) -> str:
        """生成分析总结"""
        summary = f"""
智能图表生成分析报告：

数据概况：
- 数据形状：{df.shape[0]}行 × {df.shape[1]}列
- 数值型列：{len(df.select_dtypes(include=['number']).columns)}个
- 分类型列：{len(df.select_dtypes(include=['object']).columns)}个

分析上下文：{analysis_context}

推荐图表：
"""
        
        for i, rec in enumerate(recommendations, 1):
            summary += f"{i}. {rec['chart_type'].upper()}图 - {rec['title']}\n"
            summary += f"   目的：{rec['description']}\n"
            summary += f"   优先级：{rec.get('priority', 'medium')}\n\n"
        
        summary += f"总计推荐 {len(recommendations)} 个图表，覆盖了数据的主要分析维度。"
        
        return summary
