import math
import random
import re
import time

from .token import TOKENTYPE


def callFunction(compute, function, stack):
    match function:
        case "pow":
            right = stack.pop()
            right = right["value"]
            left = stack.pop()
            left = left["value"]
            # どちらかが文字列ならエラー
            if type(left) is str or type(right) is str:
                compute.setTokenError(
                    "String is not suport power",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            stack.append({"type": TOKENTYPE.NUMBER, "value": left**right})
        case "sqrt":
            value = stack.pop()
            value = value["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport sqrt",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            stack.append({"type": TOKENTYPE.NUMBER, "value": value**0.5})
        case "abs":
            value = stack.pop()
            value = value["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport abs",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            stack.append({"type": TOKENTYPE.NUMBER, "value": abs(value)})
        case "ceil":
            value = stack.pop()
            value = value["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport ceil",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            stack.append({"type": TOKENTYPE.NUMBER, "value": math.ceil(value)})
        case "floor":
            value = stack.pop()
            value = value["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport floor",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            stack.append({"type": TOKENTYPE.NUMBER, "value": math.floor(value)})
        case "round":
            value = stack.pop()
            value = value["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport round",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            stack.append({"type": TOKENTYPE.NUMBER, "value": round(value)})
        case "trunc":
            value = stack.pop()
            value = value["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport trunc",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            stack.append({"type": TOKENTYPE.NUMBER, "value": math.trunc(value)})
        case "int":
            value = stack.pop()
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(value["value"])})
        case "float":
            value = stack.pop()
            stack.append({"type": TOKENTYPE.NUMBER, "value": float(value["value"])})
        case "str":
            value = stack.pop()
            stack.append({"type": TOKENTYPE.STRING, "value": str(value["value"])})
        case "len":
            value = stack.pop()
            stack.append({"type": TOKENTYPE.NUMBER, "value": len(value["value"])})
        case "max":
            right = stack.pop()
            right = right["value"]
            left = stack.pop()
            left = left["value"]
            if type(right) is str or type(left) is str:
                tokentype = TOKENTYPE.STRING
            else:
                tokentype = TOKENTYPE.NUMBER
            stack.append({"type": tokentype, "value": max(right, left)})
        case "min":
            right = stack.pop()
            right = right["value"]
            left = stack.pop()
            left = left["value"]
            tokentype = TOKENTYPE.NUMBER
            if type(right) is str or type(left) is str:
                tokentype = TOKENTYPE.STRING
            else:
                tokentype = TOKENTYPE.NUMBER
            stack.append({"type": tokentype, "value": min(right, left)})
        case "replace":  # replace(string, old, new)
            new = stack.pop()
            new = str(new["value"])
            old = stack.pop()
            old = str(old["value"])
            string = stack.pop()
            string = str(string["value"])
            stack.append({"type": TOKENTYPE.STRING, "value": string.replace(old, new)})
        case "split":  # split(string, separator)
            separator = stack.pop()
            separator = str(separator["value"])
            string = stack.pop()
            string = str(string["value"])
            stack.append({"type": TOKENTYPE.STRING, "value": string.split(separator)})
        case "upper":  # upper(string)
            string = stack.pop()
            stack.append(
                {"type": TOKENTYPE.STRING, "value": str(string["value"]).upper()}
            )
        case "lower":  # lower(string)
            string = stack.pop()
            stack.append(
                {"type": TOKENTYPE.STRING, "value": str(string["value"]).lower()}
            )
        case "if":  # if(condition, true, false)
            false = stack.pop()
            true = stack.pop()
            condition = stack.pop()
            condition = condition["value"]
            if condition == 1:
                stack.append(true)
            else:
                stack.append(false)
        case "not":  # not(condition)
            condition = stack.pop()
            condition = condition["value"]
            if condition == 1:
                stack.append({"type": TOKENTYPE.NUMBER, "value": 0})
            else:
                stack.append({"type": TOKENTYPE.NUMBER, "value": 1})
        case "and":  # and(condition, condition)
            right = stack.pop()
            right = right["value"]
            left = stack.pop()
            left = left["value"]
            if right == 1 and left == 1:
                stack.append({"type": TOKENTYPE.NUMBER, "value": 1})
            else:
                stack.append({"type": TOKENTYPE.NUMBER, "value": 0})
        case "or":  # or(condition, condition)
            right = stack.pop()
            right = right["value"]
            left = stack.pop()
            left = left["value"]
            if right == 1 or left == 1:
                stack.append({"type": TOKENTYPE.NUMBER, "value": 1})
            else:
                stack.append({"type": TOKENTYPE.NUMBER, "value": 0})
        case "match":  # match(string, pattern)
            pattern = stack.pop()
            pattern = pattern["value"]
            string = stack.pop()
            string = string["value"]
            if re.match(pattern, string):
                stack.append({"type": TOKENTYPE.NUMBER, "value": 1})
            else:
                stack.append({"type": TOKENTYPE.NUMBER, "value": 0})
        case "substring":  # substring(string, start, end)
            end = stack.pop()
            end = end["value"]
            start = stack.pop()
            start = start["value"]
            string = stack.pop()
            string = string["value"]
            stack.append({"type": TOKENTYPE.STRING, "value": string[start:end]})
        case "random":  # random(start, end)
            end = stack.pop()
            end = end["value"]
            start = stack.pop()
            start = start["value"]
            if start > end:
                compute.setTokenError(
                    "Random error start > end",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            try:
                if type(start) is float or type(end) is float:
                    stack.append(
                        {"type": TOKENTYPE.NUMBER, "value": random.uniform(start, end)}
                    )
                else:
                    stack.append(
                        {"type": TOKENTYPE.NUMBER, "value": random.randint(start, end)}
                    )
            except ValueError:
                compute.setTokenError(
                    "Random error must number",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
        case "random_int":  # randomint(0, 2^64 -1)
            try:
                stack.append(
                    {"type": TOKENTYPE.NUMBER, "value": random.randint(0, 2**64 - 1)}
                )
            except ValueError:
                compute.setTokenError(
                    "Random error",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
        case "random_float":  # randomfloat(0, 1)
            try:
                stack.append({"type": TOKENTYPE.NUMBER, "value": random.random()})
            except ValueError:
                compute.setTokenError(
                    "Random error",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
        case "random_string":  # randomstring(length)
            length = stack.pop()
            length = length["value"]
            stack.append(
                {
                    "type": TOKENTYPE.STRING,
                    "value": "".join(
                        [
                            random.choice(
                                "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
                            )
                            for i in range(length)
                        ]
                    ),
                }
            )
        case "uuid":  # uuid()
            import uuid

            stack.append({"type": TOKENTYPE.STRING, "value": str(uuid.uuid4())})
        case "time":  # time() as hh:mm:ss
            stack.append({"type": TOKENTYPE.STRING, "value": time.strftime("%H:%M:%S")})
        case "date":  # date() as yyyy-mm-dd
            stack.append({"type": TOKENTYPE.STRING, "value": time.strftime("%Y-%m-%d")})
        case "datetime":  # datetime() as yyyy-mm-dd hh:mm:ss
            stack.append(
                {"type": TOKENTYPE.STRING, "value": time.strftime("%Y-%m-%d %H:%M:%S")}
            )
        case "timestamp":  # timestamp() as yyyy-mm-dd hh:mm:ss
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.time())})
        case "year":  # year() as yyyy
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%Y"))})
        case "month":  # month() as mm
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%m"))})
        case "day":  # day() as dd
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%d"))})
        case "hour":  # hour() as hh
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%H"))})
        case "minute":  # minute() as mm
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%M"))})
        case "second":  # second() as ss
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%S"))})
        case "weekday":  # weekday() as 0-6
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%w"))})
        case "week":  # week() as 0-53
            stack.append({"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%W"))})
        case (
            "chained"
        ):  # chained("variable", weight, max_number, joiner) # variabel is string
            # weight is 0.0 - 1.0   max_number is int > 0
            max_number = stack.pop()
            max_number = max_number["value"]
            if isinstance(max_number, int) is False or max_number <= 0:
                compute.setTokenError(
                    "Chained max_number must be int > 0",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            weight = stack.pop()
            weight = weight["value"]
            if isinstance(weight, float) is False or (weight < 0 and weight > 1):
                compute.setTokenError(
                    "Chained weight must be float >= 0",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            variable = stack.pop()
            variable = variable["value"]
            if isinstance(variable, str) is False:
                compute.setTokenError(
                    "Chained variable must be string",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            value = compute.getChained(variable, weight, max_number)
            if isinstance(value, int) or isinstance(value, float):
                stack.append({"type": TOKENTYPE.NUMBER, "value": value})
            elif isinstance(value, str):
                stack.append({"type": TOKENTYPE.STRING, "value": value})
            else:
                compute.setTokenError(
                    "Chained parse error, must be int, float or string",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
            return False
        case _:
            compute.setTokenError(
                "Unknown function",
                compute.token_start,
                compute.token_end,
                TOKENTYPE.ERROR,
            )
            return False
    return True
