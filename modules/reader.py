import copy
import json
import os
import re

from modules.logger import getDefaultLogger

Logger = getDefaultLogger()


def read_file(filename, error_info="", query_suffixes=None):
    return read_file_v2(filename, error_info, query_suffixes)


def read_file_v2(filename, error_info="", query_suffixes=None):
    Logger.debug(f"read_file_v2 {filename} {error_info} {query_suffixes}")
    strs = []
    filenames = filename.split()
    for filename in filenames:
        Logger.debug(f"read_file_v2 {filename}")
        try:
            ext = os.path.splitext(filenames[0])[-1:][0]
            if re.match(r"(.+\.jsonl)\[(.+)\]", filename) or ext == ".jsonl":
                Logger.debug("load jsonl")
                if ext == ".jsonl":
                    query = "*"
                    queries = ["*"]
                else:
                    q = re.match(r"(.+\.jsonl)\[(.+)\]", filename)
                    if q is not None:
                        filename = q.group(1)
                        query = q.group(2)
                    queries = query.split(",")
                    # trim space
                    for i, q in enumerate(queries):
                        queries[i] = q.strip()

                qs = copy.deepcopy(queries)
                if query_suffixes is not None:
                    # add query_prefixes to queries
                    for suffix in query_suffixes:
                        for query in qs:
                            queries.append(query + suffix)
                Logger.debug(f"query {queries}")
                with open(filename, "r", encoding="utf_8") as f:
                    all_text = f.read()
                    # /* */ を削除 \n をまたぐので注意
                    all_text = re.sub(r"/\*.*?\*/", "", all_text, flags=re.DOTALL)
                    lines = all_text.split("\n")
                    try:
                        for idx, item in enumerate(lines):
                            # comment out を削除
                            item = re.sub(r"\s*\/\/.*$", "", item)
                            # gg(f"line {idx + 1} item {item}")
                            if re.match(r"^\s*$", item):
                                continue
                            item = json.loads(item)
                            if item is None:
                                continue
                            # replace W => weight V => variables C => choice
                            if "W" in item:
                                item["weight"] = item.get("W", 0.1)
                                del item["W"]
                            else:
                                item["weight"] = 0.1
                            if "V" in item:
                                value = item.get("V", [""])
                                if type(value) is not list:
                                    value = [value]
                                if len(value) == 0:
                                    value = [""]  # empty string
                                item["variables"] = value
                                del item["V"]
                            if "C" in item:
                                choice = item.get("C", [])
                                if isinstance(choice, str):
                                    choice = [choice]
                                item["choice"] = item.get("C", [])
                                del item["C"]
                                if isinstance(item.get("choice"), list):
                                    _query = ""
                                    for i, c in enumerate(item["choice"]):
                                        if isinstance(c, dict):
                                            keys = c.keys()
                                            for key in keys:
                                                if key in queries:
                                                    if _query != "":
                                                        _query = _query + "," + key
                                                        break
                                        if c != "*":
                                            if _query != "":
                                                _query = _query + "," + c
                                    item["query"] = _query.strip(",")
                            else:
                                item["choice"] = ["*"]
                            Logger.debug(f"replaced item {item}")
                            choice = item.get("choice", ["*"])
                            if "choice" in item:
                                del item["choice"]
                            # queries にマッチするものを取り出す
                            for query in queries:
                                if "*" in choice or query == "*" or query in choice:
                                    strs.append(item)
                                else:  # keyを探す weight override
                                    for key in choice:
                                        if type(key) is not str:
                                            if query in key:
                                                Logger.debug(f"key {key}")
                                                item["weight"] = key[query]
                                                strs.append(item)
                                                break
                    except Exception as e:
                        Logger.error(
                            f"json decode error {filename} line{idx + 1} {item} {e}"
                        )
                Logger.debug(f"strs {strs}")
            elif ext == ".json":
                with open(filename, "r", encoding="utf_8") as f:
                    json_data = json.load(f)
                    if type(json_data) is list:
                        parsed = []
                        for item in json_data:
                            if "W" in item:
                                item["weight"] = item.get("W", 0.1)
                                del item["W"]
                            if "C" in item:
                                item["choice"] = item.get("C", [])
                                del item["C"]
                            if "V" in item:
                                item["variables"] = item.get("V", [])
                                del item["V"]
                            parsed.append(item)
                        strs.extend(parsed)
            else:
                with open(filename, "r", encoding="utf_8") as f:
                    for i, item in enumerate(f.readlines()):
                        if re.match(r"^\s*#.*", item) or re.match(r"^\s*$", item):
                            continue
                        item = re.sub(r"\s*#.*$", "", item)
                        try:
                            strs.append(item_split_txt(item))
                        except Exception:
                            Logger.error(
                                f"Error happen line {error_info} {filename} {i} {item}"
                            )
        except FileNotFoundError:
            Logger.error(f"{filename} is not found")
            raise FileNotFoundError(f"{filename} is not found")
    return strs


# create_prompt v2
def item_split_txt(item, error_info="", default_weight=0.1):
    if type(item) is not str:
        if type(item) is dict:
            item["variables"] = item.get("V", [])
            if item["variables"] is not list:
                item["variables"] = [item["variables"]]
            if "V" in item:
                del item["V"]
            item["weight"] = item.get("W", default_weight)
            if "W" in item:
                del item["W"]
            if "C" in item:
                del item["C"]
            return item
        Logger.warning(f"item {item} is not str {type(item)}")
        return {"variables": [str(item)], "weight": default_weight}
    item = item.replace("\n", " ").strip().replace(r"\;", r"${semicolon}")
    split = item.split(";")

    if type(split) is list:
        for i in range(0, len(split)):
            split[i] = split[i].replace(r"${semicolon}", ";")
    try:
        weight = float(split[0])
        if len(split) == 1:
            return {"weight": default_weight, "variables": [weight]}
    except ValueError:
        Logger.debug(f"weight convert error use defaut {error_info} {split[0]}")
        weight = default_weight
        return {"weight": weight, "variables": split}
    variables = split[1:]
    return {"weight": weight, "variables": variables}
