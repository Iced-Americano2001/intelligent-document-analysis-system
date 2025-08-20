import aiohttp
import asyncio
from typing import Dict, Any, List, Optional, Union
from abc import ABC, abstractmethod
import json
from loguru import logger
from config.settings import OLLAMA_CONFIG, OPENAI_CONFIG, ANTHROPIC_CONFIG, get_third_party_config, is_third_party_enabled

class BaseLLMClient(ABC):
    """大语言模型客户端基类"""
    
    def __init__(self, model_name: str):
        self.model_name = model_name
        
    @abstractmethod
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成文本补全"""
        pass
    
    @abstractmethod
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """聊天补全"""
        pass

class OllamaClient(BaseLLMClient):
    """Ollama 客户端"""
    
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(model_name or OLLAMA_CONFIG['model'])
        self.base_url = OLLAMA_CONFIG['host']
        self.timeout = OLLAMA_CONFIG['timeout']
        self.max_tokens = OLLAMA_CONFIG.get('max_tokens', 2000)
        
        # 确保URL格式正确
        if not self.base_url.startswith('http'):
            self.base_url = f"http://localhost{self.base_url}" if self.base_url.startswith(':') else f"http://{self.base_url}"
        
        logger.info(f"初始化Ollama客户端: URL={self.base_url}, Model={self.model_name}")
    
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成文本补全"""
        try:
            url = f"{self.base_url}/api/generate"
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": kwargs.get("stream", False),
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.9),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "response": result.get("response", ""),
                            "model": result.get("model", self.model_name),
                            "created_at": result.get("created_at"),
                            "done": result.get("done", True)
                        }
                    else:
                        error_text = await response.text()
                        logger.error(f"Ollama API错误: {response.status} - {error_text}")
                        return {
                            "success": False,
                            "error": f"API错误: {response.status} - {error_text}"
                        }
        except Exception as e:
            logger.error(f"Ollama API调用异常: {str(e)}")
            return {
                "success": False,
                "error": f"连接异常: {str(e)}"
            }
    
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """聊天补全"""
        try:
            url = f"{self.base_url}/api/chat"
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "stream": kwargs.get("stream", False),
                "options": {
                    "temperature": kwargs.get("temperature", 0.7),
                    "top_p": kwargs.get("top_p", 0.9),
                    "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    url,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=self.timeout)
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "message": result.get("message", {}),
                            "model": result.get("model", self.model_name),
                            "created_at": result.get("created_at"),
                            "done": result.get("done", True)
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"API错误: {response.status} - {error_text}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"连接异常: {str(e)}"
            }

