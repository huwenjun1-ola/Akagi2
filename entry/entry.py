import asyncio
import sys
import signal
import threading

from mitm.client import Client
import os
from .logger import logger
import time
from settings.settings import settings, MITMType
from mitm.jpmaj import start_proxy, stop_proxy, mjai_messages,gRoomManager,room_manager_lock

os.environ["LOGURU_AUTOINIT"] = "False"


class Application:
    def __init__(self):
        pass

    def signal_handler(self, signum, frame):
        """处理信号的回调函数"""
        logger.info(f"{os.getpid()} Received signal {signum}, shutting down gracefully...")
        global gRoomManager
        with room_manager_lock:
            gRoomManager.isStopping=True
        
        # 等待gRoomMap变空，最多等待5分钟
        timeout = 1800  # 30分钟超时
        start_time = time.time()
        while True:
            # 使用锁保护读取gRoomMap的长度
            with room_manager_lock:
                room_count = len(gRoomManager.gRoomMap)
            
            if room_count == 0:
                logger.info("All rooms cleaned up, shutting down...")
                break
            
            if time.time() - start_time > timeout:
                logger.warning(f"Timeout reached, {room_count} rooms still active, forcing shutdown...")
                break
            
            logger.info(f"Waiting for {room_count} rooms to clean up...")
            time.sleep(5)  # 减少睡眠时间，增加检查频率
        
        stop_proxy()
        logger.info(f"{os.getpid()} Akagi stopped")
        sys.exit(0)

    def run(self):
        # 注册信号处理器
        signal.signal(signal.SIGHUP, self.signal_handler)
        _thread = threading.Thread(
            target=lambda: asyncio.run(start_proxy(settings.mitm.host, settings.mitm.port)))
        _thread.daemon = True
        _thread.start()
        #  在这里阻塞 - 实现持续运行和信号检测
        while True:
            # 短暂休眠避免CPU占用过高
            time.sleep(10)



def main():
    app = Application()
    app.run()
