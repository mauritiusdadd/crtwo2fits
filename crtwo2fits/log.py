import logging


def log(message, level=logging.DEBUG):
    logger = logging.getLogger()
    for each_message in str(message).splitlines():
        if logger is not None:
            logger.log(level, each_message)
