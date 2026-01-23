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
original_add = main_logger.add
if os.environ.get("LOGURU_WRITEFILE", "1") == "0":
    main_logger.add = safe_add_handler

from entry import entry
from settings.settings import settings

if __name__ == '__main__':
    try:
        cfgPath="./config/config.toml"
        if not os.path.exists(cfgPath):
            cfgPath=f"../{cfgPath}"
        with open(cfgPath, 'rb') as f:
            data = tomllib.load(f)
            dLogger=data.get("logger")
            levelStr=dLogger.get("Level")
            main_logger.remove()
            # 2. 重新添加：仅绑定标准输出和标准错误
            # 通常建议：INFO 及以下去 stdout，WARNING 及以上去 stderr
            if levelStr == "all":
                original_add(sys.stdout, level="DEBUG")
            else:
                original_add(sys.stdout, level="INFO")
            original_add(sys.stderr, level="WARNING")
            dNsq=data.get("go-nsq")
            lAddrs=dNsq.get("game")
            if lAddrs:
                addr=lAddrs[0]
                host,port=addr.split(":")
                settings.mitm.host = host
                settings.mitm.port = port
                main_logger.info(f"apply config from go,host:{host},port:{port}")
            main_logger.info(f"apply config from go")
    except Exception as e:
        main_logger.error(e)
    entry.main()