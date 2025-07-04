import logging
import os
import time
import json
import threading
import queue
from pathlib import Path
from enum import Enum
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
import uuid

from config import BASE_DIR

logger = logging.getLogger(__name__)

# 任务状态枚举
class TaskStatus(str, Enum):
    PENDING = "pending"       # 等待中
    PROCESSING = "processing" # 处理中
    COMPLETED = "completed"   # 已完成
    FAILED = "failed"         # 失败
    CANCELLED = "cancelled"   # 已取消

# 任务优先级枚举
class TaskPriority(int, Enum):
    LOW = 0
    NORMAL = 1
    HIGH = 2
    URGENT = 3

# 任务类型枚举
class TaskType(str, Enum):
    MODEL_TRAINING = "model_training"
    AUDIO_SYNTHESIS = "audio_synthesis"
    VIDEO_GENERATION = "video_generation"
    FILE_CLEANUP = "file_cleanup"

class Task:
    def __init__(
        self, 
        task_id: str,
        task_type: TaskType,
        params: Dict[str, Any],
        username: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Optional[Callable] = None
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.params = params
        self.username = username
        self.priority = priority
        self.status = TaskStatus.PENDING
        self.created_at = datetime.now()
        self.started_at = None
        self.completed_at = None
        self.result = None
        self.error = None
        self.progress = 0
        self.callback = callback
        self.timeout = 3600  # 默认超时时间：1小时
        self.retry_count = 0  # 重试次数
        self.max_retries = 3  # 最大重试次数
        self.resource_usage = {  # 资源使用情况
            "cpu": 1.0,  # CPU核心数
            "memory": 512,  # 内存MB
            "gpu": 0.0,  # GPU使用量
        }

    def to_dict(self) -> Dict[str, Any]:
        """将任务转换为字典表示"""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "username": self.username,
            "priority": self.priority,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "progress": self.progress,
            "result": self.result,
            "error": self.error
        }

    def __lt__(self, other):
        """用于优先级队列的比较"""
        if self.priority != other.priority:
            return self.priority > other.priority  # 高优先级先执行
        return self.created_at < other.created_at  # 同优先级按创建时间排序

