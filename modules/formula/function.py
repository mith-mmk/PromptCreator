import math
import random
import re
import time

from .token import TOKENTYPE


def getValues(num, stack, args=None):
    if args is not None:
        return args[:num]
    # V1 mode
    values = []
    for _ in range(num):
        arg = stack.pop()
        values.append(arg)
    return values


def callFunction(compute, function, stack, args=None):
    match function:
        case "pow":
            values = getValues(2, stack, args=args)
            right = values[0]["value"]
            left = values[1]["value"]
            # right = stack.pop()
            # right = right["value"]
            # left = stack.pop()
            # left = left["value"]
            # どちらかが文字列ならエラー
            if type(left) is str or type(right) is str:
                compute.setTokenError(
                    "String is not suport power",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False, None
            return True, {"type": TOKENTYPE.NUMBER, "value": left**right}
        case "sqrt":
            value = getValues(1, stack, args=args)[0]["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport sqrt",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False, None
            return True, {"type": TOKENTYPE.NUMBER, "value": value**0.5}
        case "abs":
            value = getValues(1, stack, args=args)[0]["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport abs",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            return True, {"type": TOKENTYPE.NUMBER, "value": abs(value)}
        case "ceil":
            value = getValues(1, stack, args=args)[0]["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport ceil",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            return True, {"type": TOKENTYPE.NUMBER, "value": math.ceil(value)}
        case "floor":
            value = getValues(1, stack, args=args)[0]["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport floor",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            return True, {"type": TOKENTYPE.NUMBER, "value": math.floor(value)}
        case "round":
            value = getValues(1, stack, args=args)[0]["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport round",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            return True, {"type": TOKENTYPE.NUMBER, "value": round(value)}
        case "trunc":
            value = getValues(1, stack, args=args)[0]["value"]
            # 文字列ならエラー
            if type(value) is str:
                compute.setTokenError(
                    "String is not suport trunc",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
            return True, {"type": TOKENTYPE.NUMBER, "value": math.trunc(value)}
        case "int":
            value = getValues(1, stack, args=args)[0]
            return True, {"type": TOKENTYPE.NUMBER, "value": int(value["value"])}
        case "float":
            value = getValues(1, stack, args=args)[0]
            return True, {"type": TOKENTYPE.NUMBER, "value": float(value["value"])}
        case "str":
            value = getValues(1, stack, args=args)[0]
            return True, {"type": TOKENTYPE.STRING, "value": str(value["value"])}
        case "len":
            value = getValues(1, stack, args=args)[0]
            return True, {"type": TOKENTYPE.NUMBER, "value": len(value["value"])}
        case "max":
            if args is None:
                values = getValues(2, stack, args=args)
                right = values[0]["value"]
                left = values[1]["value"]
                if type(right) is str or type(left) is str:
                    tokentype = TOKENTYPE.STRING
                else:
                    tokentype = TOKENTYPE.NUMBER
                return True, {"type": tokentype, "value": max(right, left)}
            else:
                values = []
                for arg in args:
                    values.append(arg["value"])
                r_max = max(values)
                if type(r_max) is str:
                    tokentype = TOKENTYPE.STRING
                else:
                    tokentype = TOKENTYPE.NUMBER
                return True, {"type": tokentype, "value": r_max}

        case "min":
            if args is None:
                values = getValues(2, stack, args=args)
                right = values[0]["value"]
                left = values[1]["value"]
                tokentype = TOKENTYPE.NUMBER
                if type(right) is str or type(left) is str:
                    tokentype = TOKENTYPE.STRING
                else:
                    tokentype = TOKENTYPE.NUMBER
                return True, {"type": tokentype, "value": min(right, left)}
            else:
                values = []
                for arg in args:
                    values.append(arg["value"])
                r_min = min(values)
                if type(r_min) is str:
                    tokentype = TOKENTYPE.STRING
                else:
                    tokentype = TOKENTYPE.NUMBER
                return True, {"type": tokentype, "value": r_min}
        case "replace":  # replace(string, old, new)
            values = getValues(3, stack, args=args)
            new = values[0]["value"]
            old = values[1]["value"]
            string = values[2]["value"]
            return True, {"type": TOKENTYPE.STRING, "value": string.replace(old, new)}
        case "split":  # split(string, separator)
            values = getValues(2, stack, args=args)
            separator = values[0]["value"]
            string = values[1]["value"]
            string = str(string["value"])
            return True, {"type": TOKENTYPE.STRING, "value": string.split(separator)}
        case "upper":  # upper(string)
            string = getValues(1, stack, args=args)[0]
            return True, {
                "type": TOKENTYPE.STRING,
                "value": str(string["value"]).upper(),
            }
        case "lower":  # lower(string)
            string = getValues(1, stack, args=args)[0]
            return True, {
                "type": TOKENTYPE.STRING,
                "value": str(string["value"]).lower(),
            }

        case "if":  # if(condition, true, false)
            values = getValues(3, stack, args=args)
            false = values[0]
            true = values[1]
            condition = values[2]["value"]
            if condition == 1:
                return True, true
            else:
                return True, false
        case "not":  # not(condition)
            condition = getValues(1, stack, args=args)[0]["value"]
            if condition == 1:
                return True, {"type": TOKENTYPE.NUMBER, "value": 0}
            else:
                return True, {"type": TOKENTYPE.NUMBER, "value": 1}
        case "and":  # and(condition, condition)
            values = getValues(2, stack, args=args)
            right = values[0]["value"]
            left = values[1]["value"]
            if right == 1 and left == 1:
                return True, {"type": TOKENTYPE.NUMBER, "value": 1}
            else:
                return True, {"type": TOKENTYPE.NUMBER, "value": 0}
        case "or":  # or(condition, condition)
            values = getValues(2, stack, args=args)
            right = values[0]["value"]
            left = values[1]["value"]
            if right == 1 or left == 1:
                return True, {"type": TOKENTYPE.NUMBER, "value": 1}
            else:
                return True, {"type": TOKENTYPE.NUMBER, "value": 0}
        case "match":  # match(string, pattern)
            values = getValues(2, stack, args=args)
            pattern = values[0]["value"]
            string = values[1]["value"]
            if re.match(pattern, string):
                return True, {"type": TOKENTYPE.NUMBER, "value": 1}
            else:
                return True, {"type": TOKENTYPE.NUMBER, "value": 0}
        case "substring":  # substring(string, start, end)
            values = getValues(3, stack, args=args)
            end = values[0]["value"]
            start = values[1]["value"]
            string = values[2]["value"]
            return True, {"type": TOKENTYPE.STRING, "value": string[start:end]}
        case "random":  # random(start, end)
            values = getValues(2, stack, args=args)
            end = values[0]["value"]
            start = values[1]["value"]
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
                    return True, {
                        "type": TOKENTYPE.NUMBER,
                        "value": random.uniform(start, end),
                    }
                else:
                    return True, {
                        "type": TOKENTYPE.NUMBER,
                        "value": random.randint(start, end),
                    }
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
                return True, {
                    "type": TOKENTYPE.NUMBER,
                    "value": random.randint(0, 2**64 - 1),
                }
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
                return True, {"type": TOKENTYPE.NUMBER, "value": random.random()}
            except ValueError:
                compute.setTokenError(
                    "Random error",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
        case "random_string":  # randomstring(length)
            length = getValues(1, stack, args=args)[0]["value"]
            return True, {
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

        case "uuid":  # uuid()
            import uuid

            return True, {"type": TOKENTYPE.STRING, "value": str(uuid.uuid4())}
        case "time":  # time() as hh:mm:ss
            return True, {"type": TOKENTYPE.STRING, "value": time.strftime("%H:%M:%S")}
        case "date":  # date() as yyyy-mm-dd
            return True, {"type": TOKENTYPE.STRING, "value": time.strftime("%Y-%m-%d")}
        case "datetime":  # datetime() as yyyy-mm-dd hh:mm:ss
            return True, {
                "type": TOKENTYPE.STRING,
                "value": time.strftime("%Y-%m-%d %H:%M:%S"),
            }

        case "timestamp":  # timestamp() as yyyy-mm-dd hh:mm:ss
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.time())}
        case "year":  # year() as yyyy
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%Y"))}
        case "month":  # month() as mm
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%m"))}
        case "day":  # day() as dd
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%d"))}
        case "hour":  # hour() as hh
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%H"))}
        case "minute":  # minute() as mm
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%M"))}
        case "second":  # second() as ss
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%S"))}
        case "weekday":  # weekday() as 0-6
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%w"))}
        case "week":  # week() as 0-53
            return True, {"type": TOKENTYPE.NUMBER, "value": int(time.strftime("%W"))}
        # V2 functions
        case "contains":  # contains(string, substring)
            if compute.version < 2:
                values = getValues(2, stack, args=args)
                substring = values[0]["value"]
                string = values[1]["value"]
                if substring in string:
                    return True, {"type": TOKENTYPE.NUMBER, "value": 1}
                else:
                    return True, {"type": TOKENTYPE.NUMBER, "value": 0}
            else:  # V2
                if args is None or len(args) < 2:
                    compute.setTokenError(
                        "Contains error",
                        compute.token_start,
                        compute.token_end,
                        TOKENTYPE.ERROR,
                    )
                    return False
                args.reverse()
                string = args[0]["value"]
                substrings = args[1:]

                for substring in substrings:
                    if substring in string:
                        return True, {"type": TOKENTYPE.NUMBER, "value": 1}
                return True, {"type": TOKENTYPE.NUMBER, "value": 0}

        case _:
            try:
                if compute.version < 2:
                    compute.setTokenError(
                        "Unknown function",
                        compute.token_start,
                        compute.token_end,
                        TOKENTYPE.ERROR,
                    )
                    return False
                if args is not None:
                    args.reverse()
                    values = [arg["value"] for arg in args]
                else:
                    values = None
                value = compute.callbackFunction(function, args=values)
                if isinstance(value, int) or isinstance(value, float):
                    return True, {"type": TOKENTYPE.NUMBER, "value": value}
                elif isinstance(value, str):
                    return True, {"type": TOKENTYPE.STRING, "value": value}
                else:
                    compute.setTokenError(
                        "Unknown function return must be int, float or string",
                        compute.token_start,
                        compute.token_end,
                        TOKENTYPE.ERROR,
                    )
                    return False
            except:
                compute.setTokenError(
                    "Unknown function",
                    compute.token_start,
                    compute.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
