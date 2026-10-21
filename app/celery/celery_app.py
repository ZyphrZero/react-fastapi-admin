"""
Celery应用配置和实例创建

Author: bixuejun(bxjgood@163.com)
Date: 2025-12-14 11:45:00
"""

import errno
import os
import threading
import subprocess
import sys
import socket
import tempfile
import json
from celery import Celery
from kombu import Queue

from app.settings.config import settings
from app.tasks.celery_config import BEAT_SCHEDULE, TASK_MODULES, TASK_ROUTES
from app.utils.log_control import logger


def get_redis_url(db_number: int=settings.REDIS_DB) -> str:
    """
    构建Redis连接URL
    
    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2025-12-14 11:45:00
    Args:
        无
        
    Returns:
        str: Redis连接URL
    """
    redis_host = settings.REDIS_HOST
    redis_port = settings.REDIS_PORT
    redis_password = settings.REDIS_PASSWORD
    redis_db = db_number
    
    if redis_password:
        return f"redis://:{redis_password}@{redis_host}:{redis_port}/{redis_db}"
    else:
        return f"redis://{redis_host}:{redis_port}/{redis_db}"


# 创建Celery应用实例
celery_app = Celery(
    'celery_app',
    broker=get_redis_url(),
    backend=get_redis_url(settings.REDIS_DB+1),
)

# Celery配置
celery_app.conf.update(
    # 任务序列化格式
    task_serializer='json',
    # 结果序列化格式
    result_serializer='json',
    # 接受的内容类型
    accept_content=['json'],
    # broker 连接池禁用（每次投递独立短连接）：api 进程内嵌 worker（线程 + prefork 池）与
    # FastAPI handler 的 send_task 共享连接池存在竞态，消息可能静默丢失；redis 同网建连开销 ~1ms 可接受。
    broker_pool_limit=0,
    # 时区设置
    timezone='Asia/Shanghai',
    # 不使用UTC时间
    enable_utc=False,
    # 任务结果过期时间（秒）
    result_expires=3600,
    # 任务执行结果是否持久化
    result_persistent=True,
    # 任务发送后是否立即确认
    task_acks_late=True,
    # 每个worker预取任务数量
    worker_prefetch_multiplier=4,
    # 任务限流
    task_time_limit=3600,  # 硬超时（秒）
    task_soft_time_limit=3000,  # 软超时（秒）
    # 队列配置（列表经 settings.CELERY_QUEUES 驱动可裁剪）
    task_queues=tuple(Queue(name) for name in settings.celery_queues),
    # 默认队列
    task_default_queue='default',
    task_default_exchange='tasks',
    task_default_routing_key='task.default',
    # Worker配置
    worker_max_tasks_per_child=1000,  # 每个worker子进程最多执行任务数
    worker_disable_rate_limits=False,
    # 日志配置
    worker_hijack_root_logger=False,
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s] [%(task_name)s(%(task_id)s)] %(message)s',
    # Beat调度器配置
    beat_schedule_filename='celery-beat-schedule',
)

# 业务配置单独维护，任务模块立即导入以兼容进程内任务调用与独立 worker。
celery_app.conf.update(task_routes=TASK_ROUTES, beat_schedule=BEAT_SCHEDULE)
celery_app.autodiscover_tasks(TASK_MODULES, related_name=None, force=True)


# Worker线程引用
_worker_thread = None
_worker_process = None
_beat_thread = None
_beat_process = None
_beat_lock_acquired = False
# 锁/调度文件名带项目前缀：脚手架派生的多个项目同机并发内嵌启动 beat 时互不互抢
_beat_lock_path = os.path.join(
    tempfile.gettempdir(), f"{settings.PROJECT_NAME.lower().replace(' ', '-')}_celery_beat.lock"
)
_beat_schedule_path = os.path.join(
    tempfile.gettempdir(), f"{settings.PROJECT_NAME.lower().replace(' ', '-')}-celery-beat-schedule"
)


def _is_process_alive(pid: int) -> bool:
    """
    检查指定进程是否存在，不向进程发送实际信号。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2026-08-16 21:55:23
    Args:
        pid: 待检查的进程 ID。

    Returns:
        bool: 进程存在时返回 True，否则返回 False。
    """
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError as exc:
        if getattr(exc, "winerror", None) == 87 or exc.errno == errno.ESRCH:
            return False
        raise
    except SystemError:
        # Windows 下 os.kill(pid, 0) 对已退出进程可能包装为 SystemError。
        if sys.platform == "win32":
            return False
        raise