class TaskQueue:
    def __init__(self, max_concurrent_tasks: int = 2):
        self.task_queue = queue.PriorityQueue()
        self.active_tasks: Dict[str, Task] = {}
        self.completed_tasks: Dict[str, Task] = {}
        self.max_concurrent_tasks = max_concurrent_tasks
        self.lock = threading.Lock()
        self.task_db_path = BASE_DIR / "tasks.json"
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.timeout_thread = threading.Thread(target=self._check_timeouts, daemon=True)
        self.running = False
        
        # 资源管理
        self.available_resources = {
            "cpu": os.cpu_count() or 4,  # 可用CPU核心数
            "memory": 8192,  # 可用内存MB
            "gpu": 1.0,  # 可用GPU资源
        }
        self.used_resources = {
            "cpu": 0.0,
            "memory": 0,
            "gpu": 0.0,
        }
        
        self.load_tasks()

    def start(self):
        """启动任务队列处理线程"""
        self.running = True
        self.worker_thread.start()
        self.timeout_thread.start()
        logger.info("任务队列服务已启动")

    def stop(self):
        """停止任务队列处理线程"""
        self.running = False
        if self.worker_thread.is_alive():
            self.worker_thread.join(timeout=5.0)
        if self.timeout_thread.is_alive():
            self.timeout_thread.join(timeout=5.0)
        logger.info("任务队列服务已停止")

    def add_task(self, task: Task) -> str:
        """添加新任务到队列"""
        with self.lock:
            self.task_queue.put(task)
            self.save_tasks()
            logger.info(f"已添加任务 {task.task_id} 到队列")
        return task.task_id

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        with self.lock:
            # 检查活动任务
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                if task.status == TaskStatus.PROCESSING:
                    logger.warning(f"无法取消正在处理的任务 {task_id}")
                    return False
                task.status = TaskStatus.CANCELLED
                self.completed_tasks[task_id] = task
                del self.active_tasks[task_id]
                self.save_tasks()
                logger.info(f"已取消任务 {task_id}")
                return True
            
            # 检查等待中的任务
            new_queue = queue.PriorityQueue()
            found = False
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task.task_id == task_id:
                    task.status = TaskStatus.CANCELLED
                    self.completed_tasks[task_id] = task
                    found = True
                    logger.info(f"已取消等待中的任务 {task_id}")
                else:
                    new_queue.put(task)
            
            # 恢复未取消的任务
            self.task_queue = new_queue
            
            if found:
                self.save_tasks()
                return True
                
            logger.warning(f"未找到任务 {task_id}")
            return False

    def get_task(self, task_id: str) -> Optional[Task]:
        """获取任务信息"""
        with self.lock:
            if task_id in self.active_tasks:
                return self.active_tasks[task_id]
            if task_id in self.completed_tasks:
                return self.completed_tasks[task_id]
            
            # 检查等待中的任务
            tasks = []
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task.task_id == task_id:
                    result = task
                tasks.append(task)
            
            # 恢复任务队列
            for task in tasks:
                self.task_queue.put(task)
                
            if 'result' in locals():
                return result
                
            return None

    def get_user_tasks(self, username: str) -> List[Dict[str, Any]]:
        """获取用户的所有任务"""
        with self.lock:
            result = []
            
            # 检查活动任务
            for task_id, task in self.active_tasks.items():
                if task.username == username:
                    result.append(task.to_dict())
            
            # 检查已完成任务
            for task_id, task in self.completed_tasks.items():
                if task.username == username:
                    result.append(task.to_dict())
            
            # 检查等待中的任务
            tasks = []
            while not self.task_queue.empty():
                task = self.task_queue.get()
                if task.username == username:
                    result.append(task.to_dict())
                tasks.append(task)
            
            # 恢复任务队列
            for task in tasks:
                self.task_queue.put(task)
                
            return result

    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        with self.lock:
            pending_count = self.task_queue.qsize()
            active_count = len(self.active_tasks)
            completed_count = len(self.completed_tasks)
            
            # 按任务类型统计
            type_counts = {}
            for task_type in TaskType:
                type_counts[task_type.value] = {
                    "pending": 0,
                    "processing": 0,
                    "completed": 0,
                    "failed": 0,
                    "cancelled": 0
                }
            
            # 统计等待中的任务
            tasks = []
            while not self.task_queue.empty():
                task = self.task_queue.get()
                type_counts[task.task_type]["pending"] += 1
                tasks.append(task)
            
            # 恢复任务队列
            for task in tasks:
                self.task_queue.put(task)
            
            # 统计活动任务
            for task in self.active_tasks.values():
                type_counts[task.task_type]["processing"] += 1
            
            # 统计已完成任务
            for task in self.completed_tasks.values():
                if task.status == TaskStatus.COMPLETED:
                    type_counts[task.task_type]["completed"] += 1
                elif task.status == TaskStatus.FAILED:
                    type_counts[task.task_type]["failed"] += 1
                elif task.status == TaskStatus.CANCELLED:
                    type_counts[task.task_type]["cancelled"] += 1
            
            return {
                "pending_count": pending_count,
                "active_count": active_count,
                "completed_count": completed_count,
                "max_concurrent_tasks": self.max_concurrent_tasks,
                "type_counts": type_counts
            }

    def update_task_progress(self, task_id: str, progress: float, result: Any = None, error: str = None) -> bool:
        """更新任务进度"""
        with self.lock:
            if task_id in self.active_tasks:
                task = self.active_tasks[task_id]
                task.progress = min(100.0, max(0.0, progress))
                
                if progress >= 100.0:
                    task.status = TaskStatus.COMPLETED
                    task.completed_at = datetime.now()
                    task.result = result
                    self.completed_tasks[task_id] = task
                    
                    # 释放资源
                    self._release_resources(task)
                    del self.active_tasks[task_id]
                elif error:
                    task.status = TaskStatus.FAILED
                    task.completed_at = datetime.now()
                    task.error = error
                    self.completed_tasks[task_id] = task
                    
                    # 释放资源
                    self._release_resources(task)
                    del self.active_tasks[task_id]
                
                self.save_tasks()
                return True
            
            logger.warning(f"未找到活动任务 {task_id}")
            return False

    def set_max_concurrent_tasks(self, count: int) -> bool:
        """设置最大并发任务数"""
        if count < 1:
            return False
        
        with self.lock:
            self.max_concurrent_tasks = count
            return True

    def save_tasks(self):
        """保存任务状态到文件"""
        try:
            data = {
                "active_tasks": {task_id: task.to_dict() for task_id, task in self.active_tasks.items()},
                "completed_tasks": {task_id: task.to_dict() for task_id, task in self.completed_tasks.items()}
            }
            
            with open(self.task_db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"保存任务状态失败: {str(e)}")

    def load_tasks(self):
        """从文件加载任务状态"""
        if not self.task_db_path.exists():
            return
        
        try:
            with open(self.task_db_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # 恢复已完成任务
            for task_id, task_data in data.get("completed_tasks", {}).items():
                task = self._dict_to_task(task_data)
                self.completed_tasks[task_id] = task
                
            # 恢复活动任务（仅加载PENDING状态的任务，其他状态视为失败）
            for task_id, task_data in data.get("active_tasks", {}).items():
                task = self._dict_to_task(task_data)
                if task.status == TaskStatus.PENDING:
                    self.task_queue.put(task)
                else:
                    task.status = TaskStatus.FAILED
                    task.error = "系统重启导致任务中断"
                    self.completed_tasks[task_id] = task
                    
            logger.info(f"已加载 {len(self.completed_tasks)} 个已完成任务")
        except Exception as e:
            logger.error(f"加载任务状态失败: {str(e)}")

    def _dict_to_task(self, task_data: Dict[str, Any]) -> Task:
        """将字典转换为任务对象"""
        task = Task(
            task_id=task_data["task_id"],
            task_type=task_data["task_type"],
            params={},  # 参数不保存
            username=task_data["username"],
            priority=task_data.get("priority", TaskPriority.NORMAL)
        )
        
        task.status = task_data["status"]
        task.created_at = datetime.fromisoformat(task_data["created_at"])
        
        if task_data.get("started_at"):
            task.started_at = datetime.fromisoformat(task_data["started_at"])
            
        if task_data.get("completed_at"):
            task.completed_at = datetime.fromisoformat(task_data["completed_at"])
            
        task.progress = task_data.get("progress", 0)
        task.result = task_data.get("result")
        task.error = task_data.get("error")
        
        return task

    def _check_timeouts(self):
        """检查任务超时的工作线程"""
        while self.running:
            try:
                with self.lock:
                    current_time = datetime.now()
                    timed_out_tasks = []
                    
                    # 检查活动任务是否超时
                    for task_id, task in self.active_tasks.items():
                        if task.started_at and task.timeout > 0:
                            elapsed_seconds = (current_time - task.started_at).total_seconds()
                            if elapsed_seconds > task.timeout:
                                timed_out_tasks.append(task_id)
                    
                    # 处理超时任务
                    for task_id in timed_out_tasks:
                        task = self.active_tasks[task_id]
                        
                        # 检查是否可以重试
                        if task.retry_count < task.max_retries:
                            # 重新加入队列进行重试
                            task.retry_count += 1
                            task.status = TaskStatus.PENDING
                            task.started_at = None
                            task.progress = 0
                            self.task_queue.put(task)
                            logger.warning(f"任务 {task_id} 超时，进行第 {task.retry_count} 次重试")
                            
                            # 释放资源
                            self._release_resources(task)
                            del self.active_tasks[task_id]
                        else:
                            # 超过最大重试次数，标记为失败
                            task.status = TaskStatus.FAILED
                            task.completed_at = current_time
                            task.error = f"任务超时，已重试 {task.retry_count} 次"
                            self.completed_tasks[task_id] = task
                            
                            # 释放资源
                            self._release_resources(task)
                            del self.active_tasks[task_id]
                            logger.error(f"任务 {task_id} 超时且超过最大重试次数，标记为失败")
                    
                    if timed_out_tasks:
                        self.save_tasks()
                
                # 每10秒检查一次
                time.sleep(10)
                
            except Exception as e:
                logger.error(f"超时检查线程异常: {str(e)}")
                time.sleep(30)

    def _allocate_resources(self, task: Task) -> bool:
        """为任务分配资源"""
        # 检查是否有足够的资源
        for resource, amount in task.resource_usage.items():
            if self.used_resources[resource] + amount > self.available_resources[resource]:
                return False
        
        # 分配资源
        for resource, amount in task.resource_usage.items():
            self.used_resources[resource] += amount
            
        return True

    def _release_resources(self, task: Task):
        """释放任务占用的资源"""
        for resource, amount in task.resource_usage.items():
            self.used_resources[resource] = max(0, self.used_resources[resource] - amount)

    def _process_queue(self):
        """处理任务队列的工作线程"""
        while self.running:
            try:
                # 检查是否可以处理更多任务
                with self.lock:
                    if len(self.active_tasks) >= self.max_concurrent_tasks or self.task_queue.empty():
                        time.sleep(1)
                        continue
                    
                    # 获取下一个任务
                    task = self.task_queue.get(block=False)
                    
                    # 检查资源是否足够
                    if not self._allocate_resources(task):
                        # 资源不足，放回队列
                        self.task_queue.put(task)
                        logger.info(f"资源不足，任务 {task.task_id} 重新排队")
                        time.sleep(5)
                        continue
                    
                    # 更新任务状态
                    task.status = TaskStatus.PROCESSING
                    task.started_at = datetime.now()
                    self.active_tasks[task.task_id] = task
                    self.save_tasks()
                
                # 执行任务回调
                if task.callback:
                    try:
                        result = task.callback(task)
                        self.update_task_progress(task.task_id, 100.0, result=result)
                    except Exception as e:
                        logger.error(f"任务 {task.task_id} 执行失败: {str(e)}")
                        
                        # 检查是否可以重试
                        with self.lock:
                            if task.retry_count < task.max_retries:
                                # 重新加入队列进行重试
                                task.retry_count += 1
                                task.status = TaskStatus.PENDING
                                task.started_at = None
                                task.progress = 0
                                self.task_queue.put(task)
                                logger.warning(f"任务 {task.task_id} 执行失败，进行第 {task.retry_count} 次重试")
                                
                                # 释放资源
                                self._release_resources(task)
                                del self.active_tasks[task.task_id]
                                self.save_tasks()
                            else:
                                # 超过最大重试次数，标记为失败
                                self.update_task_progress(task.task_id, 0.0, error=f"{str(e)}，已重试 {task.retry_count} 次")
                else:
                    # 没有回调的任务直接标记为完成
                    self.update_task_progress(task.task_id, 100.0)
                    
            except queue.Empty:
                time.sleep(1)
            except Exception as e:
                logger.error(f"任务处理线程异常: {str(e)}")
                time.sleep(5)

# 创建全局任务队列实例
task_queue = TaskQueue()

class TaskService:
    def __init__(self):
        self.task_queue = task_queue
        
    def start(self):
        """启动任务队列服务"""
        self.task_queue.start()
        
    def stop(self):
        """停止任务队列服务"""
        self.task_queue.stop()
        
    def create_task(
        self,
        task_type: TaskType,
        params: Dict[str, Any],
        username: str,
        priority: TaskPriority = TaskPriority.NORMAL,
        callback: Optional[Callable] = None
    ) -> str:
        """创建新任务"""
        task_id = str(uuid.uuid4())
        task = Task(
            task_id=task_id,
            task_type=task_type,
            params=params,
            username=username,
            priority=priority,
            callback=callback
        )
        return self.task_queue.add_task(task)
        
    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        return self.task_queue.cancel_task(task_id)
        
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """获取任务信息"""
        task = self.task_queue.get_task(task_id)
        if task:
            return task.to_dict()
        return None
        
    def get_user_tasks(self, username: str) -> List[Dict[str, Any]]:
        """获取用户的所有任务"""
        return self.task_queue.get_user_tasks(username)
        
    def get_queue_status(self) -> Dict[str, Any]:
        """获取队列状态"""
        return self.task_queue.get_queue_status()
        
    def update_task_progress(self, task_id: str, progress: float, result: Any = None, error: str = None) -> bool:
        """更新任务进度"""
        return self.task_queue.update_task_progress(task_id, progress, result, error)
        
    def set_max_concurrent_tasks(self, count: int) -> bool:
        """设置最大并发任务数"""
        return self.task_queue.set_max_concurrent_tasks(count) 