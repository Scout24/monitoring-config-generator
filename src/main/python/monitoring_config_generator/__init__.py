import logging


def init_logging():
    formatter = logging.Formatter("%(asctime)s [%(name)s] %(levelname)s: %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    monconfgenerator_logger = logging.getLogger('monconfgenerator')
    monconfgenerator_logger.setLevel(logging.INFO)
    monconfgenerator_logger.addHandler(console_handler)


def set_log_level_to_debug():
    monconfgenerator_logger = logging.getLogger('monconfgenerator')
    monconfgenerator_logger.setLevel(logging.DEBUG)

init_logging()