def _read_beat_lock_owner() -> dict:
    """Read lock owner data while staying compatible with the old pid-only file."""
    try:
        with open(_beat_lock_path, "r", encoding="utf-8") as lock_file:
            raw_owner = lock_file.read().strip()
    except OSError:
        return {"pid": 0, "hostname": ""}

    if not raw_owner:
        return {"pid": 0, "hostname": ""}

    try:
        owner = json.loads(raw_owner)
        return {
            "pid": int(owner.get("pid") or 0),
            "hostname": str(owner.get("hostname") or ""),
        }
    except (json.JSONDecodeError, TypeError, ValueError):
        try:
            return {"pid": int(raw_owner), "hostname": ""}
        except ValueError:
            return {"pid": 0, "hostname": ""}


def _is_beat_lock_owner_alive(owner: dict) -> bool:
    """Check whether the lock owner still represents a live local process."""
    owner_hostname = owner.get("hostname")
    if owner_hostname and owner_hostname != socket.gethostname():
        return False
    return _is_process_alive(int(owner.get("pid") or 0))


def _try_acquire_beat_lock() -> bool:
    """Acquire a host-local lock so only one Granian worker starts Celery beat."""
    global _beat_lock_acquired

    while True:
        try:
            lock_fd = os.open(_beat_lock_path, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(lock_fd, "w", encoding="utf-8") as lock_file:
                lock_file.write(json.dumps({"pid": os.getpid(), "hostname": socket.gethostname()}))
            _beat_lock_acquired = True
            return True
        except FileExistsError:
            owner = _read_beat_lock_owner()

            if _is_beat_lock_owner_alive(owner):
                logger.info(f"Celery beat 已由进程 {owner['pid']} 启动，当前进程跳过启动")
                return False

            try:
                os.remove(_beat_lock_path)
                logger.warning(f"清理 Celery beat 过期锁文件: {_beat_lock_path}, owner={owner}")
            except FileNotFoundError:
                continue
            except OSError as e:
                logger.warning(f"Celery beat 锁文件被占用，当前进程跳过启动: {e}")
                return False


def _release_beat_lock() -> None:
    """Release the Celery beat process lock owned by this process."""
    global _beat_lock_acquired

    if not _beat_lock_acquired:
        return

    try:
        os.remove(_beat_lock_path)
    except FileNotFoundError:
        pass
    except OSError as e:
        logger.warning(f"释放 Celery beat 锁文件失败: {e}")
    finally:
        _beat_lock_acquired = False


def start_celery_worker(concurrency: int = None):
    """
    在后台线程启动Celery worker

    并发池按操作系统自动选择：Windows 下使用 solo pool（兼容性最好，单执行槽，
    concurrency 参数不生效）；Linux 下使用 prefork pool（concurrency 参数生效）。

    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2025-12-14 11:45:00
    Args:
        concurrency: worker 并发数，None 时取 settings.CELERY_WORKER_CONCURRENCY

    Returns:
        无
    """
    global _worker_thread, _worker_process

    if _worker_thread is not None and _worker_thread.is_alive():
        logger.warning("⚠️ Celery worker 已经在运行中")
        return

    if concurrency is None:
        concurrency = settings.CELERY_WORKER_CONCURRENCY

    def run_worker():
        """在子进程中运行worker"""
        try:
            logger.info("🚀 正在启动 Celery worker...")

            # 使用subprocess启动worker进程
            worker_hostname = f"celery_worker@{socket.gethostname()}-{os.getpid()}"
            # 并发池按操作系统选择：Windows 用 solo（兼容性最好），Linux 用 prefork（并发生效）
            worker_pool = "solo" if sys.platform == "win32" else "prefork"
            cmd = [
                sys.executable,
                '-m', 'celery',
                '-A', 'app.celery.celery_app',
                'worker',
                '--loglevel=info',
                '--events',
                f'--pool={worker_pool}',
                f'--hostname={worker_hostname}',
                f'--queues={",".join(settings.celery_queues)}',
            ]
            # solo pool 是单执行槽，--concurrency 不生效，跳过以免误导
            if worker_pool != "solo":
                cmd.append(f'--concurrency={concurrency}')
            else:
                logger.info("当前为 Windows solo pool（单执行槽），并发数配置不生效")

            # 子进程编码防护（实测）：Windows 控制台默认 GBK，worker/beat 打印非 ASCII
            # 可能触发 UnicodeEncodeError 崩溃并连带 serve 退出——强制子进程 stdio 走 UTF-8，
            # 解码失败以 replace 兜底，不再向上传播致命异常
            child_env = dict(os.environ, PYTHONIOENCODING="utf-8:replace")

            global _worker_process
            _worker_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=child_env,
                bufsize=1,
            )

            logger.info(f"✅ Celery worker 启动成功 (pool={worker_pool}, concurrency={concurrency if worker_pool != 'solo' else 1})")
            
            # 读取并记录worker输出
            for line in _worker_process.stdout:
                if line.strip():
                    logger.info(f"[Celery Worker] {line.strip()}")
            
        except Exception as e:
            logger.error(f"❌ Celery worker 启动失败: {e}")
    
    # 创建并启动后台线程
    _worker_thread = threading.Thread(target=run_worker, daemon=True, name="CeleryWorkerThread")
    _worker_thread.start()
    logger.info("Celery worker 后台线程已启动")


