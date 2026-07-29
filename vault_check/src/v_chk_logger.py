import pathlib
import json
import atexit

import logging.config
import logging.handlers

pil_logger = logging.getLogger('PIL')
pil_logger.setLevel(logging.INFO)

logger = logging.getLogger("v_chk")  # __name__ is a common choice
LOG_LVL = 'DEBUG'      # NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL

def setup_logging():
    # noinspection DuplicatedCode
    # config_file = pathlib.Path("src/logging_configs/0-stdout.json")
    config_file = pathlib.Path("src/logging_configs/1-stderr-file.json")
    # config_file = pathlib.Path("src/logging_configs/2-stderr-json-file.json")
    # config_file = pathlib.Path("src/logging_configs/3-homework-filtered-stdout-stderr.json")
    # config_file = pathlib.Path("src/logging_configs/4-queued-json-stderr.json")
    # config_file = pathlib.Path("src/logging_configs/5-queued-stderr-json-file.json")
    with open(config_file) as f_in:
        config = json.load(f_in)

    logging.config.dictConfig(config)
    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)

def make_logger():
    # noinspection DuplicatedCode
    setup_logging()
    logging.basicConfig(level=LOG_LVL)

    logger.info("Logger initialized...")

if __name__ == "__main__":
    make_logger()