import logging

def init_test_logger():
    """set up logging for testing without syslog by logging DEBUG to console"""
    logger = logging.getLogger()
    loghandler = logging.StreamHandler()
    loghandler.setFormatter(logging.Formatter('yaml_server[%(filename)s:%(lineno)d]: %(levelname)s: %(message)s'))
    logger.addHandler(loghandler)
    logger.setLevel(logging.DEBUG)
