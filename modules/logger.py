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
    'notset': logging.NOTSET,
    'none': None
}


class LogPrint():
    def __init__(self):
        self.log_dir = None
        self.print_levels = None
        self.logging_level = None
        self.log_days = None
        self.startMessage = False

    def setConfig(self, log_dir='./log', print_levels=['info'], logging_level='info', log_days=7):
        chenged = False
        if log_dir != self.log_dir:
            self.log_dir = log_dir
            os.makedirs(log_dir, exist_ok=True)
            chenged = True
        if print_levels != self.print_levels:
            self.print_levels = print_levels
            chenged = True
        logging_level = enum.get(logging_level)
        if logging_level != self.logging_level:
            self.logging_level = logging_level
            chenged = True
        if log_days != self.log_days:
            self.log_days = log_days
            chenged = True
        if chenged:
            self._initLogConfig()
            if not self.startMessage:
                self.debug('LogPrint logging start')
            self.startMessage = True

    def _initLogConfig(self):
        print(self.logging_level)
        if self.logging_level is None:
            return
        today = datetime.now().strftime('%Y%m%d')
        logfile = os.path.join(self.log_dir, today + '.log')
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=logfile)
        handler = CustomTimedRotatingFileHandler(logfile, when="D", interval=1, backupCount=7)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger = logging.getLogger("run-loop")
        logger.setLevel(self.logging_level)
        logger.addHandler(handler)
        self.log_remover()
   
    def setLogDirectory(self, log_dir):
        self.log_dir = log_dir
        self._initLogConfig()

    def setLogDays(self, log_days):
        self.log_days = log_days
        self.log_remover()
    
    def setPrintModes(self, print_levels):
        self.print_levels = print_levels
    
    def setFileMode(self, logging_level):
        self.logging_level = enum.get(logging_level) or logging.INFO
        logger = logging.getLogger("run-loop")
        logger.setLevel(self.logging_level)
    
    def info(self, *msg):
        if 'info' in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            logging.info(*msg)

    def verbose(self, *msg):
        if 'verbose' in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            logging.debug(*msg)
    
    def debug(self, *msg):
        if 'debug' in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            logging.debug(*msg)
    
    def error(self, *msg):
        if 'error' in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            logging.error(*msg)
    
    def warning(self, *msg):
        if 'warning' in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            logging.warning(*msg)

    def critical(self, *msg):
        if 'critical' in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            logging.critical(*msg)

    def log_remover(self):
        if self.logging_level is None or self.log_days is None or self.log_dir == 0:
            return
        for f in glob.glob(os.path.join(self.log_dir, '*.log')):
            if os.path.getmtime(f) < time.time() - self.log_days * 24 * 60 * 60:
                os.remove(f)