class OpenAIClient(BaseLLMClient):
    """OpenAI 客户端"""
    
    def __init__(self, model_name: Optional[str] = None):
        super().__init__(model_name or OPENAI_CONFIG['model'])
        self.api_key = OPENAI_CONFIG['api_key']
        self.base_url = OPENAI_CONFIG.get('base_url', 'https://api.openai.com/v1')
        self.max_tokens = OPENAI_CONFIG['max_tokens']
        
        if not self.api_key:
            logger.warning("OpenAI API密钥未配置")
    
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成文本补全"""
        try:
            url = f"{self.base_url}/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 1.0),
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "response": result["choices"][0]["text"],
                            "model": result["model"],
                            "usage": result.get("usage", {})
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"OpenAI API错误: {response.status} - {error_text}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"OpenAI API异常: {str(e)}"
            }
    
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """聊天补全"""
        try:
            url = f"{self.base_url}/chat/completions"
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", 0.7),
                "top_p": kwargs.get("top_p", 1.0),
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers) as response:
                    if response.status == 200:
                        result = await response.json()
                        return {
                            "success": True,
                            "message": result["choices"][0]["message"],
                            "model": result["model"],
                            "usage": result.get("usage", {})
                        }
                    else:
                        error_text = await response.text()
                        return {
                            "success": False,
                            "error": f"OpenAI API错误: {response.status} - {error_text}"
                        }
        except Exception as e:
            return {
                "success": False,
                "error": f"OpenAI API异常: {str(e)}"
            }

class ThirdPartyAPIClient(BaseLLMClient):
    """第三方API客户端"""
    
    def __init__(self, model_name: Optional[str] = None):
        self.config = get_third_party_config()
        super().__init__(model_name or self.config.get('model', 'gpt-3.5-turbo'))
        
        self.api_key = self.config.get('api_key', '')
        self.base_url = self.config.get('base_url', '').rstrip('/')
        self.timeout = self.config.get('timeout', 60)
        self.max_tokens = self.config.get('max_tokens', 4000)
        self.temperature = self.config.get('temperature', 0.7)
        
        # 检查必要配置
        if not self.api_key:
            raise ValueError("第三方API密钥未配置")
        if not self.base_url:
            raise ValueError("第三方API端点未配置")
        
        logger.info(f"初始化第三方API客户端: URL={self.base_url}, Model={self.model_name}")
    
    async def generate_completion(self, prompt: str, **kwargs) -> Dict[str, Any]:
        """生成文本补全 - 使用chat completions接口"""
        messages = [{"role": "user", "content": prompt}]
        result = await self.chat_completion(messages, **kwargs)
        
        # 转换格式以兼容原有接口
        if result.get("success"):
            message = result.get("message", {})
            content = message.get("content", "") if isinstance(message, dict) else str(message)
            return {
                "success": True,
                "response": content,
                "model": result.get("model", self.model_name),
                "usage": result.get("usage", {})
            }
        else:
            return result
    
    async def chat_completion(self, messages: List[Dict], **kwargs) -> Dict[str, Any]:
        """聊天补全"""
        try:
            # 根据您的示例，如果base_url已经包含完整路径，直接使用
            if self.base_url.endswith('/v1'):
                url = f"{self.base_url}/chat/completions"
            elif '/v1/chat/completions' in self.base_url:
                url = self.base_url
            else:
                # 默认追加路径
                url = f"{self.base_url}/v1/chat/completions"
            
            # 构建请求头 - 按照OpenAI标准格式
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # 构建请求体 - 完全按照OpenAI格式
            payload = {
                "model": self.model_name,
                "messages": messages,
                "max_tokens": kwargs.get("max_tokens", self.max_tokens),
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", 1.0),
                "stream": kwargs.get("stream", False)
            }
            
            # 移除None值以保持clean payload
            payload = {k: v for k, v in payload.items() if v is not None}
            
            logger.debug(f"发送请求到: {url}")
            logger.debug(f"请求头: Authorization=Bearer {self.api_key[:10]}...")
            logger.debug(f"请求体: {payload}")
            
            # 配置会话
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            connector = None
            if self.config.get('proxy'):
                connector = aiohttp.ProxyConnector(url=self.config['proxy'])
            
            # 发送请求 - 重试机制
            max_retries = self.config.get('retry_attempts', 3)
            for attempt in range(max_retries):
                try:
                    async with aiohttp.ClientSession(
                        connector=connector,
                        timeout=timeout
                    ) as session:
                        async with session.post(url, json=payload, headers=headers) as response:
                            response_text = await response.text()
                            logger.debug(f"接收到API响应 (状态码: {response.status}): {response_text}")
                            
                            if response.status == 200:
                                try:
                                    result = json.loads(response_text)
                                    
                                    # 检查返回格式
                                    if 'choices' in result and len(result['choices']) > 0:
                                        choice = result['choices'][0]
                                        
                                        # 处理message格式
                                        if 'message' in choice:
                                            message = choice['message']
                                            # 确保message有content
                                            if 'content' in message and message['content']:
                                                logger.debug("✅ 第三方API调用成功")
                                                return {
                                                    "success": True,
                                                    "message": message,
                                                    "model": result.get("model", self.model_name),
                                                    "usage": result.get("usage", {}),
                                                    "provider": self.config.get('provider', 'third_party'),
                                                    "attempt": attempt + 1
                                                }
                                            else:
                                                logger.warning(f"API返回空内容，尝试重试 ({attempt + 1}/{max_retries})")
                                                if attempt < max_retries - 1:
                                                    await asyncio.sleep(self.config.get('retry_delay', 1.0))
                                                    continue
                                    
                                    # 如果格式不正确，返回错误
                                    logger.error(f"API返回格式异常: {result}")
                                    return {
                                        "success": False,
                                        "error": "API返回格式异常",
                                        "details": str(result)
                                    }
                                    
                                except json.JSONDecodeError as e:
                                    logger.error(f"JSON解析失败: {e}")
                                    return {
                                        "success": False,
                                        "error": f"响应解析失败: {str(e)}",
                                        "raw_response": response_text
                                    }
                            else:
                                # 处理错误响应
                                try:
                                    error_data = json.loads(response_text)
                                    error_msg = error_data.get("error", {}).get("message", response_text)
                                except:
                                    error_msg = response_text
                                
                                logger.error(f"第三方API错误 {response.status}: {error_msg}")
                                return {
                                    "success": False,
                                    "error": f"第三方API错误: {response.status} - {error_msg}",
                                    "status_code": response.status,
                                    "details": error_msg
                                }
                                
                except asyncio.TimeoutError:
                    logger.warning(f"请求超时，尝试重试 ({attempt + 1}/{max_retries})")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(self.config.get('retry_delay', 1.0))
                        continue
                    else:
                        return {
                            "success": False,
                            "error": f"第三方API超时 (>{self.timeout}秒，重试{max_retries}次)"
                        }
                        
                except Exception as e:
                    logger.warning(f"请求异常，尝试重试 ({attempt + 1}/{max_retries}): {e}")
                    if attempt < max_retries - 1:
                        await asyncio.sleep(self.config.get('retry_delay', 1.0))
                        continue
                    else:
                        logger.error(f"第三方API异常: {e}")
                        return {
                            "success": False,
                            "error": f"第三方API异常: {str(e)}"
                        }
            
            # 如果所有重试都失败
            return {
                "success": False,
                "error": f"第三方API调用失败，已重试{max_retries}次"
            }
                        
        except Exception as e:
            logger.error(f"第三方API调用异常: {e}")
            return {
                "success": False,
                "error": f"第三方API异常: {str(e)}"
            }

class LLMManager:
    """大语言模型管理器"""
    
    def __init__(self, default_provider: str = "ollama"):
        self.default_provider = default_provider
        self.clients = {}
        self._init_clients()
    
    def _init_clients(self):
        """初始化客户端"""
        try:
            self.clients["ollama"] = OllamaClient()
            logger.info("Ollama客户端初始化成功")
        except Exception as e:
            logger.error(f"Ollama客户端初始化失败: {e}")
        
        try:
            if OPENAI_CONFIG['api_key']:
                self.clients["openai"] = OpenAIClient()
                logger.info("OpenAI客户端初始化成功")
        except Exception as e:
            logger.error(f"OpenAI客户端初始化失败: {e}")
        
        # 初始化第三方API客户端
        try:
            if is_third_party_enabled():
                self.clients["third_party"] = ThirdPartyAPIClient()
                logger.info("第三方API客户端初始化成功")
                # 如果第三方API启用，设置为默认提供商
                self.default_provider = "third_party"
        except Exception as e:
            logger.error(f"第三方API客户端初始化失败: {e}")
    
    def get_client(self, provider: Optional[str] = None) -> BaseLLMClient:
        """获取指定的客户端"""
        provider = provider or self.default_provider
        
        if provider not in self.clients:
            raise ValueError(f"不支持的提供商: {provider}")
        
        return self.clients[provider]
    
    async def generate_completion(self, prompt: str, provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """生成文本补全 - 支持自动回退"""
        target_provider = provider or self.default_provider
        # 统一按提供商配置对齐/收敛 max_tokens
        kwargs = self._apply_max_tokens_policy(kwargs, target_provider)
        
        try:
            client = self.get_client(target_provider)
            result = await client.generate_completion(prompt, **kwargs)
            
            # 如果第三方API失败，尝试回退到Ollama
            if not result.get("success") and target_provider == "third_party" and "ollama" in self.clients:
                logger.warning(f"第三方API失败，回退到Ollama: {result.get('error')}")
                ollama_client = self.clients["ollama"]
                result = await ollama_client.generate_completion(prompt, **kwargs)
                if result.get("success"):
                    result["fallback_provider"] = "ollama"
                    result["original_error"] = result.get('error')
            
            return result
        except Exception as e:
            # 如果出现异常且不是ollama，尝试回退
            if target_provider != "ollama" and "ollama" in self.clients:
                logger.warning(f"主要提供商异常，回退到Ollama: {e}")
                try:
                    ollama_client = self.clients["ollama"]
                    result = await ollama_client.generate_completion(prompt, **kwargs)
                    if result.get("success"):
                        result["fallback_provider"] = "ollama"
                        result["original_error"] = str(e)
                    return result
                except Exception as fallback_e:
                    logger.error(f"回退也失败: {fallback_e}")
            
            return {
                "success": False,
                "error": f"所有提供商都失败: {str(e)}"
            }

    async def chat_completion(self, messages: List[Dict], provider: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        """聊天补全 - 支持自动回退"""
        target_provider = provider or self.default_provider
        # 统一按提供商配置对齐/收敛 max_tokens
        kwargs = self._apply_max_tokens_policy(kwargs, target_provider)
        
        try:
            client = self.get_client(target_provider)
            result = await client.chat_completion(messages, **kwargs)
            
            # 如果第三方API失败，尝试回退到Ollama
            if not result.get("success") and target_provider == "third_party" and "ollama" in self.clients:
                logger.warning(f"第三方API失败，回退到Ollama: {result.get('error')}")
                ollama_client = self.clients["ollama"]
                result = await ollama_client.chat_completion(messages, **kwargs)
                if result.get("success"):
                    result["fallback_provider"] = "ollama"
                    result["original_error"] = result.get('error')
            
            return result
        except Exception as e:
            # 如果出现异常且不是ollama，尝试回退
            if target_provider != "ollama" and "ollama" in self.clients:
                logger.warning(f"主要提供商异常，回退到Ollama: {e}")
                try:
                    ollama_client = self.clients["ollama"]
                    result = await ollama_client.chat_completion(messages, **kwargs)
                    if result.get("success"):
                        result["fallback_provider"] = "ollama"
                        result["original_error"] = str(e)
                    return result
                except Exception as fallback_e:
                    logger.error(f"回退也失败: {fallback_e}")
            
            return {
                "success": False,
                "error": f"所有提供商都失败: {str(e)}"
            }
    
    async def test_connection(self, provider: Optional[str] = None) -> Dict[str, Any]:
        """测试连接"""
        try:
            result = await self.generate_completion(
                "Hello, this is a test message.",
                provider=provider,
                max_tokens=50
            )
            return {
                "success": result.get("success", False),
                "provider": provider or self.default_provider,
                "message": "连接测试成功" if result.get("success") else result.get("error", "连接失败")
            }
        except Exception as e:
            return {
                "success": False,
                "provider": provider or self.default_provider,
                "message": f"连接测试异常: {str(e)}"
            }

    def _apply_max_tokens_policy(self, kwargs: Dict[str, Any], provider: str) -> Dict[str, Any]:
        """根据当前提供商的配置对齐/收敛 max_tokens 参数。"""
        try:
            if provider == "openai":
                default_max = OPENAI_CONFIG.get("max_tokens", 4000)
            elif provider == "third_party":
                config = get_third_party_config()
                default_max = config.get("max_tokens", 4000)
            elif provider == "ollama":
                default_max = OLLAMA_CONFIG.get("max_tokens", 2000)
            else:
                # 其他提供商（如anthropic）按其配置，若无则给保守默认
                default_max = ANTHROPIC_CONFIG.get("max_tokens", 4000)
        except Exception:
            default_max = 2000

        requested = kwargs.get("max_tokens")
        if requested is None:
            aligned = default_max
        else:
            aligned = min(int(requested), int(default_max))

        # 返回新的 kwargs，避免污染上游引用
        new_kwargs = {k: v for k, v in kwargs.items() if k != "max_tokens"}
        new_kwargs["max_tokens"] = aligned
        return new_kwargs

# 全局LLM管理器实例
llm_manager = LLMManager()

async def get_llm_response(prompt: str, provider: Optional[str] = None, **kwargs) -> str:
    """获取LLM响应的便捷函数"""
    result = await llm_manager.generate_completion(prompt, provider, **kwargs)
    if result.get("success"):
        return result.get("response", "")
    else:
        raise Exception(f"LLM调用失败: {result.get('error', '未知错误')}")

async def get_chat_response(messages: List[Dict], provider: Optional[str] = None, **kwargs) -> str:
    """获取聊天响应的便捷函数"""
    result = await llm_manager.chat_completion(messages, provider, **kwargs)
    if result.get("success"):
        message = result.get("message", {})
        return message.get("content", "") if isinstance(message, dict) else str(message)
    else:
        raise Exception(f"聊天调用失败: {result.get('error', '未知错误')}")
