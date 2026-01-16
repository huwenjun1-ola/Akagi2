import os
import sys
import time

from loguru import logger as main_logger

from mitm.jpmaj import  on_room_new_message, gRoomManager,  print_memory_usage

flag="Received MJAI message: {"
print(os.getpid())
main_logger.remove()
# 2. 重新添加：仅绑定标准输出和标准错误
# 通常建议：INFO 及以下去 stdout，WARNING 及以上去 stderr
main_logger.add(sys.stderr, level="WARNING")
main_logger.add(sys.stdout, level="INFO")


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





if __name__ == '__main__':
    lMsg = []
    with open('game_akagi.log', 'rb') as f:
        for line in f.readlines():
            lMsg.append(line.strip())
    for rid in range(0,1):
        main_logger.info(f"rid : {rid}")
        mockRoom(lMsg,rid)
        print_memory_usage()


    main_logger.info("done")
    while 1:
        time.sleep(10)
        print_memory_usage()

