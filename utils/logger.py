# utils/logger.py

import logging
from utils.config import LOG_PATH


# 配置 logging 系统
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    encoding="utf-8"
)

# 获取 logger 对象
logger = logging.getLogger()


# 普通信息日志
def log_info(message):
    logger.info(message)


# 错误日志
def log_error(message):
    logger.error(message)