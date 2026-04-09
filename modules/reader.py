import copy
import json
import os
import re
import sqlite3

from modules.logger import getDefaultLogger

Logger = getDefaultLogger()

SQLITE_INTERNAL_COLUMNS = {
    "id",
    "raw_json",
    "choice_json",
    "variables_json",
    "attributes",
}


def _split_references(text):
    refs = []
    current = []
    depth = 0
    for ch in text:
        if ch == "[":
            depth += 1
            current.append(ch)
        elif ch == "]":
            depth = max(depth - 1, 0)
            current.append(ch)
        elif ch.isspace() and depth == 0:
            if current:
                refs.append("".join(current))
                current = []
        else:
            current.append(ch)
    if current:
        refs.append("".join(current))
    return refs


def _strip_jsonl_comments(all_text):
    all_text = re.sub(r"/\*.*?\*/", "", all_text, flags=re.DOTALL)
    lines = all_text.split("\n")
    stripped = []
    for item in lines:
        item = re.sub(r"\s*\/\/.*$", "", item)
        if re.match(r"^\s*$", item):
            continue
        stripped.append(item)
    return stripped


def _listify(value, default=None):
    if value is None:
        return default if default is not None else []
    if isinstance(value, list):
        return value
    return [value]


def _decode_json_value(value):
    if not isinstance(value, str):
        return value
    stripped = value.strip()
    if stripped == "":
        return value
    if (
        (stripped.startswith("[") and stripped.endswith("]"))
        or (stripped.startswith("{") and stripped.endswith("}"))
        or (stripped.startswith('"') and stripped.endswith('"'))
        or stripped in {"true", "false", "null"}
        or re.match(r"^-?\d+(\.\d+)?$", stripped)
    ):
        try:
            return json.loads(stripped)
        except json.JSONDecodeError:
            return value
    return value


def _normalize_item(item, queries=None, default_weight=0.1):
    item = copy.deepcopy(item)
    if not isinstance(item, dict):
        return item_split_txt(item, default_weight=default_weight)

    if "raw_json" in item:
        try:
            raw_item = json.loads(item["raw_json"])
            if isinstance(raw_item, dict):
                merged_item = raw_item
                for key, value in item.items():
                    if key != "raw_json" and value is not None:
                        merged_item[key] = value
                item = merged_item
        except Exception:
            Logger.warning("raw_json decode error in database row")

    for key in list(item.keys()):
        item[key] = _decode_json_value(item[key])

    attributes = item.get("attributes")
    if isinstance(attributes, dict):
        for key, value in attributes.items():
            if key not in item:
                item[key] = value

    if "choice_json" in item and "C" not in item and "choice" not in item:
        item["choice"] = _decode_json_value(item["choice_json"])
    if "variables_json" in item and "V" not in item and "variables" not in item:
        item["variables"] = _decode_json_value(item["variables_json"])

    if "W" in item:
        item["weight"] = item.pop("W")
    elif "weigth" in item and "weight" not in item:
        item["weight"] = item.pop("weigth")
    else:
        item["weight"] = item.get("weight", default_weight)

    if "V" in item:
        value = item.pop("V")
    elif "variable" in item and "variables" not in item:
        value = item.pop("variable")
    else:
        value = item.get("variables", [""])
    value = _listify(value, [""])
    if len(value) == 0:
        value = [""]
    item["variables"] = value

    if "C" in item:
        choice = item.pop("C")
    elif "category" in item and "choice" not in item:
        choice = item.get("category")
    else:
        choice = item.get("choice", ["*"])
    choice = _listify(choice, ["*"])
    if len(choice) == 0:
        choice = ["*"]
    item["choice"] = choice

    if queries is not None:
        item["query"] = _build_query_text(choice, queries)

    if "__name__" in item and "name" not in item:
        item["name"] = item["__name__"]
    if "name" in item and "__name__" not in item:
        item["__name__"] = item["name"]

    for key in SQLITE_INTERNAL_COLUMNS:
        if key in item:
            del item[key]

    return item


def _build_query_text(choice, queries):
    matched = []
    for selected in choice:
        if isinstance(selected, dict):
            for key in selected.keys():
                if key in queries:
                    matched.append(key)
        elif selected != "*" and selected in queries:
            matched.append(selected)
    return ",".join(dict.fromkeys(matched))


def _append_matching_item(strs, item, queries):
    normalized = _normalize_item(item, queries=queries)
    choice = normalized.pop("choice", ["*"])
    for query in queries:
        if "*" in choice or query == "*" or query in choice:
            strs.append(copy.deepcopy(normalized))
        else:
            for key in choice:
                if isinstance(key, dict) and query in key:
                    weighted_item = copy.deepcopy(normalized)
                    weighted_item["weight"] = key[query]
                    strs.append(weighted_item)
                    break


def _parse_jsonl_reference(filename):
    q = re.match(r"(.+\.jsonl)\[(.+)\]", filename)
    if q is None:
        return filename, ["*"]
    query = q.group(2)
    queries = [item.strip() for item in query.split(",") if item.strip()]
    return q.group(1), queries


def _expand_queries(queries, query_suffixes):
    expanded = copy.deepcopy(queries)
    if query_suffixes is not None:
        for suffix in query_suffixes:
            for query in queries:
                expanded.append(query + suffix)
    return list(dict.fromkeys(expanded))


def _is_db_reference(filename, database):
    if not database or not isinstance(filename, str):
        return False
    if os.path.splitext(filename)[1]:
        return False
    if os.path.exists(filename):
        return False
    return re.match(r"^[^\[\]]+(\[.+\])?$", filename) is not None


