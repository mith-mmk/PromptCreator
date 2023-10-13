import re

import modules.logger as logger
from modules.prompt import item_split

# Read a file and return a list of prompt
Logger = logger.getDefaultLogger()


def read_file(filename):
    strs = []
    filenames = filename.split()
    for filename in filenames:
        try:
            with open(filename, "r", encoding="utf_8") as f:
                for i, item in enumerate(f.readlines()):
                    if re.match(r"^\s*#.*", item) or re.match(r"^\s*$", item):
                        continue
                    item = re.sub(r"\s*#.*$", "", item)
                    try:
                        strs.append(item_split(item))
                    except Exception:
                        Logger.error(f"Error happen line {filename} {i} {item}")
        except FileNotFoundError:
            Logger.error(f"{filename} is not found")
            raise FileNotFoundError
    return strs
