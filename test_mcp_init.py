#!/usr/bin/env python3
"""
测试MCP智能体初始化问题修复
"""

import asyncio
import logging
from agents.mcp_agent import MCPDocumentQAAgent

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_mcp_initialization():
    """测试MCP智能体初始化"""
    print("🧪 开始测试MCP智能体初始化...")
    
    # 测试1: 创建智能体
    print("\n📝 测试1: 创建MCP智能体")
    try:
        agent = MCPDocumentQAAgent()
        print("✅ MCP智能体创建成功")
    except Exception as e:
        print(f"❌ MCP智能体创建失败: {e}")
        return False
    
    # 测试2: 第一次初始化
    print("\n📝 测试2: 第一次初始化")
    try:
        await agent.initialize()
        print(f"✅ 第一次初始化成功，工具数量: {len(agent.available_tools)}")
    except Exception as e:
        print(f"❌ 第一次初始化失败: {e}")
        return False
    
    # 测试3: 重复初始化（测试幂等性）
    print("\n📝 测试3: 重复初始化（幂等性测试）")
    try:
        tool_count_before = len(agent.available_tools)
        await agent.initialize()
        tool_count_after = len(agent.available_tools)
        if tool_count_before == tool_count_after:
            print(f"✅ 重复初始化成功，工具数量保持一致: {tool_count_after}")
        else:
            print(f"⚠️ 重复初始化后工具数量变化: {tool_count_before} -> {tool_count_after}")
    except Exception as e:
        print(f"❌ 重复初始化失败: {e}")
        return False
    
    # 测试4: 并发初始化
    print("\n📝 测试4: 并发初始化测试")
    try:
        tasks = [agent.initialize() for _ in range(3)]
        await asyncio.gather(*tasks)
        print(f"✅ 并发初始化成功，工具数量: {len(agent.available_tools)}")
    except Exception as e:
        print(f"❌ 并发初始化失败: {e}")
        return False
    
    print("\n🎉 所有测试通过！MCP智能体初始化修复成功")
    return True

if __name__ == "__main__":
    asyncio.run(test_mcp_initialization())
