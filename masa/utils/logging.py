import bittensor as bt
import logging
import logging.handlers
import os
from datetime import datetime


def setup_logging(log_dir: str = "logs", debug: bool = False):
    """Setup logging configuration for the masa validator.

    Args:
        log_dir: Directory to store log files
        debug: Whether to enable debug logging
    """
    # Create logs directory if it doesn't exist
    os.makedirs(log_dir, exist_ok=True)

    # Create a formatter that includes timestamp, level, and message
    formatter = logging.Formatter(
        "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )

    # Setup file handler with rotation
    log_file = os.path.join(
        log_dir, f"validator_{datetime.now().strftime('%Y%m%d')}.log"
    )
    file_handler = logging.handlers.RotatingFileHandler(
        log_file, maxBytes=10 * 1024 * 1024, backupCount=5  # 10MB
    )
    file_handler.setFormatter(formatter)

    # Setup scoring log file
    scores_handler = logging.FileHandler(os.path.join(log_dir, "scores.log"))
    scores_handler.setFormatter(formatter)
    scores_logger = logging.getLogger("masa.scoring")
    scores_logger.addHandler(scores_handler)
    scores_logger.setLevel(logging.INFO)

    # Setup validation log file
    validation_handler = logging.FileHandler(os.path.join(log_dir, "validation.log"))
    validation_handler.setFormatter(formatter)
    validation_logger = logging.getLogger("masa.validation")
    validation_logger.addHandler(validation_handler)
    validation_logger.setLevel(logging.INFO)

    # Configure bittensor logging
    bt.logging.add_handler(file_handler)
    bt.logging.set_trace(debug)

    # Log startup message
    bt.logging.info("=" * 50)
    bt.logging.info("Starting Masa Validator")
    bt.logging.info(f"Log files directory: {os.path.abspath(log_dir)}")
    bt.logging.info("=" * 50)


def log_score(uid: int, volume: float, reward: float, hotkey: str):
    """Log scoring information to the scores log file.

    Args:
        uid: Miner UID
        volume: Tweet volume
        reward: Calculated reward
        hotkey: Miner's hotkey
    """
    logger = logging.getLogger("masa.scoring")
    logger.info(
        f"SCORE | UID: {uid:4d} | Volume: {volume:6.0f} | "
        f"Reward: {reward:.4f} | Hotkey: {hotkey}"
    )


def log_validation(uid: int, tweet_id: str, status: str, reason: str = None):
    """Log validation information to the validation log file.

    Args:
        uid: Miner UID
        tweet_id: ID of the tweet being validated
        status: Validation status (SUCCESS/FAILURE)
        reason: Reason for failure (if status is FAILURE)
    """
    logger = logging.getLogger("masa.validation")
    msg = f"VALIDATION | UID: {uid:4d} | Tweet: {tweet_id} | Status: {status}"
    if reason:
        msg += f" | Reason: {reason}"
    logger.info(msg)
