"""
智能图表生成器
支持多种图表类型和自动推荐
"""
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
import statsmodels.api as sm
from statsmodels.tsa.seasonal import seasonal_decompose
from statsmodels.tsa.stattools import adfuller
from scipy import stats
from typing import Dict, Any, List, Optional, Tuple
import logging

logger = logging.getLogger(__name__)

class ChartGenerator:
    """智能图表生成器"""
    
    def __init__(self, data: pd.DataFrame):
        self.data = data
        self.numeric_cols = data.select_dtypes(include=['number']).columns.tolist()
        self.categorical_cols = data.select_dtypes(include=['object', 'category']).columns.tolist()
        self.datetime_cols = data.select_dtypes(include=['datetime64']).columns.tolist()
        
    def generate_charts_for_analysis(self, analysis_text: str) -> Dict[str, Any]:
        """基于分析文本生成相应的图表"""
        charts = {}
        
        # 根据分析内容智能推荐图表
        analysis_lower = analysis_text.lower()
        
        # 1. 趋势分析图表
        if any(keyword in analysis_lower for keyword in ['趋势', '变化', '增长', '下降', '时间', 'trend']):
            trend_charts = self._generate_trend_charts(analysis_text)
            charts.update(trend_charts)
        
        # 2. 分布分析图表
        if any(keyword in analysis_lower for keyword in ['分布', '直方图', '频率', 'distribution']):
            dist_charts = self._generate_distribution_charts()
            charts.update(dist_charts)
        
        # 3. 相关性分析图表
        if any(keyword in analysis_lower for keyword in ['相关', '关系', '关联', 'correlation']):
            corr_charts = self._generate_correlation_charts()
            charts.update(corr_charts)
        
        # 4. 对比分析图表
        if any(keyword in analysis_lower for keyword in ['对比', '比较', '差异', 'compare']):
            comp_charts = self._generate_comparison_charts()
            charts.update(comp_charts)
        
        # 5. 高级统计分析图表
        if any(keyword in analysis_lower for keyword in ['回归', '正态', '统计', 'regression', 'normal', 'statistical']):
            stat_charts = self._generate_advanced_statistical_charts()
            charts.update(stat_charts)
        
        # 6. 如果没有特定关键词，生成综合图表
        if not charts:
            charts = self._generate_comprehensive_charts()
        
        return charts
    
    def _generate_trend_charts(self, analysis_text: str) -> Dict[str, Any]:
        """生成趋势图表"""
        charts = {}
        
        # 查找可能的时间列
        time_col = None
        for col in self.data.columns:
            if any(keyword in col.lower() for keyword in ['time', 'date', '时间', '日期', 'year', '年']):
                time_col = col
                break
        
        # 如果没有时间列，使用索引作为时间轴
        if time_col is None:
            x_axis = self.data.index
            x_label = "数据点索引"
        else:
            x_axis = self.data[time_col]
            x_label = time_col
        
        # 为每个数值列生成趋势图
        for col in self.numeric_cols[:3]:  # 最多3个趋势图
            fig = go.Figure()
            
            # 添加原始数据线
            fig.add_trace(go.Scatter(
                x=x_axis,
                y=self.data[col],
                mode='lines+markers',
                name=f'{col}',
                line=dict(width=2)
            ))
            
            # 添加趋势线
            if len(self.data) > 2:
                z = np.polyfit(range(len(self.data)), self.data[col].ffill().bfill(), 1)
                trend_line = np.poly1d(z)(range(len(self.data)))
                fig.add_trace(go.Scatter(
                    x=x_axis,
                    y=trend_line,
                    mode='lines',
                    name=f'{col} 趋势线',
                    line=dict(dash='dash', color='red', width=2)
                ))
            
            # 添加移动平均线（如果数据足够）
            if len(self.data) >= 7:
                moving_avg = self.data[col].rolling(window=min(7, len(self.data)//3)).mean()
                fig.add_trace(go.Scatter(
                    x=x_axis,
                    y=moving_avg,
                    mode='lines',
                    name=f'{col} 移动平均',
                    line=dict(dash='dot', color='green', width=1.5)
                ))
            
            # 如果是时间序列且数据足够，添加季节性分解
            if time_col and len(self.data) >= 24:
                try:
                    # 尝试进行季节性分解
                    ts_data = self.data.set_index(time_col)[col].dropna()
                    if len(ts_data) >= 24:
                        decomposition = seasonal_decompose(ts_data, model='additive', period=min(12, len(ts_data)//2))
                        
                        # 添加趋势分量
                        fig.add_trace(go.Scatter(
                            x=ts_data.index,
                            y=decomposition.trend,
                            mode='lines',
                            name=f'{col} 季节性趋势',
                            line=dict(color='orange', width=2)
                        ))
                except Exception as e:
                    logger.warning(f"季节性分解失败: {e}")
            
            fig.update_layout(
                title=f'{col} 趋势分析图',
                xaxis_title=x_label,
                yaxis_title=col,
                template='plotly_white',
                hovermode='x unified'
            )
            
            charts[f'trend_{col}'] = fig
        
        return charts
    
    def _generate_advanced_statistical_charts(self) -> Dict[str, Any]:
        """生成高级统计分析图表"""
        charts = {}
        
        if len(self.numeric_cols) >= 1:
            # 正态性检验图表
            for col in self.numeric_cols[:2]:
                data_clean = self.data[col].dropna()
                if len(data_clean) > 3:
                    # Q-Q图
                    fig = go.Figure()
                    
                    # 计算理论分位数和实际分位数
                    sorted_data = np.sort(data_clean)
                    theoretical_quantiles = stats.norm.ppf(np.linspace(0.01, 0.99, len(sorted_data)))
                    
                    fig.add_trace(go.Scatter(
                        x=theoretical_quantiles,
                        y=sorted_data,
                        mode='markers',
                        name='数据点',
                        marker=dict(color='blue', size=6)
                    ))
                    
                    # 添加理论线
                    fig.add_trace(go.Scatter(
                        x=[theoretical_quantiles.min(), theoretical_quantiles.max()],
                        y=[sorted_data.min(), sorted_data.max()],
                        mode='lines',
                        name='理论正态线',
                        line=dict(color='red', dash='dash')
                    ))
                    
                    # Shapiro-Wilk正态性检验
                    try:
                        stat, p_value = stats.shapiro(data_clean)
                        is_normal = "正态分布" if p_value > 0.05 else "非正态分布"
                        fig.update_layout(
                            title=f'{col} Q-Q图 (正态性检验)<br><sub>Shapiro-Wilk: p={p_value:.4f}, {is_normal}</sub>',
                            xaxis_title='理论分位数',
                            yaxis_title='样本分位数',
                            template='plotly_white'
                        )
                    except Exception:
                        fig.update_layout(
                            title=f'{col} Q-Q图 (正态性检验)',
                            xaxis_title='理论分位数',
                            yaxis_title='样本分位数',
                            template='plotly_white'
                        )
                    
                    charts[f'qq_plot_{col}'] = fig
        
        # 回归分析图表
        if len(self.numeric_cols) >= 2:
            col1, col2 = self.numeric_cols[0], self.numeric_cols[1]
            
            # 创建回归分析图
            fig = go.Figure()
            
            # 散点图
            fig.add_trace(go.Scatter(
                x=self.data[col1],
                y=self.data[col2],
                mode='markers',
                name='数据点',
                marker=dict(color='blue', size=8, opacity=0.6)
            ))
            
            # 线性回归
            try:
                # 清理数据
                clean_data = self.data[[col1, col2]].dropna()
                if len(clean_data) > 2:
                    x = clean_data[col1]
                    y = clean_data[col2]
                    
                    # 使用statsmodels进行回归
                    X = sm.add_constant(x)
                    model = sm.OLS(y, X).fit()
                    
                    # 预测线
                    x_pred = np.linspace(x.min(), x.max(), 100)
                    X_pred = sm.add_constant(x_pred)
                    y_pred = model.predict(X_pred)
                    
                    fig.add_trace(go.Scatter(
                        x=x_pred,
                        y=y_pred,
                        mode='lines',
                        name='回归线',
                        line=dict(color='red', width=2)
                    ))
                    
                    # 置信区间
                    predictions = model.get_prediction(X_pred)
                    conf_int = predictions.conf_int()
                    
                    fig.add_trace(go.Scatter(
                        x=x_pred,
                        y=conf_int[:, 0],
                        mode='lines',
                        line=dict(width=0),
                        showlegend=False,
                        hoverinfo='skip'
                    ))
                    
                    fig.add_trace(go.Scatter(
                        x=x_pred,
                        y=conf_int[:, 1],
                        mode='lines',
                        fill='tonexty',
                        fillcolor='rgba(255,0,0,0.2)',
                        line=dict(width=0),
                        name='95%置信区间',
                        hoverinfo='skip'
                    ))
                    
                    # 添加统计信息
                    r_squared = model.rsquared
                    p_value = model.f_pvalue
                    
                    fig.update_layout(
                        title=f'{col1} vs {col2} 回归分析<br><sub>R² = {r_squared:.4f}, p = {p_value:.4f}</sub>',
                        xaxis_title=col1,
                        yaxis_title=col2,
                        template='plotly_white'
                    )
                    
                    charts[f'regression_{col1}_{col2}'] = fig
            
            except Exception as e:
                logger.warning(f"回归分析失败: {e}")
        
        return charts
    
    def _generate_distribution_charts(self) -> Dict[str, Any]:
        """生成分布图表"""
        charts = {}
        
        for col in self.numeric_cols[:3]:  # 最多3个分布图
            # 创建子图：直方图和箱线图
            fig = make_subplots(
                rows=1, cols=2,
                subplot_titles=[f'{col} 直方图', f'{col} 箱线图'],
                specs=[[{"secondary_y": False}, {"secondary_y": False}]]
            )
            
            # 直方图
            fig.add_trace(
                go.Histogram(x=self.data[col], name=col, nbinsx=20),
                row=1, col=1
            )
            
            # 箱线图
            fig.add_trace(
                go.Box(y=self.data[col], name=col, boxpoints='outliers'),
                row=1, col=2
            )
            
            fig.update_layout(
                title=f'{col} 分布分析',
                template='plotly_white',
                showlegend=False
            )
            
            charts[f'distribution_{col}'] = fig
        
        return charts
    
    def _generate_correlation_charts(self) -> Dict[str, Any]:
        """生成相关性图表"""
        charts = {}
        
        if len(self.numeric_cols) >= 2:
            # 相关性热力图
            corr_matrix = self.data[self.numeric_cols].corr()
            
            fig = go.Figure(data=go.Heatmap(
                z=corr_matrix.values,
                x=corr_matrix.columns,
                y=corr_matrix.columns,
                colorscale='RdBu',
                zmid=0,
                text=corr_matrix.round(2).values,
                texttemplate="%{text}",
                textfont={"size": 10},
                hoverongaps=False
            ))
            
            fig.update_layout(
                title='变量相关性热力图',
                template='plotly_white'
            )
            
            charts['correlation_heatmap'] = fig
            
            # 散点图矩阵（选择前4个变量）
            if len(self.numeric_cols) >= 2:
                selected_cols = self.numeric_cols[:4]
                fig = px.scatter_matrix(
                    self.data[selected_cols],
                    title='变量散点图矩阵',
                    template='plotly_white'
                )
                charts['scatter_matrix'] = fig
        
        return charts
    
    def _generate_comparison_charts(self) -> Dict[str, Any]:
        """生成对比图表"""
        charts = {}
        
        # 如果有分类列，生成分组对比图
        if self.categorical_cols and self.numeric_cols:
            cat_col = self.categorical_cols[0]
            num_col = self.numeric_cols[0]
            
            # 确保分类不超过10个
            if self.data[cat_col].nunique() <= 10:
                # 分组箱线图
                fig = px.box(
                    self.data, 
                    x=cat_col, 
                    y=num_col,
                    title=f'{num_col} 按 {cat_col} 分组对比',
                    template='plotly_white'
                )
                charts[f'comparison_{cat_col}_{num_col}'] = fig
                
                # 分组统计条形图
                grouped_stats = self.data.groupby(cat_col)[num_col].agg(['mean', 'median', 'std']).reset_index()
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=grouped_stats[cat_col],
                    y=grouped_stats['mean'],
                    name='平均值',
                    marker_color='lightblue'
                ))
                fig.add_trace(go.Bar(
                    x=grouped_stats[cat_col],
                    y=grouped_stats['median'],
                    name='中位数',
                    marker_color='orange'
                ))
                
                fig.update_layout(
                    title=f'{num_col} 按 {cat_col} 分组统计',
                    xaxis_title=cat_col,
                    yaxis_title=num_col,
                    template='plotly_white',
                    barmode='group'
                )
                charts[f'grouped_stats_{cat_col}_{num_col}'] = fig
        
        return charts
    
    def _generate_comprehensive_charts(self) -> Dict[str, Any]:
        """生成综合分析图表"""
        charts = {}
        
        # 1. 数据概览
        if self.numeric_cols:
            # 选择前4个数值列
            selected_cols = self.numeric_cols[:4]
            
            # 创建多子图
            rows = 2
            cols = 2
            fig = make_subplots(
                rows=rows, cols=cols,
                subplot_titles=[f'{col} 分布' for col in selected_cols],
                specs=[[{"secondary_y": False} for _ in range(cols)] for _ in range(rows)]
            )
            
            for i, col in enumerate(selected_cols):
                row = i // cols + 1
                col_idx = i % cols + 1
                
                fig.add_trace(
                    go.Histogram(x=self.data[col], name=col, showlegend=False),
                    row=row, col=col_idx
                )
            
            fig.update_layout(
                title='数据分布概览',
                template='plotly_white'
            )
            charts['overview_distributions'] = fig
        
        # 2. 基本统计图
        if len(self.numeric_cols) >= 2:
            # 前两个数值列的散点图
            col1, col2 = self.numeric_cols[0], self.numeric_cols[1]
            fig = px.scatter(
                self.data, 
                x=col1, 
                y=col2,
                title=f'{col1} vs {col2} 散点图',
                template='plotly_white',
                trendline="ols"  # 添加趋势线
            )
            charts[f'scatter_{col1}_{col2}'] = fig
        
        return charts
    
    def generate_chart_from_description(self, description: str, chart_type: str = "auto") -> Optional[go.Figure]:
        """根据描述生成特定图表"""
        try:
            if chart_type == "auto":
                # 根据描述自动选择图表类型
                if "趋势" in description or "时间" in description:
                    return self._create_trend_chart(description)
                elif "分布" in description:
                    return self._create_distribution_chart(description)
                elif "对比" in description or "比较" in description:
                    return self._create_comparison_chart(description)
                else:
                    return self._create_general_chart(description)
            else:
                # 根据指定类型生成图表
                if chart_type == "line":
                    return self._create_line_chart(description)
                elif chart_type == "bar":
                    return self._create_bar_chart(description)
                elif chart_type == "scatter":
                    return self._create_scatter_chart(description)
                elif chart_type == "histogram":
                    return self._create_histogram_chart(description)
                else:
                    return self._create_general_chart(description)
        
        except Exception as e:
            logger.error(f"生成图表失败: {e}")
            return None
    
    def _create_trend_chart(self, description: str) -> go.Figure:
        """创建趋势图"""
        if not self.numeric_cols:
            raise ValueError("没有数值列可用于趋势分析")
        
        # 选择第一个数值列
        y_col = self.numeric_cols[0]
        x_axis = self.data.index
        
        fig = go.Figure()
        fig.add_trace(go.Scatter(
            x=x_axis,
            y=self.data[y_col],
            mode='lines+markers',
            name=y_col,
            line=dict(width=2)
        ))
        
        fig.update_layout(
            title=f'{y_col} 趋势图',
            xaxis_title='时间点',
            yaxis_title=y_col,
            template='plotly_white'
        )
        
        return fig
    
    def _create_distribution_chart(self, description: str) -> go.Figure:
        """创建分布图"""
        if not self.numeric_cols:
            raise ValueError("没有数值列可用于分布分析")
        
        col = self.numeric_cols[0]
        fig = px.histogram(
            self.data, 
            x=col, 
            title=f'{col} 分布直方图',
            template='plotly_white',
            marginal="box"  # 添加边际箱线图
        )
        
        return fig
    
    def _create_comparison_chart(self, description: str) -> go.Figure:
        """创建对比图"""
        if not self.numeric_cols:
            raise ValueError("没有数值列可用于对比分析")
        
        if len(self.numeric_cols) >= 2:
            # 创建多个变量的对比
            cols = self.numeric_cols[:3]  # 最多3个变量
            
            fig = go.Figure()
            for col in cols:
                fig.add_trace(go.Box(
                    y=self.data[col],
                    name=col
                ))
            
            fig.update_layout(
                title='多变量分布对比',
                yaxis_title='数值',
                template='plotly_white'
            )
            
            return fig
        else:
            return self._create_distribution_chart(description)
    
    def _create_general_chart(self, description: str) -> go.Figure:
        """创建通用图表"""
        if not self.numeric_cols:
            raise ValueError("没有可用的数值列")
        
        # 创建简单的线图
        col = self.numeric_cols[0]
        fig = px.line(
            self.data, 
            y=col, 
            title=f'{col} 数据图表',
            template='plotly_white'
        )
        
        return fig
    
    def _create_line_chart(self, description: str) -> go.Figure:
        """创建折线图"""
        return self._create_trend_chart(description)
    
    def _create_bar_chart(self, description: str) -> go.Figure:
        """创建条形图"""
        if self.categorical_cols and self.numeric_cols:
            cat_col = self.categorical_cols[0]
            num_col = self.numeric_cols[0]
            
            # 聚合数据
            grouped = self.data.groupby(cat_col)[num_col].mean().reset_index()
            
            fig = px.bar(
                grouped,
                x=cat_col,
                y=num_col,
                title=f'{num_col} 按 {cat_col} 分组平均值',
                template='plotly_white'
            )
            
            return fig
        else:
            return self._create_distribution_chart(description)
    
    def _create_scatter_chart(self, description: str) -> go.Figure:
        """创建散点图"""
        if len(self.numeric_cols) >= 2:
            col1, col2 = self.numeric_cols[0], self.numeric_cols[1]
            fig = px.scatter(
                self.data,
                x=col1,
                y=col2,
                title=f'{col1} vs {col2} 散点图',
                template='plotly_white',
                trendline="ols"
            )
            return fig
        else:
            return self._create_distribution_chart(description)
    
    def _create_histogram_chart(self, description: str) -> go.Figure:
        """创建直方图"""
        return self._create_distribution_chart(description)


def parse_chart_requests_from_text(text: str) -> List[Dict[str, str]]:
    """从文本中解析图表请求"""
    chart_requests = []
    
    # 定义图表关键词映射
    chart_keywords = {
        'line': ['趋势', '线图', '折线', '时间', '变化'],
        'bar': ['条形', '柱状', '对比', '分组'],
        'scatter': ['散点', '相关', '关系'],
        'histogram': ['直方图', '分布', '频率'],
        'box': ['箱线图', '四分位'],
        'heatmap': ['热力图', '相关性矩阵']
    }
    
    text_lower = text.lower()
    
    for chart_type, keywords in chart_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            chart_requests.append({
                'type': chart_type,
                'description': f'根据分析内容生成{chart_type}图表'
            })
    
    # 如果没有特定图表请求，添加默认的综合分析图表
    if not chart_requests:
        chart_requests.append({
            'type': 'auto',
            'description': '根据数据特征自动生成合适的图表'
        })
    
    return chart_requests
