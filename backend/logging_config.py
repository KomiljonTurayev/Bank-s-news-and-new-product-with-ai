import logging

from config import settings


def setup_logging():
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, settings.log_level.upper(), logging.INFO))

    console = logging.StreamHandler()
    console.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] [%(name)s] - %(message)s [%(thread)d]"
        )
    )
    logger.addHandler(console)
    return logger
