from typing import Dict, Any, List, Optional
import logging
import pandas as pd
from .base_agent import BaseAgent
from config.settings import get_prompt_template
from utils.data_utils import DataProcessor, DataAnalyzer, DataVisualizer

logger = logging.getLogger(__name__)

class AnalysisAgent(BaseAgent):
    """数据分析智能体"""
    
    def __init__(self):
        super().__init__(
            name="Analysis_Agent",
            description="对提取的数据进行专业分析并生成可视化图表的智能体"
        )
        self.add_capability("data_analysis")
        self.add_capability("statistical_analysis")
        self.add_capability("trend_analysis")
        self.add_capability("correlation_analysis")
        self.add_capability("data_visualization") 
        self.max_context_length = 8000
        self.temperature = 0.3

    async def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理数据分析请求"""
        if not isinstance(input_data, dict):
            raise ValueError("输入数据必须是字典格式")
        
        data = input_data.get("data")
        analysis_type = input_data.get("analysis_type", "comprehensive")
        requirements = input_data.get("requirements", "")
        data_source = input_data.get("source", "unknown")
        # 用于趋势分析的特定列
        trend_target_col = input_data.get("trend_target_col")
        trend_time_col = input_data.get("trend_time_col")
        
        if data is None:
            raise ValueError("数据不能为空")
            
        self.add_memory({"type": "analysis_start", "analysis_type": analysis_type})
        
        try:
            processor = DataProcessor()
            processor.load_data(data, source=data_source)
            processor.clean_data()
            
            analyzer = DataAnalyzer(processor)
            visualizer = DataVisualizer(processor.data) # 初始化可视化工具

            analysis_results = {}
            visualizations = {} # 用于存放生成的图表

            # 1. 描述性统计
            if analysis_type in ["comprehensive", "statistical"]:
                analysis_results["descriptive"] = analyzer.descriptive_analysis()
                dist_cols = visualizer.get_plottable_columns('numeric', 3)
                for col in dist_cols:
                    visualizations[f"dist_{col}"] = visualizer.generate_distribution_chart(col)

            # 2. 相关性分析
            if analysis_type in ["comprehensive", "correlation"]:
                analysis_results["correlation"] = analyzer.correlation_analysis()
                visualizations["correlation_heatmap"] = visualizer.generate_correlation_heatmap()

            # 3. 趋势分析 
            if analysis_type in ["comprehensive", "trend"] and trend_target_col:
                analysis_results["trend"] = analyzer.trend_analysis(
                    target_column=trend_target_col, 
                    time_column=trend_time_col
                )
                visualizations["trend_chart"] = visualizer.generate_trend_chart(
                    target_column=trend_target_col, 
                    time_column=trend_time_col
                )

            data_summary = processor.get_summary()
            
            ai_insights = await self._generate_ai_insights(data_summary, analysis_results, requirements)
            
            result = {
                "analysis_type": analysis_type,
                "data_source": data_source,
                "data_summary": data_summary,
                "statistical_analysis": analysis_results,
                "ai_insights": ai_insights,
                "visualizations": visualizations, # 返回真实的图表对象
                "recommendations": await self._generate_recommendations(analysis_results, ai_insights)
            }
            
            self.add_memory({"type": "analysis_success", "insights_length": len(ai_insights)})
            return result
            
        except Exception as e:
            logger.error(f"数据分析失败: {e}", exc_info=True)
            self.add_memory({"type": "analysis_error", "error": str(e)})
            raise

    async def _generate_ai_insights(self, data_summary: Dict[str, Any], 
                                  analysis_results: Dict[str, Any], 
                                  requirements: str) -> str:
        """生成AI分析洞察"""
        try:
            # 构建分析提示词
            prompt = self._build_analysis_prompt(data_summary, analysis_results, requirements)
            
            # 获取AI分析
            insights = await self._get_llm_response(prompt, max_tokens=2000)
            
            return insights
            
        except Exception as e:
            logger.error(f"AI洞察生成失败: {e}")
            return f"AI洞察生成失败: {str(e)}"
    
    def _build_analysis_prompt(self, data_summary: Dict[str, Any], 
                             analysis_results: Dict[str, Any], 
                             requirements: str) -> str:
        """构建分析提示词"""
        # 获取基础模板
        base_template = get_prompt_template("data_analysis")
        
        # 格式化数据摘要
        data_summary_text = self._format_data_summary(data_summary)
        
        # 格式化分析结果
        analysis_details = self._format_analysis_results(analysis_results)
        
        if base_template:
            return base_template.format(
                data_summary=data_summary_text,
                data_details=analysis_details,
                analysis_requirements=requirements or "进行全面的数据分析"
            )
        
        # 默认提示词
        return f"""你是一个专业的数据分析师。请基于以下数据和分析结果提供专业洞察。

