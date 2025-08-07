from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Union, Callable
import logging
import asyncio
from datetime import datetime
from enum import Enum

logger = logging.getLogger(__name__)

class WorkflowStatus(Enum):
    """工作流状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class StepStatus(Enum):
    """步骤状态枚举"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

class WorkflowStep:
    """工作流步骤"""
    
    def __init__(self, name: str, handler: Callable, dependencies: List[str] = None, 
                 retry_count: int = 3, timeout: int = 300, critical: bool = True):
        self.name = name
        self.handler = handler
        self.dependencies = dependencies or []
        self.retry_count = retry_count
        self.timeout = timeout
        self.critical = critical
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.execution_time = None
    
    def reset(self):
        """重置步骤状态"""
        self.status = StepStatus.PENDING
        self.result = None
        self.error = None
        self.start_time = None
        self.end_time = None
        self.execution_time = None

class BaseWorkflow(ABC):
    """工作流基类"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.steps: Dict[str, WorkflowStep] = {}
        self.execution_order = []
        self.status = WorkflowStatus.PENDING
        self.context = {}
        self.results = {}
        self.errors = []
        self.start_time = None
        self.end_time = None
        self.execution_time = None
        self.max_parallel_steps = 3
    
    def add_step(self, step: WorkflowStep):
        """添加工作流步骤"""
        self.steps[step.name] = step
        logger.info(f"工作流 {self.name} 添加步骤: {step.name}")
    
    def set_execution_order(self, order: List[str]):
        """设置执行顺序"""
        # 验证所有步骤都存在
        for step_name in order:
            if step_name not in self.steps:
                raise ValueError(f"步骤不存在: {step_name}")
        
        self.execution_order = order
        logger.info(f"工作流 {self.name} 设置执行顺序: {order}")
    
    async def execute(self, input_data: Any, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行工作流"""
        logger.info(f"开始执行工作流: {self.name}")
        
        self.status = WorkflowStatus.RUNNING
        self.start_time = datetime.now()
        self.context = context or {}
        self.context["input_data"] = input_data
        
        try:
            # 重置所有步骤
            for step in self.steps.values():
                step.reset()
            
            # 按顺序执行步骤
            if self.execution_order:
                await self._execute_sequential()
            else:
                await self._execute_dependency_based()
            
            self.status = WorkflowStatus.COMPLETED
            self.end_time = datetime.now()
            self.execution_time = (self.end_time - self.start_time).total_seconds()
            
            logger.info(f"工作流 {self.name} 执行完成，耗时: {self.execution_time:.2f}秒")
            
            return {
                "workflow": self.name,
                "status": self.status.value,
                "execution_time": self.execution_time,
                "results": self.results,
                "context": self.context,
                "errors": self.errors,
                "success": self.status == WorkflowStatus.COMPLETED
            }
            
        except Exception as e:
            self.status = WorkflowStatus.FAILED
            self.end_time = datetime.now()
            self.execution_time = (self.end_time - self.start_time).total_seconds()
            
            error_info = {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
                "step": "workflow_execution"
            }
            self.errors.append(error_info)
            
            logger.error(f"工作流 {self.name} 执行失败: {e}")
            
            return {
                "workflow": self.name,
                "status": self.status.value,
                "execution_time": self.execution_time,
                "error": str(e),
                "errors": self.errors,
                "partial_results": self.results,
                "success": False
            }
    
    async def _execute_sequential(self):
        """按顺序执行步骤"""
        for step_name in self.execution_order:
            step = self.steps[step_name]
            
            try:
                await self._execute_step(step)
                
                # 如果关键步骤失败，停止执行
                if step.status == StepStatus.FAILED and step.critical:
                    raise Exception(f"关键步骤失败: {step_name}")
                    
            except Exception as e:
                if step.critical:
                    raise
                else:
                    logger.warning(f"非关键步骤失败，继续执行: {step_name}, 错误: {e}")
    
    async def _execute_dependency_based(self):
        """基于依赖关系执行步骤"""
        completed_steps = set()
        
        while len(completed_steps) < len(self.steps):
            # 找到可以执行的步骤
            ready_steps = []
            
            for step_name, step in self.steps.items():
                if (step_name not in completed_steps and 
                    step.status == StepStatus.PENDING and
                    all(dep in completed_steps for dep in step.dependencies)):
                    ready_steps.append(step)
            
            if not ready_steps:
                # 没有可执行的步骤，可能有循环依赖
                pending_steps = [name for name, step in self.steps.items() 
                               if step.status == StepStatus.PENDING]
                if pending_steps:
                    raise Exception(f"存在循环依赖或未满足的依赖: {pending_steps}")
                break
            
            # 并行执行准备好的步骤
            if len(ready_steps) > self.max_parallel_steps:
                ready_steps = ready_steps[:self.max_parallel_steps]
            
            await asyncio.gather(*[self._execute_step(step) for step in ready_steps])
            
            # 更新完成的步骤
            for step in ready_steps:
                if step.status in [StepStatus.COMPLETED, StepStatus.FAILED, StepStatus.SKIPPED]:
                    completed_steps.add(step.name)
                    
                    # 如果关键步骤失败，停止执行
                    if step.status == StepStatus.FAILED and step.critical:
                        raise Exception(f"关键步骤失败: {step.name}")
    
    async def _execute_step(self, step: WorkflowStep):
        """执行单个步骤"""
        logger.info(f"执行步骤: {step.name}")
        
        step.status = StepStatus.RUNNING
        step.start_time = datetime.now()
        
        for attempt in range(step.retry_count + 1):
            try:
                # 执行步骤处理器
                if asyncio.iscoroutinefunction(step.handler):
                    result = await asyncio.wait_for(
                        step.handler(self.context), 
                        timeout=step.timeout
                    )
                else:
                    result = step.handler(self.context)
                
                step.result = result
                step.status = StepStatus.COMPLETED
                step.end_time = datetime.now()
                step.execution_time = (step.end_time - step.start_time).total_seconds()
                
                # 更新工作流结果和上下文
                self.results[step.name] = result
                if isinstance(result, dict):
                    self.context.update(result)
                
                logger.info(f"步骤 {step.name} 执行成功，耗时: {step.execution_time:.2f}秒")
                return
                
            except asyncio.TimeoutError:
                error_msg = f"步骤 {step.name} 执行超时 (第{attempt + 1}次尝试)"
                logger.warning(error_msg)
                
                if attempt < step.retry_count:
                    await asyncio.sleep(min(2 ** attempt, 10))  # 指数退避
                    continue
                else:
                    step.error = f"超时: {step.timeout}秒"
                    break
                    
            except Exception as e:
                error_msg = f"步骤 {step.name} 执行失败: {str(e)} (第{attempt + 1}次尝试)"
                logger.warning(error_msg)
                
                if attempt < step.retry_count:
                    await asyncio.sleep(min(2 ** attempt, 10))  # 指数退避
                    continue
                else:
                    step.error = str(e)
                    break
        
        # 所有重试都失败了
        step.status = StepStatus.FAILED
        step.end_time = datetime.now()
        step.execution_time = (step.end_time - step.start_time).total_seconds()
        
        error_info = {
            "step": step.name,
            "error": step.error,
            "timestamp": step.end_time.isoformat(),
            "execution_time": step.execution_time
        }
        self.errors.append(error_info)
        
        logger.error(f"步骤 {step.name} 最终执行失败: {step.error}")
    
    def get_step_status(self) -> Dict[str, Any]:
        """获取所有步骤状态"""
        return {
            step_name: {
                "status": step.status.value,
                "execution_time": step.execution_time,
                "error": step.error
            }
            for step_name, step in self.steps.items()
        }
    
    def get_workflow_status(self) -> Dict[str, Any]:
        """获取工作流状态"""
        return {
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "execution_time": self.execution_time,
            "steps_total": len(self.steps),
            "steps_completed": sum(1 for step in self.steps.values() 
                                 if step.status == StepStatus.COMPLETED),
            "steps_failed": sum(1 for step in self.steps.values() 
                              if step.status == StepStatus.FAILED),
            "errors_count": len(self.errors)
        }
    
    def get_workflow_info(self) -> Dict[str, Any]:
        """获取工作流信息 - 兼容测试"""
        return {
            "name": self.name,
            "description": self.description,
            "steps": list(self.steps.keys()),
            "execution_order": self.execution_order
        }
    
    async def cancel(self):
        """取消工作流执行"""
        self.status = WorkflowStatus.CANCELLED
        logger.info(f"工作流 {self.name} 已取消")
    
    @abstractmethod
    async def setup_workflow(self):
        """设置工作流步骤 - 子类必须实现"""
        pass

