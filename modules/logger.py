from logging.handlers import TimedRotatingFileHandler
import logging
import os
from datetime import datetime
import glob
import time


class CustomTimedRotatingFileHandler(TimedRotatingFileHandler):
    def __init__(self, filename, when='h', interval=1, backupCount=0, encoding=None, delay=False, utc=False):
        super().__init__(filename, when, interval, backupCount, encoding, delay, utc)

    def doRollover(self):
        super().doRollover()
        if self.stream:
            self.stream.close()
            self.stream = None

    def _compute_fn(self, currentTime):
        timestamp = self.toTime(currentTime)
        return timestamp.strftime('%y%m%d.log')


enum = {
    'debug': logging.DEBUG,
    'info': logging.INFO,
    'warning': logging.WARNING,
    'error': logging.ERROR,
    'critical': logging.CRITICAL,
}


class LogPrint():
    def __init__(self, log_dir, print_modes, file_mode, log_days):
        self.log_dir = log_dir
        self.print_modes = print_modes
        self.file_mode = enum.get(file_mode) or logging.INFO
        self.log_days = log_days
        self._initLogConfig()

    def _initLogConfig(self):
        today = datetime.now().strftime('%Y%m%d')
        logfile = os.path.join(self.log_dir, today + '.log')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=logfile)
        handler = CustomTimedRotatingFileHandler(logfile, when="D", interval=1, backupCount=7)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger = logging.getLogger("run-loop")
        logger.setLevel(self.file_mode)
        logger.addHandler(handler)
        log_remover(self.log_days)
   
    def setLogDirectory(self, log_dir):
        self.log_dir = log_dir
        self._initLogConfig()

    def setLogDays(self, log_days):
        self.log_days = log_days
        log_remover(self.log_days)
    
    def setPrintModes(self, print_modes):
        self.print_modes = print_modes
    
    def setFileMode(self, file_mode):
        self.file_mode = enum.get(file_mode) or logging.INFO
        logger = logging.getLogger("run-loop")
        logger.setLevel(self.file_mode)
    
    def info(self, *msg):
        if 'info' in self.print_modes:
            print(*msg)
        logging.info(msg)

    def verbose(self, *msg):
        if 'verbose' in self.print_modes:
            print(*msg)
        logging.debug(msg)
    
    def debug(self, *msg):
        if 'debug' in self.print_modes:
            print(*msg)
        logging.debug(msg)
    
    def error(self, *msg):
        if 'error' in self.print_modes:
            print(*msg)
        logging.error(msg)
    
    def warning(self, *msg):
        if 'warning' in self.print_modes:
            print(*msg)
        logging.warning(msg)

    def critical(self, *msg):
        if 'critical' in self.print_modes:
            print(*msg)
        logging.critical(msg)


def log_remover(log_dir, log_days=7):
    for f in glob.glob(os.path.join(log_dir, '*.log')):
        if os.path.getmtime(f) < time.time() - log_days * 24 * 60 * 60:
            os.remove(f)