数据概览:
{data_summary_text}

分析结果:
{analysis_details}

分析要求: {requirements or "进行全面的数据分析"}

请提供以下内容:
1. 数据概述和质量评估
2. 关键发现和模式识别
3. 趋势分析和异常检测
4. 相关性和因果关系分析
5. 业务洞察和意义解释
6. 潜在风险和机会识别

分析洞察:"""
    
    def _format_data_summary(self, data_summary: Dict[str, Any]) -> str:
        """格式化数据摘要"""
        try:
            lines = []
            
            # 基本信息
            basic_info = data_summary.get("基本信息", {})
            lines.append(f"数据行数: {basic_info.get('行数', 'N/A')}")
            lines.append(f"数据列数: {basic_info.get('列数', 'N/A')}")
            lines.append(f"数据源: {basic_info.get('数据源', 'N/A')}")
            
            # 列信息
            column_info = data_summary.get("列信息", {})
            if column_info:
                lines.append("\n列信息:")
                for col_name, col_data in list(column_info.items())[:5]:  # 只显示前5列
                    lines.append(f"- {col_name}: {col_data.get('数据类型', 'N/A')}, "
                               f"缺失率: {col_data.get('缺失率', 'N/A')}")
            
            # 统计信息
            stats_info = data_summary.get("统计信息", {})
            if stats_info:
                lines.append("\n主要统计信息:")
                for col_name, col_stats in list(stats_info.items())[:3]:  # 只显示前3列
                    avg = col_stats.get('平均值', 'N/A')
                    std = col_stats.get('标准差', 'N/A')
                    lines.append(f"- {col_name}: 平均值={avg}, 标准差={std}")
            
            return "\n".join(lines)
            
        except Exception as e:
            logger.error(f"数据摘要格式化失败: {e}")
            return str(data_summary)
    
    def _format_analysis_results(self, analysis_results: Dict[str, Any]) -> str:
        """格式化分析结果"""
        try:
            lines = []
            
            # 描述性分析
            if "descriptive" in analysis_results:
                lines.append("描述性统计:")
                desc_data = analysis_results["descriptive"]
                for col_name, stats in list(desc_data.items())[:3]:  # 前3列
                    lines.append(f"- {col_name}: 均值={stats.get('平均值', 'N/A'):.2f}, "
                               f"标准差={stats.get('标准差', 'N/A'):.2f}")
            
            # 相关性分析
            if "correlation" in analysis_results:
                corr_data = analysis_results["correlation"]
                strong_corr = corr_data.get("strong_correlations", {})
                if strong_corr:
                    lines.append("\n强相关关系:")
                    for pair, corr_value in list(strong_corr.items())[:3]:
                        lines.append(f"- {pair}: {corr_value:.3f}")
            
            # 趋势分析
            if "trend" in analysis_results:
                trend_data = analysis_results["trend"]
                direction = trend_data.get("趋势方向", "N/A")
                slope = trend_data.get("趋势斜率", "N/A")
                lines.append(f"\n趋势分析: {direction}, 斜率={slope}")
            
            return "\n".join(lines) if lines else "无详细分析结果"
            
        except Exception as e:
            logger.error(f"分析结果格式化失败: {e}")
            return str(analysis_results)

    async def _generate_recommendations(self, analysis_results: Dict[str, Any], 
                                      ai_insights: str) -> List[str]:
        """生成建议和推荐"""
        try:
            recommendations_prompt = f"""基于以下分析结果和洞察，请提供3-5个具体的业务建议：

