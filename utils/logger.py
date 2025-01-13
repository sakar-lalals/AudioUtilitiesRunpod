import logging

logger_cache = {}

def get_logger(logger_name, level="DEBUG"):
    global logger_cache

    if logger_name in logger_cache:
        return logger_cache[logger_name]

    logger = logging.getLogger(logger_name)

    # Clear existing handlers to prevent duplicate logs
    if logger.hasHandlers():
        logger.handlers.clear()

    level = getattr(logging, level.upper(), logging.DEBUG)
    logger.setLevel(level)

    ch = logging.StreamHandler()
    ch.setLevel(level)

    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    ch.setFormatter(formatter)
    logger.addHandler(ch)

    logger_cache[logger_name] = logger

    return logger

if __name__ == "__main__":
    logger1 = get_logger("BeamUtils", level="DEBUG")
    logger2 = get_logger("BeamUtils", level="INFO")

    logger1.debug("Voice path exists, checking files...")
    logger2.info("This is an info message")
    logger1.warning("This is a warning message")
    logger2.error("This is an error message")
    logger1.critical("This is a critical message")