import datetime
import os

# *** LOGGER SEPC CHANGE *** 2023/08/24

global Logger
Logger = None

enum = {
    "debug": 10,
    "verbose": 15,  # 'verbose' is not in 'logging' module
    "info": 20,
    "warning": 30,
    "error": 40,
    "critical": 50,
    "notset": 60,
    "none": None,
}


def getDefaultLogger() -> "LogPrint":
    return getLogger("root")


def getLogger(service_name="root") -> "LogPrint":
    if type(Logger) is dict:
        if service_name in Logger:
            logger = Logger[service_name]
            return logger
    return LogPrint(service_name)


class LogPrint:
    def __init__(self, service_name="root"):
        global Logger
        self.service_name = service_name
        self.log_dir = None  # log file path if None, not write log file
        self.print_levels = ["info", "warning", "error", "critical"]  # print levels
        self.logging_level = 20
        self.log_days = None
        self.startMessage = False
        self.startDay = datetime.datetime.now()
        self.f = None
        if Logger is None:
            Logger = {}
        if self.service_name not in Logger:
            Logger[self.service_name] = self

    def setConfig(
        self,
        log_dir="./log",
        print_levels=["info", "warning", "error", "critical"],
        logging_level="info",
        log_days=7,
    ):
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
                self.debug("LogPrint logging start")
            self.startMessage = True

    def _initLogConfig(self):
        print(self.logging_level)
        if self.logging_level is None:
            return
        print(self.logging_level, self.log_dir, self.log_days)
        # self.log_dir ファイルがなければ作成
        if self.log_dir is None:
            return
        logfile = self.log_dir
        dirs = os.path.split(logfile)
        if not os.path.exists(dirs[0]):
            os.makedirs(dirs[0])
        if not os.path.exists(logfile):
            open(logfile, "w").close()

    def getPrintLevel(self):
        return self.print_levels

    def setLogDirectory(self, log_dir):
        self.log_dir = log_dir
        self._initLogConfig()

    def setLogDays(self, log_days):
        self.log_days = log_days

    def setPrintModes(self, print_levels):
        self.print_levels = print_levels

    def setFileMode(self, logging_level):
        self.logging_level = enum.get(logging_level) or 20

    def info(self, *msg):
        try:
            if "info" in self.print_levels:
                print(*msg)
            if self.logging_level is not None:
                if self.logging_level <= 20:
                    self.write("info", *msg)
        except Exception:
            print(*msg)

    def verbose(self, *msg):
        if "verbose" in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            if self.logging_level <= 15:
                self.write("verbose", *msg)

    def debug(self, *msg):
        if "debug" in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            if self.logging_level <= 10:
                self.write("debug", *msg)

    def error(self, *msg):
        if "error" in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            if self.logging_level <= 40:
                self.write("error", *msg)

    def warning(self, *msg):
        if "warning" in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            if self.logging_level <= 30:
                self.write("warning", *msg)

    def critical(self, *msg):
        if "critical" in self.print_levels:
            print(*msg)
        if self.logging_level is not None:
            if self.logging_level <= 50:
                self.write("critical", *msg)

    def write(self, logging_level, *msg):
        if self.logging_level is None:
            return
        if self.log_dir is None:
            return
        #  logging_level -> key
        for key, value in enum.items():
            if value == logging_level:
                logging_level = key
                break
        now = datetime.datetime.now()
        now = now.strftime("%Y-%m-%d %H:%M:%S,%f")
        string = f"{now}:[{logging_level}] {self.service_name}: "
        if self.f is None:
            f = open(self.log_dir, "a")
            self.f = f
        if type(msg) is tuple:
            msg = list(msg)
        if type(msg) is list:
            msg = [str(i) for i in msg]
            msg = format(" ".join(msg))
        else:
            msg = str(msg)
        try:
            self.f.write(string + msg + "\n")
            self.f.flush()
        except Exception as e:
            print(e)
            try:
                f = open(self.log_dir, "a")
                f.write(string + msg + "\n")
                self.f = f
                self.f.flush()
            except Exception as e:
                print(e)
                self.f = None
                return
        self.log_rotate()

    def log_rotate(self):
        if self.logging_level is None:
            return
        now = datetime.datetime.now()
        # 日付をまたいでいない場合はreturn
        now = now.strftime("%Y%m%d")
        start = self.startDay.strftime("%Y%m%d")
        if now <= start:
            return
        if not os.path.exists(self.log_dir):
            return
        # log_dir + '.' + str(i) は削除
        try:
            self.f.close()
        except Exception:
            print("log file close error")
        i = self.log_days
        if i > 0:
            final_logfile = self.log_dir + "." + str(i)
            if os.path.exists(final_logfile):
                os.remove(final_logfile)
            # log_dir は log_dir + '.' + str(1) にrename
            logfile = self.log_dir
            if os.path.exists(logfile):
                try:
                    while i > 0:
                        # log_dir + '.' + str(i-1) は log_dir + '.' + str(i) にrename
                        rn_logfile = self.log_dir + "." + str(i - 1)
                        if os.path.exists(rn_logfile):
                            os.rename(rn_logfile, final_logfile)
                        final_logfile = rn_logfile
                        i -= 1
                    os.rename(logfile, f"{logfile}.1")
                except Exception as e:
                    print(e)
            open(logfile, "w").close()
            # update startDay
            self.startDay = now

    def stdout(self, *msg):
        print(*msg)


LogPrint("service")
