import json
import os
import sys
import threading
import traceback
import asyncio
import queue
import time
from functools import partialmethod

import mitmproxy.http
import mitmproxy.log
import mitmproxy.tcp
import mitmproxy.websocket
import psutil
from mitmproxy import proxy, options, ctx
from mitmproxy.tools.dump import DumpMaster
from .bridge import JpMahjongBridge
from .mitm_abc import ClientWebSocketABC
from .logger import logger
from .bridge.jp_mahjong.nsq_receiver import JpMahjongNsqReceiver

class JpMahjongRoom():
    room_id:int
    jpmaj_bridges: dict[int, JpMahjongBridge] = {}  # store all flow.id -> MajsoulBridge

    def __init__(self, room_id):
        self.room_id = room_id
        self.jpmaj_bridges={}

    def OnMsg(self,mjai_message ):
        data = mjai_message.get("Data")
        for bridge in self.jpmaj_bridges.values():
            if bridge is not None:
                msgs = bridge.parse(data)
                if debug_uid == bridge.uid:
                    for m in msgs:
                        mjai_messages.put(m)
                else:
                    reply = bridge.execute(msgs)
                    if reply:
                        if nsq_receiver:
                            nsq_receiver.publish_akagi_events(
                                f"{nsq_receiver.MahjongTopic}.reply",
                                reply
                            )
        if  data.get("type")=="end_game":
            self.check_destroy()

    def check_destroy(self):
        bridge_to_destroy = []
        for uid,bridge in self.jpmaj_bridges.items():
            if bridge is not None and bridge.is_timeout():
                bridge_to_destroy.append(uid)
        if bridge_to_destroy:
            for uid in bridge_to_destroy:
                del self.jpmaj_bridges[uid]
                logger.info(f"销毁房间 {self.room_id} 的用户 {uid}")

class RoomManager():
    def __init__(self):
        self.gRoomMap: dict[int, JpMahjongRoom] = {}
        self.isStopping = False

# 全局锁用于保护gRoomManager的并发访问
room_manager_lock = threading.Lock()
gRoomManager=RoomManager()
# Because in Majsouls, every flow's message has an id, we need to use one bridge for each flow
mjai_messages: queue.Queue[dict] = queue.Queue() # store all messages
nsq_receiver:JpMahjongNsqReceiver=None
debug_uid=0
timeout_seconds = 3 * 60  # 3分钟超时

