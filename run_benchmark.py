import asyncio
import os
import sys
import time
import tomllib

import psutil

from entry import entry
from loguru import logger as main_logger

from mitm.jpmaj import on_room_robot_message, on_room_new_message, gRoomManager, check_room_timeout

flag="Received MJAI message: {"
print(os.getpid())
main_logger.remove()
# 2. 重新添加：仅绑定标准输出和标准错误
# 通常建议：INFO 及以下去 stdout，WARNING 及以上去 stderr
main_logger.add(sys.stderr, level="WARNING")
# main_logger.add(sys.stdout, level="DEBUG")


def parse_log():
    lMsg = []
    lStr = []
    with open('game_akagi.hatta.stdout.log', 'rb') as f:
        for line in f.readlines():
            line = line.decode("utf-8")
            if line.find("on_room_robot_message:201") >= 0:
                if line.find("105719494") == -1:
                    continue
                index = line.find(flag)
                if index >= 0:
                    mjai_msg = line[index + len(flag) - 1:]
                    lStr.append(mjai_msg)
                    # mjai_msg=mjai_msg.replace("'","\"")
                    lMsg.append(mjai_msg.strip())
    with open('game_akagi.log', 'w') as f:
        f.writelines(lStr)
    print(len(lMsg))


def mockRoom(lMsg,rid):
    for msg in lMsg:
        """处理NSQ消息 - 同步handler"""
        try:
            # 解码消息体
            mjai_message = eval(msg)
            mjai_message["Rid"]=rid
            main_logger.debug(f"Received MJAI message: {mjai_message}")
            type_val = mjai_message.get("Type")
            if type_val == "create_game":
                dData=mjai_message.get("Data")
                dData["Rid"]=rid
                on_room_new_message(mjai_message.get("Data"))
                continue

            # 使用锁保护读取gRoomMap
            rid = mjai_message.get("Rid")
            if rid not in gRoomManager.gRoomMap:
                continue

            room = gRoomManager.gRoomMap[rid]
            if room is not None:
                room.OnMsg(mjai_message)

        except Exception as e:
            main_logger.error(f"[Handler] Error handling MJAI message: {e}", exc_info=True)
            import traceback

            traceback.print_exc()


def print_memory_usage():
    """打印当前进程的内存占用"""
    process = psutil.Process(os.getpid())
    memory_info = process.memory_info()

    # 获取内存占用信息
    rss = memory_info.rss / 1024 / 1024  # 转换为MB
    vms = memory_info.vms / 1024 / 1024  # 转换为MB

    main_logger.error(f"PID: {os.getpid()}")
    main_logger.error(f"物理内存占用 (RSS): {rss:.2f} MB")
    main_logger.error(f"虚拟内存占用 (VMS): {vms:.2f} MB")

    # 还可以获取内存百分比
    memory_percent = process.memory_percent()
    main_logger.error(f"内存使用率: {memory_percent:.2f}%")


if __name__ == '__main__':
    lMsg = []
    with open('game_akagi.log', 'rb') as f:
        for line in f.readlines():
            lMsg.append(line.strip())
    for rid in range(1,100):
        main_logger.error(f"rid : {rid}")
        mockRoom(lMsg,rid)
        print_memory_usage()


    main_logger.error("done")
    while 1:
        time.sleep(10)
        print_memory_usage()