def stop_celery_worker(timeout: int = 30):
    """
    停止Celery worker
    
    Author  ：bixuejun(bxjgood@163.com)
    Date    ：2025-12-14 11:45:00
    Args:
        timeout: 等待超时时间（秒）
        
    Returns:
        无
    """
    global _worker_thread, _worker_process
    
    try:
        logger.info("🛑 正在关闭 Celery worker...")
        
        if _worker_process is not None:
            # 终止worker进程
            _worker_process.terminate()
            try:
                _worker_process.wait(timeout=timeout)
                logger.info("✅ Celery worker 已优雅关闭")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Celery worker 关闭超时，强制终止")
                _worker_process.kill()
                _worker_process.wait()
            
            _worker_process = None
        
        # 等待线程结束
        if _worker_thread is not None and _worker_thread.is_alive():
            _worker_thread.join(timeout=5)
            _worker_thread = None
            
    except Exception as e:
        logger.error(f"❌ 关闭 Celery worker 时出错: {e}")


def start_celery_beat():
    """
    在后台线程启动Celery beat调度器
    
    Args:
        无
        
    Returns:
        无
    """
    global _beat_thread, _beat_process
    
    if _beat_thread is not None and _beat_thread.is_alive():
        logger.warning("⚠️ Celery beat 已经在运行中")
        return

    if not _try_acquire_beat_lock():
        return
    
    def run_beat():
        """在子进程中运行beat调度器"""
        try:
            logger.info("⏰ 正在启动 Celery beat...")
            
            # 使用subprocess启动beat进程
            cmd = [
                sys.executable,
                '-m', 'celery',
                '-A', 'app.celery.celery_app',
                'beat',
                '--loglevel=info',
                f'--schedule={_beat_schedule_path}',  # 修复：使用正确的参数名
            ]
            
            # 编码防护同 worker：beat 日志含非 ASCII（任务名/错误）时不再因 GBK 控制台崩溃
            child_env = dict(os.environ, PYTHONIOENCODING="utf-8:replace")
            global _beat_process
            _beat_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                encoding='utf-8',
                errors='replace',
                env=child_env,
                bufsize=1,
            )
            
            logger.info("✅ Celery beat 启动成功")
            
            # 读取并记录beat输出
            for line in _beat_process.stdout:
                if line.strip():
                    logger.info(f"[Celery Beat] {line.strip()}")
            
        except Exception as e:
            logger.error(f"❌ Celery beat 启动失败: {e}")
        finally:
            _release_beat_lock()
    
    # 创建并启动后台线程
    _beat_thread = threading.Thread(target=run_beat, daemon=True, name="CeleryBeatThread")
    _beat_thread.start()
    logger.info("✅ Celery beat 后台线程已启动")


def stop_celery_beat(timeout: int = 30):
    """
    停止Celery beat调度器
    
    Args:
        timeout: 等待超时时间（秒）
        
    Returns:
        无
    """
    global _beat_thread, _beat_process
    
    try:
        logger.info("🛑 正在关闭 Celery beat...")
        
        if _beat_process is not None:
            # 终止beat进程
            _beat_process.terminate()
            try:
                _beat_process.wait(timeout=timeout)
                logger.info("✅ Celery beat 已优雅关闭")
            except subprocess.TimeoutExpired:
                logger.warning("⚠️ Celery beat 关闭超时，强制终止")
                _beat_process.kill()
                _beat_process.wait()
            
            _beat_process = None
            _release_beat_lock()
        
        # 等待线程结束
        if _beat_thread is not None and _beat_thread.is_alive():
            _beat_thread.join(timeout=5)
            _beat_thread = None
            
    except Exception as e:
        logger.error(f"❌ 关闭 Celery beat 时出错: {e}")
