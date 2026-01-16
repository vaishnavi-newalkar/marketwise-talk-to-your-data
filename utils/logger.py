import logging
import sys


def setup_logger(name: str = "nl2sql", level=logging.INFO):
    """
    Sets up a standardized logger for the application.

    Args:
        name (str): Logger name
        level (int): Logging level (INFO, DEBUG, ERROR)

    Returns:
        logging.Logger
    """

    logger = logging.getLogger(name)

    # Prevent duplicate handlers
    if logger.handlers:
        return logger

    logger.setLevel(level)

    handler = logging.StreamHandler(sys.stdout)
    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S"
    )

    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger
