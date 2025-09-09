"""
图表报告增强组件
专门处理报告中的图表显示和导出功能
"""
import streamlit as st
import logging
from typing import Dict, Any, List, Optional
import json
from pathlib import Path
import zipfile
import tempfile

logger = logging.getLogger(__name__)

class ChartReportEnhancer:
    """图表报告增强器"""
    
    def __init__(self):
        from utils.chart_converter import ChartConverter
        self.chart_converter = ChartConverter()
    
    def display_charts_in_report(self, qa_pairs: List[Dict], expanded: bool = False):
        """
        在报告中显示图表
        
        Args:
            qa_pairs: 问答对列表，包含图表数据
            expanded: 是否默认展开图表
        """
        total_charts = 0
        
        for i, qa in enumerate(qa_pairs, 1):
            charts = qa.get("charts", {})
            if charts:
                total_charts += len(charts)
                
                with st.expander(f"📊 问答 {i} 的图表 ({len(charts)}个)", expanded=expanded):
                    st.markdown(f"**问题:** {qa.get('question', '')[:100]}...")
                    
                    # 以tab形式显示多个图表
                    if len(charts) > 1:
                        chart_tabs = st.tabs([name.replace('_', ' ').title() for name in charts.keys()])
                        
                        for tab, (chart_name, chart_json) in zip(chart_tabs, charts.items()):
                            with tab:
                                self._display_single_chart(chart_name, chart_json)
                    else:
                        # 只有一个图表时直接显示
                        chart_name, chart_json = next(iter(charts.items()))
                        self._display_single_chart(chart_name, chart_json)
        
        if total_charts > 0:
            st.success(f"✅ 报告中包含 {total_charts} 个数据可视化图表")
        else:
            st.info("📊 此报告中暂无数据图表")
    
    def _display_single_chart(self, chart_name: str, chart_json: str):
        """显示单个图表"""
        try:
            import plotly.graph_objects as go
            
            # 重建图表
            chart_data = json.loads(chart_json)
            fig = go.Figure(chart_data)
            
            # 显示图表
            st.plotly_chart(fig, use_container_width=True, key=f"chart_{chart_name}")
            
            # 显示图表摘要信息
            with st.expander("📋 图表信息", expanded=False):
                chart_summary = self.chart_converter.extract_chart_summary(chart_json)
                
                col1, col2 = st.columns(2)
                with col1:
                    st.metric("图表类型", chart_summary.get("chart_type", "未知"))
                    st.metric("数据点数", chart_summary.get("data_points", 0))
                with col2:
                    st.metric("数据轨迹", chart_summary.get("traces", 0))
                    if chart_summary.get("title"):
                        st.write(f"**标题:** {chart_summary['title']}")
                
                if chart_summary.get("x_axis"):
                    st.write(f"**X轴:** {chart_summary['x_axis']}")
                if chart_summary.get("y_axis"):
                    st.write(f"**Y轴:** {chart_summary['y_axis']}")
            
            # 提供图表下载选项
            with st.expander("💾 下载图表", expanded=False):
                self._provide_chart_download_options(chart_name, chart_json)
                
        except Exception as e:
            st.error(f"❌ 图表 {chart_name} 显示失败: {str(e)}")
            logger.error(f"显示图表失败: {e}")
    
    def _provide_chart_download_options(self, chart_name: str, chart_json: str):
        """提供图表下载选项"""
        col1, col2, col3 = st.columns(3)
        
        with col1:
            if st.button("📥 下载PNG", key=f"download_png_{chart_name}"):
                self._download_chart_as_image(chart_name, chart_json, "png")
        
        with col2:
            if st.button("📥 下载SVG", key=f"download_svg_{chart_name}"):
                self._download_chart_as_image(chart_name, chart_json, "svg")
        
        with col3:
            if st.button("📥 下载HTML", key=f"download_html_{chart_name}"):
                self._download_chart_as_html(chart_name, chart_json)
    
    def _download_chart_as_image(self, chart_name: str, chart_json: str, format_type: str):
        """下载图表为图片格式"""
        try:
            # 转换为图片
            img_b64 = self.chart_converter.chart_to_image(chart_json, format_type, 1200, 800)
            
            if img_b64:
                import base64
                img_bytes = base64.b64decode(img_b64)
                
                # 提供下载
                st.download_button(
                    label=f"💾 保存 {format_type.upper()} 文件",
                    data=img_bytes,
                    file_name=f"{chart_name}.{format_type}",
                    mime=f"image/{format_type}",
                    key=f"save_{format_type}_{chart_name}"
                )
            else:
                st.error(f"❌ {format_type.upper()}格式转换失败")
                
        except Exception as e:
            st.error(f"❌ 图片下载失败: {str(e)}")
    
    def _download_chart_as_html(self, chart_name: str, chart_json: str):
        """下载图表为HTML格式"""
        try:
            # 转换为HTML
            html_content = self.chart_converter.chart_to_html(chart_json, include_plotlyjs='inline')
            
            if html_content:
                st.download_button(
                    label="💾 保存 HTML 文件",
                    data=html_content.encode('utf-8'),
                    file_name=f"{chart_name}.html",
                    mime="text/html",
                    key=f"save_html_{chart_name}"
                )
            else:
                st.error("❌ HTML格式转换失败")
                
        except Exception as e:
            st.error(f"❌ HTML下载失败: {str(e)}")
    
    def export_all_charts_as_zip(self, conversation_history: List[Dict], output_dir: Optional[str] = None) -> Optional[str]:
        """
        导出所有图表为ZIP文件
        
        Args:
            conversation_history: 对话历史
            output_dir: 输出目录
            
        Returns:
            ZIP文件路径，如果失败返回None
        """
        try:
            if not output_dir:
                output_dir = Path("outputs/charts")
            else:
                output_dir = Path(output_dir)
            
            output_dir.mkdir(parents=True, exist_ok=True)
            
            # 创建临时目录
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_path = Path(temp_dir)
                chart_count = 0
                
                # 提取所有图表
                for i, conv in enumerate(conversation_history):
                    if conv.get("type") == "answer":
                        charts = conv.get("charts", {})
                        for chart_name, chart_json in charts.items():
                            try:
                                # 保存多种格式
                                base_name = f"qa_{i//2+1}_{chart_name}"
                                
                                # PNG格式
                                png_path = temp_path / f"{base_name}.png"
                                if self.chart_converter.save_chart_as_file(chart_json, str(png_path), "png", 1200, 800):
                                    chart_count += 1
                                
                                # HTML格式
                                html_path = temp_path / f"{base_name}.html"
                                self.chart_converter.save_chart_as_file(chart_json, str(html_path), "html")
                                
                                # JSON格式
                                json_path = temp_path / f"{base_name}.json"
                                self.chart_converter.save_chart_as_file(chart_json, str(json_path), "json")
                                
                            except Exception as e:
                                logger.warning(f"导出图表{chart_name}失败: {e}")
                
                if chart_count == 0:
                    logger.warning("没有找到可导出的图表")
                    return None
                
                # 创建ZIP文件
                from datetime import datetime
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                zip_path = output_dir / f"charts_export_{timestamp}.zip"
                
                with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                    for file_path in temp_path.iterdir():
                        if file_path.is_file():
                            zipf.write(file_path, file_path.name)
                
                logger.info(f"图表ZIP文件已创建: {zip_path}")
                return str(zip_path)
                
        except Exception as e:
            logger.error(f"导出图表ZIP文件失败: {e}")
            return None
    
    def analyze_chart_statistics(self, conversation_history: List[Dict]) -> Dict[str, Any]:
        """
        分析图表统计信息
        
        Args:
            conversation_history: 对话历史
            
        Returns:
            图表统计信息
        """
        try:
            stats = {
                "total_charts": 0,
                "chart_types": {},
                "charts_per_qa": [],
                "chart_details": []
            }
            
            for i, conv in enumerate(conversation_history):
                if conv.get("type") == "answer":
                    charts = conv.get("charts", {})
                    qa_chart_count = len(charts)
                    stats["charts_per_qa"].append(qa_chart_count)
                    stats["total_charts"] += qa_chart_count
                    
                    for chart_name, chart_json in charts.items():
                        try:
                            # 获取图表摘要
                            chart_summary = self.chart_converter.extract_chart_summary(chart_json)
                            chart_type = chart_summary.get("chart_type", "未知")
                            
                            # 统计图表类型
                            stats["chart_types"][chart_type] = stats["chart_types"].get(chart_type, 0) + 1
                            
                            # 记录图表详情
                            stats["chart_details"].append({
                                "qa_index": i // 2 + 1,
                                "chart_name": chart_name,
                                "chart_type": chart_type,
                                "data_points": chart_summary.get("data_points", 0),
                                "traces": chart_summary.get("traces", 0),
                                "title": chart_summary.get("title", "")
                            })
                            
                        except Exception as e:
                            logger.warning(f"分析图表{chart_name}统计信息失败: {e}")
            
            return stats
            
        except Exception as e:
            logger.error(f"分析图表统计信息失败: {e}")
            return {
                "total_charts": 0,
                "chart_types": {},
                "charts_per_qa": [],
                "chart_details": []
            }
    
    def display_chart_statistics_dashboard(self, stats: Dict[str, Any]):
        """显示图表统计仪表板"""
        try:
            st.markdown("### 📊 图表统计仪表板")
            
            # 总体统计
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("总图表数", stats.get("total_charts", 0))
            with col2:
                st.metric("图表类型数", len(stats.get("chart_types", {})))
            with col3:
                charts_per_qa = stats.get("charts_per_qa", [])
                avg_charts = sum(charts_per_qa) / len(charts_per_qa) if charts_per_qa else 0
                st.metric("平均图表/问答", f"{avg_charts:.1f}")
            with col4:
                max_charts = max(charts_per_qa) if charts_per_qa else 0
                st.metric("单次最多图表", max_charts)
            
            # 图表类型分布
            chart_types = stats.get("chart_types", {})
            if chart_types:
                st.markdown("#### 图表类型分布")
                
                # 创建饼图显示分布
                import plotly.express as px
                import pandas as pd
                
                df = pd.DataFrame(list(chart_types.items()), columns=["图表类型", "数量"])
                fig = px.pie(df, names="图表类型", values="数量", title="图表类型分布")
                st.plotly_chart(fig, use_container_width=True)
            
            # 详细列表
            chart_details = stats.get("chart_details", [])
            if chart_details:
                st.markdown("#### 图表详细列表")
                
                import pandas as pd
                df_details = pd.DataFrame(chart_details)
                df_details.columns = ["问答序号", "图表名称", "图表类型", "数据点数", "数据轨迹", "标题"]
                st.dataframe(df_details, use_container_width=True)
            
        except Exception as e:
            st.error(f"❌ 显示图表统计仪表板失败: {str(e)}")
            logger.error(f"显示图表统计仪表板失败: {e}")
