import os
import sys
from datetime import datetime, timezone

from loguru import logger


def setup_logging():
    """
    Setup logging configuration using Loguru
    """
    # Remove default logger
    logger.remove()

    # Add file logging
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)

    # Generate log file name with timestamp
    log_file = os.path.join(log_dir, f"app_{datetime.now(timezone.utc).strftime('%Y%m%d')}.log")

    # Add file sink with rotation
    logger.add(
        log_file,
        rotation="10 MB",
        retention="7 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} | {message}",
        enqueue=True  # Thread-safe logging
    )

    # Add console sink
    logger.add(
        sys.stderr,
        level="INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level}</level> | <cyan>{name}:{function}:{line}</cyan> | <level>{message}</level>",
        colorize=True
    )

    return logger


# Initialize the logger
app_logger = setup_logging()