def _parse_db_reference(reference):
    match = re.match(r"^([^\[\]]+?)(?:\[(.+)\])?$", reference)
    if match is None:
        raise ValueError(f"invalid database reference {reference}")
    table = match.group(1).strip()
    condition_text = match.group(2)
    conditions = []
    if condition_text:
        parts = re.split(r"\s+(?:and|AND)\s+", condition_text)
        for part in parts:
            part = part.strip()
            cond = re.match(
                r"^([a-zA-Z_][a-zA-Z0-9_]*)\s*=\s*(?:`([^`]+)`|\"([^\"]+)\"|'([^']+)'|(.+))$",
                part,
            )
            if cond is None:
                raise ValueError(f"invalid database condition {part}")
            conditions.append(
                (cond.group(1), cond.group(2) or cond.group(3) or cond.group(4) or cond.group(5).strip())
            )
    return table, conditions


def _match_db_conditions(item, conditions):
    if not conditions:
        return True
    normalized = _normalize_item(item)
    choice = normalized.get("choice", ["*"])
    for key, expected in conditions:
        if key == "category":
            if expected not in choice and "*" not in choice:
                return False
            continue
        actual_key = "__name__" if key == "__name__" else key
        if actual_key == "__name__" and actual_key not in normalized:
            actual_key = "name"
        actual = normalized.get(actual_key)
        if isinstance(actual, list):
            if expected not in [str(value) for value in actual]:
                return False
        elif actual is None:
            return False
        elif str(actual) != expected:
            return False
    return True


def _queries_from_conditions(conditions):
    queries = []
    for key, expected in conditions:
        if key == "category":
            queries.append(expected)
    return queries


def _read_db_rows(reference, database):
    db_type = database.get("db")
    connection = database.get("db_connection")
    if db_type != "sqlite3":
        raise NotImplementedError(f"database type {db_type} is not supported")
    if not connection:
        raise ValueError("database.db_connection is not set")

    table, conditions = _parse_db_reference(reference)
    try:
        conn = sqlite3.connect(connection)
        conn.row_factory = sqlite3.Row
    except sqlite3.Error as e:
        raise RuntimeError(f"database connection error {connection}: {e}") from e

    try:
        query = f'SELECT * FROM "{table}"'
        rows = conn.execute(query).fetchall()
    except sqlite3.Error as e:
        raise RuntimeError(f"database read error {table}: {e}") from e
    finally:
        conn.close()

    queries = _queries_from_conditions(conditions)
    filtered_rows = []
    for row in rows:
        row_dict = dict(row)
        if not _match_db_conditions(row_dict, conditions):
            continue
        if queries:
            row_dict["query"] = ",".join(queries)
        filtered_rows.append(row_dict)
    return filtered_rows


def read_file(filename, error_info="", query_suffixes=None, database=None):
    return read_file_v2(filename, error_info, query_suffixes, database=database)


def read_file_v2(filename, error_info="", query_suffixes=None, database=None):
    Logger.debug(f"read_file_v2 {filename} {error_info} {query_suffixes}")
    strs = []
    filenames = _split_references(filename)
    for current_filename in filenames:
        Logger.debug(f"read_file_v2 {current_filename}")
        try:
            ext = os.path.splitext(current_filename)[-1:][0]
            if re.match(r"(.+\.jsonl)\[(.+)\]", current_filename) or ext == ".jsonl":
                Logger.debug("load jsonl")
                current_filename, queries = _parse_jsonl_reference(current_filename)
                queries = _expand_queries(queries, query_suffixes)
                Logger.debug(f"query {queries}")
                with open(current_filename, "r", encoding="utf_8") as f:
                    lines = _strip_jsonl_comments(f.read())
                    try:
                        for idx, item in enumerate(lines):
                            parsed = json.loads(item)
                            if parsed is None:
                                continue
                            _append_matching_item(strs, parsed, queries)
                    except Exception as e:
                        Logger.error(
                            f"json decode error {current_filename} line{idx + 1} {item} {e}"
                        )
                Logger.debug(f"strs {strs}")
            elif _is_db_reference(current_filename, database):
                Logger.debug("load database")
                rows = _read_db_rows(current_filename, database)
                for row in rows:
                    strs.append(_normalize_item(row))
            elif ext == ".json":
                with open(current_filename, "r", encoding="utf_8") as f:
                    json_data = json.load(f)
                    if isinstance(json_data, list):
                        for item in json_data:
                            strs.append(_normalize_item(item))
            else:
                with open(current_filename, "r", encoding="utf_8") as f:
                    for i, item in enumerate(f.readlines()):
                        if re.match(r"^\s*#.*", item) or re.match(r"^\s*$", item):
                            continue
                        item = re.sub(r"\s*#.*$", "", item)
                        try:
                            strs.append(item_split_txt(item))
                        except Exception:
                            Logger.error(
                                f"Error happen line {error_info} {current_filename} {i} {item}"
                            )
        except FileNotFoundError:
            Logger.error(f"{current_filename} is not found")
            raise FileNotFoundError(f"{current_filename} is not found")
    return strs


def item_split_txt(item, error_info="", default_weight=0.1):
    if type(item) is not str:
        if type(item) is dict:
            item = copy.deepcopy(item)
            item["variables"] = item.get("V", item.get("variables", []))
            if not isinstance(item["variables"], list):
                item["variables"] = [item["variables"]]
            if "V" in item:
                del item["V"]
            item["weight"] = item.get(
                "W", item.get("weight", item.get("weigth", default_weight))
            )
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
