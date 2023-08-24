from logging.handlers import TimedRotatingFileHandler
import logging
import os

# *** LOGGER SEPC CHANGE *** 2023/08/24

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
            logfile = self.log_dir
            # split logfile for dircetory and filename
            dirs = os.path.split(logfile)
            if not os.path.exists(dirs[0]):
                os.makedirs(dirs[0])
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
        print(self.logging_level, self.log_dir, self.log_days)
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', filename=self.log_dir)
        # CHANGE 2023/08/24 rotate log file
        handler = TimedRotatingFileHandler(filename=self.log_dir, when='midnight', backupCount=self.log_days)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
        logger = logging.getLogger("run-loop")
        logger.setLevel(self.logging_level)
        logger.addHandler(handler)
   
    def setLogDirectory(self, log_dir):
        self.log_dir = log_dir
        self._initLogConfig()

    def setLogDays(self, log_days):
        self.log_days = log_days
    
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
