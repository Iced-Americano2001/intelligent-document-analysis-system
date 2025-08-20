from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union
import logging
import asyncio
from datetime import datetime
from utils.llm_utils import llm_manager
from config.settings import OLLAMA_CONFIG, OPENAI_CONFIG, THIRD_PARTY_API_CONFIG

logger = logging.getLogger(__name__)

class BaseAgent(ABC):
    """智能体基类"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.context = {}
        self.memory = []
        self.capabilities = []
        self.llm_provider = "ollama"  # 默认使用ollama
        self.max_context_length = 4000
        self.temperature = 0.7
        
    @abstractmethod
    async def process(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """处理输入数据的抽象方法"""
        pass
    
    async def _get_llm_response(self, prompt: str, **kwargs) -> str:
        """获取LLM响应"""
        try:
            # 合并默认参数和传入参数
            default_max_tokens = 2000
            try:
                if self.llm_provider == "ollama":
                    default_max_tokens = OLLAMA_CONFIG.get("max_tokens", 2000)
                elif self.llm_provider == "openai":
                    default_max_tokens = OPENAI_CONFIG.get("max_tokens", 4000)
                elif self.llm_provider == "third_party":
                    default_max_tokens = THIRD_PARTY_API_CONFIG.get("max_tokens", 4000)
            except Exception:
                default_max_tokens = 2000

            requested_max = kwargs.get("max_tokens")
            effective_max = default_max_tokens if requested_max is None else min(requested_max, default_max_tokens)

            llm_kwargs = {
                "temperature": self.temperature,
                "max_tokens": effective_max,
                **{k: v for k, v in kwargs.items() if k != "max_tokens"}
            }
            
            response = await llm_manager.generate_completion(
                prompt, 
                provider=self.llm_provider,
                **llm_kwargs
            )
            
            if response.get("success"):
                return response.get("response", "")
            else:
                raise Exception(f"LLM调用失败: {response.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"Agent {self.name} LLM调用异常: {str(e)}")
            raise
    
    async def _get_chat_response(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """获取聊天响应"""
        try:
            default_max_tokens = 2000
            try:
                if self.llm_provider == "ollama":
                    default_max_tokens = OLLAMA_CONFIG.get("max_tokens", 2000)
                elif self.llm_provider == "openai":
                    default_max_tokens = OPENAI_CONFIG.get("max_tokens", 4000)
                elif self.llm_provider == "third_party":
                    default_max_tokens = THIRD_PARTY_API_CONFIG.get("max_tokens", 4000)
            except Exception:
                default_max_tokens = 2000

            requested_max = kwargs.get("max_tokens")
            effective_max = default_max_tokens if requested_max is None else min(requested_max, default_max_tokens)

            llm_kwargs = {
                "temperature": self.temperature,
                "max_tokens": effective_max,
                **{k: v for k, v in kwargs.items() if k != "max_tokens"}
            }
            
            response = await llm_manager.chat_completion(
                messages,
                provider=self.llm_provider,
                **llm_kwargs
            )
            
            if response.get("success"):
                message = response.get("message", {})
                return message.get("content", "") if isinstance(message, dict) else str(message)
            else:
                raise Exception(f"LLM聊天调用失败: {response.get('error', '未知错误')}")
                
        except Exception as e:
            logger.error(f"Agent {self.name} 聊天调用异常: {str(e)}")
            raise
    
    def update_context(self, key: str, value: Any) -> None:
        """更新智能体上下文"""
        self.context[key] = value
        logger.debug(f"Agent {self.name} 上下文更新: {key}")
    
    def get_context(self, key: str, default: Any = None) -> Any:
        """获取上下文值"""
        return self.context.get(key, default)
    
    def add_memory(self, memory_item: Dict[str, Any]) -> None:
        """添加记忆"""
        memory_item["timestamp"] = datetime.now().isoformat()
        self.memory.append(memory_item)
        
        # 限制记忆长度，保留最近的记忆
        max_memory = 50
        if len(self.memory) > max_memory:
            self.memory = self.memory[-max_memory:]
        
        logger.debug(f"Agent {self.name} 添加记忆: {memory_item.get('type', 'unknown')}")
    
    def get_recent_memory(self, count: int = 10) -> List[Dict[str, Any]]:
        """获取最近的记忆"""
        return self.memory[-count:] if self.memory else []
    
    def clear_memory(self) -> None:
        """清除记忆"""
        self.memory.clear()
        logger.info(f"Agent {self.name} 记忆已清除")
    
    def set_llm_provider(self, provider: str) -> None:
        """设置LLM提供商"""
        self.llm_provider = provider
        logger.info(f"Agent {self.name} LLM提供商设置为: {provider}")
    
    def set_temperature(self, temperature: float) -> None:
        """设置温度参数"""
        self.temperature = max(0.0, min(1.0, temperature))
        logger.info(f"Agent {self.name} 温度设置为: {self.temperature}")
    
    def add_capability(self, capability: str) -> None:
        """添加能力"""
        if capability not in self.capabilities:
            self.capabilities.append(capability)
            logger.info(f"Agent {self.name} 添加能力: {capability}")
    
    def has_capability(self, capability: str) -> bool:
        """检查是否具有某项能力"""
        return capability in self.capabilities
    
    def get_status(self) -> Dict[str, Any]:
        """获取智能体状态"""
        return {
            "name": self.name,
            "description": self.description,
            "capabilities": self.capabilities,
            "llm_provider": self.llm_provider,
            "temperature": self.temperature,
            "context_size": len(self.context),
            "memory_size": len(self.memory),
            "max_context_length": self.max_context_length
        }
    
    def get_agent_info(self) -> Dict[str, Any]:
        """获取智能体信息 - 兼容测试"""
        return self.get_status()
    
    async def validate_input(self, input_data: Any) -> bool:
        """验证输入数据"""
        # 子类可以重写此方法来实现特定的验证逻辑
        return input_data is not None
    
    async def preprocess(self, input_data: Any) -> Any:
        """预处理输入数据"""
        # 子类可以重写此方法来实现特定的预处理逻辑
        return input_data
    
    async def postprocess(self, output_data: Any) -> Any:
        """后处理输出数据"""
        # 子类可以重写此方法来实现特定的后处理逻辑
        return output_data
    
    def _truncate_text(self, text: str, max_length: Optional[int] = None) -> str:
        """截断文本以适应上下文长度限制"""
        if max_length is None:
            max_length = self.max_context_length
        
        if len(text) <= max_length:
            return text
        
        # 从中间截断，保留开头和结尾
        start_length = max_length // 3
        end_length = max_length // 3
        middle_text = "\n...[文本已截断]...\n"
        
        return text[:start_length] + middle_text + text[-end_length:]
    
    def _format_context_history(self, max_items: int = 5) -> str:
        """格式化上下文历史"""
        recent_memory = self.get_recent_memory(max_items)
        if not recent_memory:
            return ""
        
        history_lines = ["上下文历史:"]
        for item in recent_memory:
            timestamp = item.get("timestamp", "")
            memory_type = item.get("type", "unknown")
            content = str(item.get("content", ""))[:100]  # 限制长度
            history_lines.append(f"- [{timestamp}] {memory_type}: {content}")
        
        return "\n".join(history_lines)

class AgentCoordinator:
    """智能体协调器"""
    
    def __init__(self):
        self.agents: Dict[str, BaseAgent] = {}
        self.workflows = {}
        
    def register_agent(self, agent: BaseAgent) -> None:
        """注册智能体"""
        self.agents[agent.name] = agent
        logger.info(f"智能体已注册: {agent.name}")
    
    def get_agent(self, name: str) -> Optional[BaseAgent]:
        """获取智能体"""
        return self.agents.get(name)
    
    def list_agents(self) -> List[str]:
        """列出所有智能体"""
        return list(self.agents.keys())
    
    async def execute_agent(self, agent_name: str, input_data: Any, 
                          context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行智能体"""
        agent = self.get_agent(agent_name)
        if not agent:
            raise ValueError(f"智能体不存在: {agent_name}")
        
        try:
            start_time = datetime.now()
            
            # 验证输入
            if not await agent.validate_input(input_data):
                raise ValueError("输入数据验证失败")
            
            # 预处理
            processed_input = await agent.preprocess(input_data)
            
            # 执行主要处理逻辑
            result = await agent.process(processed_input, context)
            
            # 后处理
            final_result = await agent.postprocess(result)
            
            end_time = datetime.now()
            execution_time = (end_time - start_time).total_seconds()
            
            # 记录执行信息
            agent.add_memory({
                "type": "execution",
                "input_type": type(input_data).__name__,
                "execution_time": execution_time,
                "success": True
            })
            
            return {
                "agent": agent_name,
                "result": final_result,
                "execution_time": execution_time,
                "timestamp": end_time.isoformat(),
                "success": True
            }
            
        except Exception as e:
            logger.error(f"智能体执行失败: {agent_name}, 错误: {e}")
            
            # 记录错误信息
            agent.add_memory({
                "type": "error",
                "error": str(e),
                "success": False
            })
            
            return {
                "agent": agent_name,
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "success": False
            }
    
    async def execute_workflow(self, workflow_name: str, input_data: Any,
                             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行工作流"""
        if workflow_name not in self.workflows:
            raise ValueError(f"工作流不存在: {workflow_name}")
        
        workflow = self.workflows[workflow_name]
        results = []
        shared_context = context or {}
        
        try:
            for step in workflow["steps"]:
                agent_name = step["agent"]
                step_input = step.get("input", input_data)
                
                # 执行智能体
                result = await self.execute_agent(agent_name, step_input, shared_context)
                results.append(result)
                
                # 更新共享上下文
                if result["success"]:
                    shared_context[f"{agent_name}_result"] = result["result"]
                else:
                    # 如果关键步骤失败，停止工作流
                    if step.get("critical", True):
                        break
            
            return {
                "workflow": workflow_name,
                "results": results,
                "context": shared_context,
                "success": all(r["success"] for r in results)
            }
            
        except Exception as e:
            logger.error(f"工作流执行失败: {workflow_name}, 错误: {e}")
            return {
                "workflow": workflow_name,
                "error": str(e),
                "partial_results": results,
                "success": False
            }
    
    def register_workflow(self, name: str, steps: List[Dict[str, Any]]) -> None:
        """注册工作流"""
        self.workflows[name] = {
            "name": name,
            "steps": steps,
            "created_at": datetime.now().isoformat()
        }
        logger.info(f"工作流已注册: {name}")
    
    def get_all_status(self) -> Dict[str, Any]:
        """获取所有智能体状态"""
        return {
            "agents": {name: agent.get_status() for name, agent in self.agents.items()},
            "workflows": list(self.workflows.keys()),
            "total_agents": len(self.agents)
        }

# 全局智能体协调器实例
agent_coordinator = AgentCoordinator()
