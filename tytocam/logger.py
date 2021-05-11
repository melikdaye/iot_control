import logging
import logging.handlers
import os


class TytoLog:

    def __init__(self):
        self.logger = logging.getLogger("Tytocam")
        logging.basicConfig(level=logging.DEBUG)
        f_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler = logging.handlers.RotatingFileHandler("/var/log/tytocam.log",maxBytes=10**6,backupCount=5)
        handler.setFormatter(f_format)
        self.logger.addHandler(handler)
