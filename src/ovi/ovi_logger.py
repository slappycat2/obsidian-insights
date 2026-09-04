"""Logging setup for ovi.

Import ``logger`` from here everywhere; call ``make_logger()`` exactly once, at
application start-up.

The JSON files in ``src/logging_configs/`` declare their log files with
relative paths (``logs/ovi.log``). Those are resolved against DATA_ROOT here
rather than the working directory, so logging works no matter where ovi is
launched from.
"""

import json
import atexit
import logging.config
import logging.handlers
from pathlib import Path

from ovi import ovi_paths as paths

# Pillow logs a great deal at DEBUG; keep it out of our log file.
pil_logger = logging.getLogger('PIL')
pil_logger.setLevel(logging.INFO)

logger = logging.getLogger("ovi")

#: Which file in src/logging_configs/ to use. The alternatives there route to
#: stdout, to JSON, or through a background queue.
ACTIVE_LOG_CONFIG = "1-stderr-file.json"

DEFAULT_LOG_LEVEL = "INFO"  # NOTSET, DEBUG, INFO, WARNING, ERROR, CRITICAL


def _resolve_handler_paths(config: dict) -> dict:
    """Rewrite relative handler filenames to absolute paths under DATA_ROOT.

    Also creates the destination directory, since RotatingFileHandler raises if
    the parent directory does not exist.
    """
    for handler in config.get("handlers", {}).values():
        filename = handler.get("filename")
        if not filename:
            continue

        path = Path(filename)
        if not path.is_absolute():
            path = (paths.DATA_ROOT / path).resolve()

        path.parent.mkdir(parents=True, exist_ok=True)
        handler["filename"] = str(path)

    return config


def setup_logging(config_name: str = ACTIVE_LOG_CONFIG) -> None:
    config_file = paths.LOGGING_CONFIG_DIR / config_name

    with open(config_file, encoding="utf-8") as f_in:
        config = json.load(f_in)

    logging.config.dictConfig(_resolve_handler_paths(config))

    queue_handler = logging.getHandlerByName("queue_handler")
    if queue_handler is not None:
        queue_handler.listener.start()
        atexit.register(queue_handler.listener.stop)


def make_logger(level: str = DEFAULT_LOG_LEVEL,
                config_name: str = ACTIVE_LOG_CONFIG) -> logging.Logger:
    """Configure logging and return the application logger.

    :param level: level for the ``ovi`` logger, e.g. from ``--debug-level``.
    :param config_name: filename within ``src/logging_configs/``.
    """
    setup_logging(config_name)

    level_name = str(level).upper()
    if not hasattr(logging, level_name):
        logger.warning("Unknown log level %r; falling back to %s",
                       level, DEFAULT_LOG_LEVEL)
        level_name = DEFAULT_LOG_LEVEL

    logger.setLevel(getattr(logging, level_name))
    logger.info("Logger initialized at level %s", level_name)

    return logger


if __name__ == "__main__":
    make_logger()
