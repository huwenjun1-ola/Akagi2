import os
import sys
import tomllib
from entry import entry
from loguru import logger as main_logger

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
            main_logger.debug(f"apply config from go,host:{host},port:{port}")
    except Exception as e:
        pass
    if os.environ.get("LOGURU_WRITEFILE", "1") == "0":
        main_logger.remove()
        # 2. 重新添加：仅绑定标准输出和标准错误
        # 通常建议：INFO 及以下去 stdout，WARNING 及以上去 stderr
        main_logger.add(sys.stdout, level="DEBUG")
        main_logger.add(sys.stderr, level="WARNING")
    entry.main()