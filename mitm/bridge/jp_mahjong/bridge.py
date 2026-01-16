import copy
import time
from typing import Self
from enum import Enum
from functools import cmp_to_key
import asyncio
import json

from akagi.libriichi_helper import meta_to_recommend
from ..bridge_base import BridgeBase
from ..logger import logger
from mjai_bot.controller import Controller

timeout_seconds = 3 * 60  # 3分钟超时

# MJAI行动类型
class MjaiActionType(Enum):
    StartGame = 'start_game'
    StartKyoku = 'start_kyoku'
    Tsumo = 'tsumo'
    Dahai = 'dahai'
    Dora = 'dora'
    Reach = 'reach'
    ReachAccepted = 'reach_accepted'
    Pon = 'pon'
    Chi = 'chi'
    Daiminkan = 'daiminkan'
    Ankan = 'ankan'
    Kakan = 'kakan'
    Hora = 'hora'
    Agari = 'agari'
    Ryukyoku = 'ryukyoku'
    EndKyoku = 'end_kyoku'
    EndGame = 'end_game'
    Nukidora = 'nukidora'

class JpMahjongBridge(BridgeBase):
    def __init__(self):
        super().__init__()
        self.rid=0
        self.uid = 0
        self.seat = 0
        self.lastDiscard = None
        self.reach = False
        self.accept_reach = None
        self.operation = {}
        self.AllReady = False
        self.temp = {}
        self.doras = []
        self.my_tehais = ["?"]*13
        self.my_tsumohai = "?"
        self.syncing = False

        self.mode_id = -1
        self.rank = -1
        self.score = -1
        self.lastMsgTimestamp = 0

        self.is_3p = False
        self.mjai_controller: Controller = Controller ()




    def parse(self, parsed_msg: bytes) -> None | list[dict]:
        """接收来自Go服务的MJAI格式内容。
        
        Args:
            content (bytes): MJAI格式的内容
            
        Returns:
            None | list[dict]: MJAI命令列表
        """
        try:
            self.lastMsgTimestamp = time.time()
            # 直接解析MJAI格式的消息
            parsed_msg=copy.deepcopy(parsed_msg)
            msgType=parsed_msg.get("type")
            if  msgType== "start_game":
                parsed_msg["id"] = self.seat
            if msgType=="start_kyoku" :
                tmpCards=['?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?', '?']
                lcards=[]
                for i in range(len(parsed_msg.get("tehais"))):
                    if i==self.seat:
                        lcards.append(parsed_msg.get("tehais")[i])
                    else:
                        lcards.append(tmpCards)
                parsed_msg["tehais"]=lcards
            if msgType=="tsumo" and self.seat!=parsed_msg.get("actor"):
                parsed_msg["pai"]='?'
            # 返回MJAI消息列表
            return [parsed_msg]
        except Exception as e:
            logger.error(f"Error parsing MJAI message: {e}")
            return None

    def build(self, command: dict) -> None | bytes:
        """将MJAI命令转换为日本麻将协议格式
        
        Args:
            command (dict): MJAI命令
            
        Returns:
            None | bytes: 转换后的日本麻将协议数据
        """
        try:
            # 直接将MJAI命令转换为JSON格式
            json_data = json.dumps(command, ensure_ascii=False)
            return json_data.encode('utf-8')
        except Exception as e:
            logger.error(f"Error building message: {e}")
            return None

    def execute(self,msgs)   :
        try:
            logger.debug(f"{self.rid}  execute1 { self.uid} { self.seat} { msgs}")

            mjai_response =self.mjai_controller.react(msgs)
            logger.debug(f"{self.rid}  execute2 { self.uid} { self.seat} {mjai_response} ")

            if "meta" not in mjai_response:
                return
            if "q_values" not in mjai_response["meta"]:
                return
            meta = mjai_response["meta"]
            recommends: list[tuple[str, float]] = meta_to_recommend(meta,False)[0:8]
            lActions = []
            for i in range(len(recommends)):
                recommend=recommends[i]
                lActions.append({
                    "Action": recommend[0],
                    "Ratio": recommend[1],
                })
            reply_msg={
                "Rid": self.rid,
                "Uid": self.uid,
                "Type":mjai_response["type"],
                "Actions": lActions,
            }
            reply=json.dumps(reply_msg)
            logger.debug(f"{self.rid}  execute3 { self.uid} { self.seat}  { reply}")
            return reply
        except Exception as e:
            logger.error(f"Error executing command: {e}")

    def is_timeout(self):
        return time.time() - self.lastMsgTimestamp > timeout_seconds