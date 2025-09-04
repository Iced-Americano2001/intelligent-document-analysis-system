"""
对话报告功能演示
演示如何使用报告生成功能
"""
import asyncio
import logging
from datetime import datetime
from pathlib import Path

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def demo_report_generation():
    """演示报告生成功能"""
    print("🤖 智能文档分析系统 - 对话报告功能演示")
    print("=" * 50)
    
    # 导入所需模块
    from agents.report_agent import ReportAgent
    from utils.report_exporter import ReportExporter
    from utils.conversation_manager import ConversationHistoryManager
    
    # 创建实例
    report_agent = ReportAgent()
    exporter = ReportExporter()
    history_manager = ConversationHistoryManager()
    
    # 创建模拟对话历史
    print("📝 创建模拟对话历史...")
    
    # 文档问答对话示例
    qa_conversations = [
        {
            "type": "question",
            "content": "这个文档的主要内容是什么？",
            "timestamp": "2025-09-04T10:00:00",
            "metadata": {"file_name": "sample_doc.pdf"}
        },
        {
            "type": "answer", 
            "content": "这个文档主要介绍了人工智能在现代办公环境中的应用。文档分为三个部分：1）AI技术概述，2）实际应用案例，3）未来发展趋势。重点讨论了机器学习、自然语言处理和计算机视觉等核心技术如何提升工作效率。",
            "timestamp": "2025-09-04T10:00:30",
            "metadata": {"file_name": "sample_doc.pdf", "confidence": 0.95}
        },
        {
            "type": "question",
            "content": "文档中提到了哪些具体的AI应用案例？",
            "timestamp": "2025-09-04T10:05:00",
            "metadata": {"file_name": "sample_doc.pdf"}
        },
        {
            "type": "answer",
            "content": "文档提到了以下几个具体的AI应用案例：\n1. 智能客服系统 - 使用自然语言处理技术，可以自动回答90%的常见问题\n2. 文档自动分类系统 - 基于机器学习算法，准确率达到95%\n3. 会议记录自动生成 - 结合语音识别和文本摘要技术\n4. 邮件智能分类和优先级排序\n5. 数据分析报告自动生成工具",
            "timestamp": "2025-09-04T10:05:45", 
            "metadata": {"file_name": "sample_doc.pdf", "confidence": 0.92}
        },
        {
            "type": "question",
            "content": "作者对AI发展趋势有什么看法？",
            "timestamp": "2025-09-04T10:10:00",
            "metadata": {"file_name": "sample_doc.pdf"}
        },
        {
            "type": "answer",
            "content": "作者认为AI发展将呈现以下趋势：\n• 更深度的人机协作：AI不会替代人类，而是成为智能助手\n• 个性化程度提升：AI系统将更好地理解用户偏好和工作习惯\n• 跨领域应用扩展：从单一场景向多领域综合应用发展\n• 伦理和安全重视：建立更完善的AI治理框架\n• 普及化加速：AI工具将变得更加用户友好，降低使用门槛",
            "timestamp": "2025-09-04T10:10:40",
            "metadata": {"file_name": "sample_doc.pdf", "confidence": 0.88}
        }
    ]
    
    # 数据分析对话示例
    data_conversations = [
        {
            "type": "question",
            "content": "请分析这个销售数据表中的趋势",
            "timestamp": "2025-09-04T14:00:00",
            "metadata": {"file_name": "sales_data.xlsx", "data_shape": "100行×8列"}
        },
        {
            "type": "answer",
            "content": "通过分析销售数据，我发现以下关键趋势：\n\n📈 **销售趋势分析**\n• 总销售额：本季度同比增长15.2%\n• 季节性特征：Q2和Q4为销售高峰期\n• 地域分布：华东地区占总销售额的35%，表现最佳\n\n🏆 **产品表现**\n• 产品A销量领先，占总销量的28%\n• 新产品C增长迅速，环比增长45%\n• 传统产品B出现下滑趋势，需要关注\n\n💡 **关键洞察**\n• 线上渠道销售增长明显，占比已达45%\n• 客单价平均提升12%，显示产品价值提升\n• 复购率达到68%，客户忠诚度较高",
            "timestamp": "2025-09-04T14:02:30",
            "metadata": {"file_name": "sales_data.xlsx", "analysis_type": "趋势分析"}
        },
        {
            "type": "question", 
            "content": "哪些因素影响了销售业绩？",
            "timestamp": "2025-09-04T14:05:00",
            "metadata": {"file_name": "sales_data.xlsx"}
        },
        {
            "type": "answer",
            "content": "基于数据分析，以下因素对销售业绩产生了显著影响：\n\n🎯 **正向影响因素**\n• 营销活动投入：ROI达到3.2，效果显著\n• 产品创新：新品上市带来20%的增量\n• 渠道扩展：新增线上平台贡献了25%的增长\n• 客户服务优化：满意度提升至90%\n\n⚠️ **负向影响因素**\n• 原材料成本上涨：影响毛利率下降3%\n• 市场竞争加剧：部分区域价格战激烈\n• 季节性波动：淡季销量下滑明显\n\n📊 **数据支撑**\n• 广告投入与销量相关系数：0.82\n• 客户满意度与复购率相关系数：0.75\n• 价格敏感度分析显示，10%的价格变动会引起15%的销量变化",
            "timestamp": "2025-09-04T14:07:15",
            "metadata": {"file_name": "sales_data.xlsx", "analysis_type": "因素分析"}
        }
    ]
    
    print("✅ 模拟对话历史创建完成")
    print(f"   - 文档问答对话：{len(qa_conversations)} 条记录")
    print(f"   - 数据分析对话：{len(data_conversations)} 条记录")
    
    # 演示文档问答报告生成
    print("\n📊 生成文档问答报告...")
    
    user_preferences = {
        "report_style": "detailed",
        "include_metadata": True,
        "include_statistics": True
    }
    
    qa_report = await report_agent.generate_conversation_report(
        qa_conversations, "document_qa", user_preferences
    )
    
    if qa_report.get("success"):
        print("✅ 文档问答报告生成成功")
        
        # 导出为不同格式
        print("\n📤 导出报告...")
        
        # HTML格式
        html_result = exporter.export_report(qa_report, "html")
        if html_result.get("success"):
            print(f"   ✅ HTML报告：{html_result['file_path']}")
        
        # Word格式
        docx_result = exporter.export_report(qa_report, "docx")
        if docx_result.get("success"):
            print(f"   ✅ Word报告：{docx_result['file_path']}")
        
        # JSON格式
        json_result = exporter.export_report(qa_report, "json")
        if json_result.get("success"):
            print(f"   ✅ JSON报告：{json_result['file_path']}")
    
    else:
        print(f"❌ 文档问答报告生成失败：{qa_report.get('error')}")
    
    # 演示数据分析报告生成
    print("\n📊 生成数据分析报告...")
    
    data_report = await report_agent.generate_conversation_report(
        data_conversations, "data_analysis", user_preferences
    )
    
    if data_report.get("success"):
        print("✅ 数据分析报告生成成功")
        
        # 导出为HTML格式展示
        html_result = exporter.export_report(data_report, "html")
        if html_result.get("success"):
            print(f"   ✅ HTML报告：{html_result['file_path']}")
    
    else:
        print(f"❌ 数据分析报告生成失败：{data_report.get('error')}")
    
    # 演示不同报告样式
    print("\n🎨 演示不同报告样式...")
    
    styles = ["detailed", "summary", "bullet_points"]
    for style in styles:
        print(f"\n   📝 生成{style}样式报告...")
        style_preferences = {
            "report_style": style,
            "include_metadata": True,
            "include_statistics": True
        }
        
        style_report = await report_agent.generate_conversation_report(
            qa_conversations[:4], "document_qa", style_preferences  # 使用部分对话
        )
        
        if style_report.get("success"):
            # 导出为HTML
            html_result = exporter.export_report(style_report, "html", f"outputs/reports/demo_{style}")
            if html_result.get("success"):
                print(f"      ✅ {style}样式报告：{html_result['file_path']}")
    
    print("\n🎉 演示完成！")
    print("\n📁 生成的报告文件保存在：outputs/reports/ 目录下")
    print("💡 您可以在浏览器中打开HTML文件查看报告效果")