class WorkflowManager:
    """工作流管理器"""
    
    def __init__(self):
        self.workflows: Dict[str, BaseWorkflow] = {}
        self.running_workflows: Dict[str, asyncio.Task] = {}
    
    def register_workflow(self, workflow: BaseWorkflow):
        """注册工作流"""
        self.workflows[workflow.name] = workflow
        logger.info(f"工作流已注册: {workflow.name}")
    
    async def execute_workflow(self, workflow_name: str, input_data: Any, 
                             context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """执行工作流"""
        if workflow_name not in self.workflows:
            raise ValueError(f"工作流不存在: {workflow_name}")
        
        workflow = self.workflows[workflow_name]
        
        # 设置工作流
        await workflow.setup_workflow()
        
        # 执行工作流
        task = asyncio.create_task(workflow.execute(input_data, context))
        self.running_workflows[workflow_name] = task
        
        try:
            result = await task
            return result
        finally:
            # 清理任务
            if workflow_name in self.running_workflows:
                del self.running_workflows[workflow_name]
    
    async def cancel_workflow(self, workflow_name: str):
        """取消工作流"""
        if workflow_name in self.running_workflows:
            task = self.running_workflows[workflow_name]
            task.cancel()
            
            if workflow_name in self.workflows:
                await self.workflows[workflow_name].cancel()
    
    def get_workflow_status(self, workflow_name: str) -> Optional[Dict[str, Any]]:
        """获取工作流状态"""
        if workflow_name in self.workflows:
            return self.workflows[workflow_name].get_workflow_status()
        return None
    
    def list_workflows(self) -> List[str]:
        """列出所有工作流"""
        return list(self.workflows.keys())
    
    def list_running_workflows(self) -> List[str]:
        """列出正在运行的工作流"""
        return list(self.running_workflows.keys())

# 全局工作流管理器实例
workflow_manager = WorkflowManager()
