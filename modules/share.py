share = {}


def set(key, value):
    global share
    share[key] = value


def get(key):
    global share
    return share[key]
