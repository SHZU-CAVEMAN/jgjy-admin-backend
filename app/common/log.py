"""应用日志配置。"""

import logging


def configure_logging() -> None:
    """配置进程级的简洁日志格式。"""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