def print_memory_usage():
    """打印当前进程的内存占用"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    # 获取内存占用信息
    rss = memory_info.rss / 1024 / 1024  # 转换为MB
    vms = memory_info.vms / 1024 / 1024  # 转换为MB

    logger.info(f"PID: {os.getpid()}")
    logger.info(f"物理内存占用 (RSS): {rss:.2f} MB")
    logger.info(f"虚拟内存占用 (VMS): {vms:.2f} MB")

    # 还可以获取内存百分比
    memory_percent = process.memory_percent()
    logger.info(f"内存使用率: {memory_percent:.2f}%")

# 添加定期检查房间超时的任务
async def check_room_timeout():
    """定期检查房间是否超时，超过3分钟没有更新则销毁房间"""
    while True:
        try:
            rooms_to_destroy = []
            ridCnt=0
            uidCnt=0
            # 使用锁保护读取gRoomMap
            with room_manager_lock:
                # 检查所有房间
                for room_id, room in gRoomManager.gRoomMap.items():
                    ridCnt+=1
                    uidCnt+=len(room.jpmaj_bridges)
                    room.check_destroy()
                    if not room.jpmaj_bridges:
                        rooms_to_destroy.append(room_id)
                
                # 销毁超时的房间
                for room_id in rooms_to_destroy:
                    if room_id in gRoomManager.gRoomMap:
                        logger.info(f"房间 {room_id} 超时超过3分钟，正在销毁...")
                        del gRoomManager.gRoomMap[room_id]
                        logger.info(f"房间 {room_id} 已销毁")
            logger.info(f"当前房间数: {ridCnt},用户数: {uidCnt}")
            print_memory_usage()
            # 每30秒检查一次
            await asyncio.sleep(60)
        except Exception as e:
            logger.error(f"检查房间超时时出错: {e}", exc_info=True)

async def start_proxy(host, port):
    global debug_rid, debug_uid
    arr = host.split("/")
    if len(arr) == 2:
        debug_uid = int(arr[0])
        host = arr[1]
    logger.info(f"Starting nsq proxy server at {host}:{port}")
    global nsq_receiver
    nsq_receiver = JpMahjongNsqReceiver()
    # 创建接收器实例
    address = f"{host}:{port}"
    """启动NSQ接收器，接收来自Go服务的MJAI格式数据"""
    # 连接到NSQ服务器
    if await nsq_receiver.connect(address):
        # 订阅来自Go服务的MJAI事件
        logger.info(f"[start_proxy] Subscribing to NSQ events...")
        try:
            await nsq_receiver.subscribe_to_akagi_events(
                nsq_receiver.MahjongTopic,
                f"akagi_channel_{os.getpid()}",
                on_room_robot_message
            )
            logger.info("[start_proxy] NSQ subscription successful, keeping connection alive...")
            # 启动房间超时检查任务
            asyncio.create_task(check_room_timeout())
            # 保持连接活跃 - NSQ Reader 在后台工作
            while True:
                await asyncio.sleep(10)
        except Exception as e:
            logger.error(f"[start_proxy] Error in NSQ subscription: {e}", exc_info=True)
            return None
    else:
        logger.error("Failed to connect to NSQ")
        return None


def stop_proxy():
    nsq_receiver.close()





import json
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class RoomRobotMessage:
    Uid: int = 0
    Seat: int = 0

@dataclass
class RoomNewMessage:
    Rid: int = 0
    Robots: List[RoomRobotMessage] = field(default_factory=list)

    @classmethod
    def from_json(cls, json_str: str):
        """从JSON字符串创建实例"""
        data = json.loads(json_str)
        data=data.get("Data")
        # 将robots列表中的字典转换为RoomRobotMessage对象
        robots = [RoomRobotMessage(**robot) for robot in data.get("Robots", [])]
        return cls(
            Rid=data.get("Rid", 0),
            Robots=robots
        )

    @classmethod
    def from_dict(cls, data: dict):
        """从字典创建实例"""
        robots = [RoomRobotMessage(**robot) for robot in data.get("Robots", [])]
        return cls(
            Rid=data.get("Rid", 0),
            Robots=robots
        )

def on_room_new_message(message):
    """处理NSQ消息"""
    try:
        # 解码消息体
        mjai_message=RoomNewMessage.from_dict( message)
        logger.info(f"on_room_new_message : {mjai_message}")
        room=JpMahjongRoom(mjai_message.Rid)
        gRoomManager.gRoomMap[mjai_message.Rid]=room
        for obj in mjai_message.Robots:
            jpmaj_bridge = JpMahjongBridge()
            jpmaj_bridge.seat=obj.Seat
            jpmaj_bridge.uid=obj.Uid
            jpmaj_bridge.rid=mjai_message.Rid
            room.jpmaj_bridges[obj.Uid]=jpmaj_bridge


    except Exception as e:
        logger.error(f"Error handling MJAI message: {e}")


def on_room_robot_message(message):
    """处理NSQ消息 - 同步handler"""
    try:
        # 解码消息体
        body = message.body
        mjai_message = json.loads(body.decode('utf-8'))
        logger.debug(f"Received MJAI message: {mjai_message}")
        type_val = mjai_message.get("Type")
        if  type_val == "create_game":
            with room_manager_lock:
                if  not gRoomManager.isStopping:
                    on_room_new_message(mjai_message.get("Data"))
            return
        
        # 使用锁保护读取gRoomMap
        rid = mjai_message.get("Rid")
        if rid not in gRoomManager.gRoomMap:
            return

        room = gRoomManager.gRoomMap[rid]
        if room is not None:
            room.OnMsg(mjai_message)

    except Exception as e:
        logger.error(f"[Handler] Error handling MJAI message: {e}", exc_info=True)
        import traceback
        traceback.print_exc()

    finally:
        # 标记消息处理完成
        try:
            message.finish()
        except Exception as e:
            logger.error(f"[Handler] Error finishing message: {e}")