分析结果摘要:
{self._format_analysis_results(analysis_results)}

AI洞察:
{ai_insights}

请提供具体、可执行的建议，格式为简洁的要点列表。每个建议应该包含:
1. 具体的行动建议
2. 预期的效果或目标
3. 实施的优先级（高/中/低）

建议列表:"""
            
            recommendations_text = await self._get_llm_response(
                recommendations_prompt, max_tokens=800
            )
            
            # 解析建议为列表
            recommendations = []
            for line in recommendations_text.split('\n'):
                line = line.strip()
                if line and (line.startswith('-') or line.startswith('•') or 
                           line.startswith('1.') or line.startswith('2.') or
                           line.startswith('3.') or line.startswith('4.') or
                           line.startswith('5.')):
                    # 清理格式化字符
                    clean_line = line.lstrip('-•123456789. ').strip()
                    if clean_line:
                        recommendations.append(clean_line)
            
            return recommendations[:5]  # 最多返回5个建议
            
        except Exception as e:
            logger.error(f"建议生成失败: {e}")
            return ["建议生成失败，请手动分析数据结果"]
    
    async def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        if not isinstance(input_data, dict):
            return False
        
        data = input_data.get("data")
        if data is None:
            return False
        
        # 检查数据格式
        try:
            if isinstance(data, (list, dict)):
                return True
            elif hasattr(data, 'to_dict'):  # pandas DataFrame
                return True
            else:
                return False
        except:
            return False
    
    async def preprocess(self, input_data: Any) -> Any:
        """预处理输入数据"""
        if isinstance(input_data, dict):
            processed_data = input_data.copy()
            
            # 确保有默认的分析类型
            if "analysis_type" not in processed_data:
                processed_data["analysis_type"] = "comprehensive"
            
            # 确保有数据源信息
            if "source" not in processed_data:
                processed_data["source"] = "unknown"
            
            return processed_data
        
        return input_data

class SpecializedAnalysisAgent(AnalysisAgent):
    """专业化分析智能体"""
    
    def __init__(self, specialization: str):
        super().__init__()
        self.specialization = specialization
        self.name = f"Specialized_Analysis_Agent_{specialization}"
        self.description = f"专门进行{specialization}分析的智能体"
        self.add_capability(f"{specialization}_analysis")
    
    async def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理专业化分析请求"""
        # 设置专业化的分析类型
        if isinstance(input_data, dict):
            input_data = input_data.copy()
            input_data["analysis_type"] = self.specialization
            input_data["requirements"] = input_data.get("requirements", "") + f" 请特别关注{self.specialization}相关的分析。"
        
        # 调用基类方法
        result = await super().process(input_data, context)
        
        # 添加专业化信息
        result["specialization"] = self.specialization
        result["specialized_insights"] = await self._get_specialized_insights(result)
        
        return result
    
    async def _get_specialized_insights(self, base_result: Dict[str, Any]) -> str:
        """获取专业化洞察"""
        try:
            specialized_prompt = f"""作为{self.specialization}分析专家，请基于以下分析结果提供专业洞察：

基础分析结果:
{base_result.get('ai_insights', '')}

数据摘要:
{self._format_data_summary(base_result.get('data_summary', {}))}

请从{self.specialization}的专业角度提供深入分析和建议。

专业洞察:"""
            
            return await self._get_llm_response(specialized_prompt, max_tokens=4096)
            
        except Exception as e:
            logger.error(f"专业化洞察生成失败: {e}")
            return f"专业化洞察生成失败: {str(e)}"
