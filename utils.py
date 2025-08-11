import os
import logging

def setup_logging(logger_name: str = "documents_reader", log_path: str = "logs/retriever.log") -> logging.Logger:
    """
    Set up and return a logger instance with the specified name.

    Args:
        logger_name (str): Name of the logger, usually __name__ of the module.
        log_path (str): Path where the log file will be written.

    Returns:
        logging.Logger: Configured logger instance.
    """
    os.makedirs(os.path.dirname(log_path), exist_ok=True)

    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)

    # Avoid adding multiple handlers in interactive environments
    if not logger.handlers:
        file_handler = logging.FileHandler(log_path, mode="a")
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger
