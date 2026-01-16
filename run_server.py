import os
import sys
import tomllib
# 创建统一的日志管理器
from loguru import logger as main_logger
import os

def safe_add_handler(*args, **kwargs):
    """安全添加日志处理器"""
    return None

# 替换原始的 add 方法
if os.environ.get("LOGURU_WRITEFILE", "1") == "0":
    original_add = main_logger.add
    main_logger.add = safe_add_handler

from entry import entry
from settings.settings import settings

if __name__ == '__main__':
    try:
        with open('../config/config.toml', 'rb') as f:
            data = tomllib.load(f)
            dNsq=data.get("go-nsq")
            lAddrs=dNsq.get("game")
            addr=lAddrs[0]
            host,port=addr.split(":")
            settings.mitm.host = host
            settings.mitm.port = port
            main_logger.info(f"apply config from go,host:{host},port:{port}")
    except Exception as e:
        pass
    entry.main()