def demo_conversation_manager():
    """演示对话管理器功能"""
    print("\n" + "=" * 50)
    print("📚 对话管理器功能演示")
    print("=" * 50)
    
    from utils.conversation_manager import ConversationHistoryManager
    
    manager = ConversationHistoryManager()
    
    # 添加一些示例对话
    print("📝 添加示例对话...")
    
    manager.add_conversation(
        "什么是机器学习？",
        "机器学习是人工智能的一个分支，它使计算机能够在没有明确编程的情况下学习和改进。",
        "document_qa",
        {"file_name": "ai_guide.pdf", "confidence": 0.95}
    )
    
    manager.add_conversation(
        "请分析这个月的销售数据",
        "本月销售额同比增长12%，主要增长来源于在线渠道。",
        "data_analysis", 
        {"file_name": "monthly_sales.xlsx", "data_shape": "50行×6列"}
    )
    
    # 获取统计信息
    print("\n📊 对话统计信息：")
    qa_stats = manager.get_conversation_statistics("document_qa")
    data_stats = manager.get_conversation_statistics("data_analysis")
    
    print(f"   文档问答：{qa_stats.get('total_conversations', 0)} 轮对话")
    print(f"   数据分析：{data_stats.get('total_conversations', 0)} 轮对话")
    
    # 演示搜索功能
    print("\n🔍 搜索功能演示：")
    search_results = manager.search_conversations("机器学习", "document_qa")
    print(f"   搜索'机器学习'找到 {len(search_results)} 条记录")
    
    # 演示备份功能
    print("\n💾 备份功能演示：")
    backup_result = manager.backup_conversation_history("document_qa")
    if backup_result.get("success"):
        print(f"   ✅ 备份成功：{backup_result['backup_path']}")
    
    print("\n✅ 对话管理器演示完成")

if __name__ == "__main__":
    print("🚀 启动对话报告功能演示...")
    
    try:
        # 运行报告生成演示
        asyncio.run(demo_report_generation())
        
        # 运行对话管理器演示
        demo_conversation_manager()
        
        print("\n" + "=" * 50)
        print("🎉 所有演示完成！")
        print("📖 现在您可以在Web界面中体验完整的报告功能了")
        print("💡 启动应用：streamlit run app.py")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ 演示过程中出现错误：{e}")
        import traceback
        traceback.print_exc()
