# leveling print module stdprint.py

class Print:
    def __init__(self, log_levels=['info']):
        self.log_levels = log_levels
    
    def info(self, *msg):
        if 'info' in self.log_levels:
            print(*msg)
    
    def verbose(self, *msg):
        if 'verbose' in self.log_levels:
            print(*msg)

    def warning(self, *msg):
        if 'warning' in self.log_levels:
            print(*msg)
    
    def error(self, *msg):
        if 'error' in self.log_levels:
            print(*msg)
    
    def debug(self, *msg):
        if 'debug' in self.log_levels:
            print(*msg)
    
    def critical(self, *msg):
        if 'critical' in self.log_levels:
            print(*msg)
    
    def exception(self, *msg):
        if 'error' in self.log_levels:
            print(*msg)
