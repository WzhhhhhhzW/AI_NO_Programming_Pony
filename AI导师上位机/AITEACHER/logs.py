"""日志配置。别的模块直接 ``from loguru import logger`` 用就行，这里只装 sink。

现场最怕"看着像卡住了"却不知道卡在哪一步，所以格式里第一列是**从启动
算起的秒数**，对着它就能算出每一步之间隔了多久。

日志文件：
    Windows  %APPDATA%\\RenesasHorseAI\\logs\\run_<时间戳>.log
    Linux    ~/RenesasHorseAI/logs/run_<时间戳>.log
"""

import os
import sys
import time

from loguru import logger

from config import _CONFIG_DIR

T0 = time.monotonic()

LOG_DIR = os.path.join(_CONFIG_DIR, "logs")

LOG_FORMAT = (
    "<dim>[{extra[mono]:9.3f}]</dim> "
    "<level>{level:<7}</level> | "
    "<cyan>{name:<10}</cyan>:"
    "<cyan>{function:<20}</cyan>:"
    "<cyan>{line:>4}</cyan> | "
    "<level>{message}</level>"
)


def setup():
    logger.remove()
    logger.configure(
        patcher=lambda rec: rec["extra"].update(mono=time.monotonic() - T0)
    )
    # 注意：不使用 enqueue=True，避免引入预料之外的问题
    # PyInstaller windowed 模式下 sys.stdout 是 None，跳过
    if sys.stdout is not None:
        logger.add(
            sink=sys.stdout,
            level="DEBUG",
            format=LOG_FORMAT,
            colorize=True,
            backtrace=False,
            diagnose=False,
        )
    logger.add(
        os.path.join(LOG_DIR, "run_{time:YYYYMMDD_HHmmss}.log"),
        level="DEBUG",
        format=LOG_FORMAT,
        colorize=False,
        rotation="20 MB",
        retention="3 days",
        encoding="utf-8",
        backtrace=True,
        diagnose=False,
    )
    logger.info("日志启动，文件在 {}", LOG_DIR)
