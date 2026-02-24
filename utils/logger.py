import logging
import os

LOG_DIR = "data"
LOG_FILE = os.path.join(LOG_DIR, "agent.log")

try:
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)
except OSError:
    pass


def get_logger(name: str) -> logging.Logger:
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger

    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "[%(asctime)s] %(name)s %(levelname)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    # File handler（云环境可能无写权限，降级为仅 console）
    try:
        fh = logging.FileHandler(LOG_FILE, encoding="utf-8")
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    except (OSError, IOError):
        pass

    return logger
