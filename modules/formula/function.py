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
            values = getValues(2, stack, args=args)
            substring = values[0]["value"]
            string = values[1]["value"]
            if substring in string:
                return True, {"type": TOKENTYPE.NUMBER, "value": 1}
            else:
                return True, {"type": TOKENTYPE.NUMBER, "value": 0}
        # case "value":
        #    # value( a ) return  expanned value
        #    string = getValues(1, stack, args=args)[0]["value"]
        #    value = compute.getValue(string)
        #    if isinstance(string, str):
        #        return True, {
        #            "type": TOKENTYPE.STRING,
        #            "value": compute.getValue(string),
        #        }
        #    else:
        #        return True, {"type": TOKENTYPE.STRING, "value": str(string)}
        #        case "choice_index":
        #            variables = getValues(3, stack, args=args)
        #            index = variables[0].get("value", 1)
        #            choice = variables[1].get("value", -1.0)
        #            variable = variables[2].get("value", "")
        #            if isinstance(variable, str) is False:
        #                compute.setTokenError(
        #                    "Choice variable must be string",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Choice variable must be string")
        #            try:
        #                choice = float(choice)
        #            except ValueError:
        #                compute.setTokenError(
        #                    "Choice index must be float 0..1",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Choice index must be float")
        #            if isinstance(index, int) is False:
        #                compute.setTokenError(
        #                    "Choice index must be int >= 1",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Choice index must be int >= 1")
        #
        #            return True, {
        #                "type": TOKENTYPE.NUMBER,
        #                "value": compute.getChoiceIndex(variable, choice, index),
        #            }
        #        case "choice_attribute":
        #            variables = getValues(3, stack, args=args)
        #            attribute = variables[0].get("value", "")
        #            choice = variables[1].get("value", -1.0)
        #            variable = variables[2].get("value", "")
        #            if isinstance(attribute, str) is False:
        #                compute.setTokenError(
        #                    "Choice attribute must be string",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Choice attribute must be string")
        #            if isinstance(variable, str) is False:
        #                compute.setTokenError(
        #                    "Choice variable must be string",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Choice variable must be string")
        #            try:
        #                choice = float(choice)
        #            except ValueError:
        #                compute.setTokenError(
        #                    "Choice index must be float 0..1",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Choice index must be float")
        #            return True, {
        #                "type": TOKENTYPE.NUMBER,
        #                "value": compute.getChoiceAttribute(variable, choice, attribute),
        #            }
        #        case "choice":
        #            # choice("a") a is variable name = chained("a", 1, 1)
        #            variable = getValues(1, stack, args=args)[0]["value"]
        #            if isinstance(variable, str) is False:
        #                compute.setTokenError(
        #                    "Chained variable must be string",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Chained variable must be string")
        #            try:
        #                value = compute.getChained(variable, 1, 1)
        #            except Exception as e:
        #                compute.setTokenError(
        #                    "Chained error",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise e
        #            if isinstance(value, int) or isinstance(value, float):
        #                return True, {"type": TOKENTYPE.NUMBER, "value": value}
        #            elif isinstance(value, str):
        #                return True, {"type": TOKENTYPE.STRING, "value": value}
        #            else:
        #                compute.setTokenError(
        #                    "Chained parse error, must be int, float or string",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #            return False
        #        case (
        #            "chained"
        #        ):  # chained("variable", weight, max_number, joiner) # variabel is string
        #            # weight is 0.0 - 1.0   max_number is int > 0
        #            joiner = " "
        #            next_multiply = 1
        #
        #            if args is None:
        #                values = getValues(3, stack, args=args)
        #                max_number = values[0]["value"]
        #                weight = values[1]["value"]
        #                variable = values[2]["value"]
        #            else:
        #                args.reverse()
        #                if len(args) < 2:
        #                    compute.setTokenError(
        #                        "Chained must have 3 arguments",
        #                        compute.token_start,
        #                        compute.token_end,
        #                        TOKENTYPE.ERROR,
        #                    )
        #                    return False
        #                variable = args[0]["value"]
        #                weight = args[1]["value"]
        #                if len(args) > 2:
        #                    max_number = args[2]["value"]
        #                else:
        #                    max_number = 10
        #                if len(args) > 3:
        #                    joiner = args[3]["value"]
        #                if len(args) > 4:
        #                    next_multiply = args[4]["value"]
        #
        #            if isinstance(weight, float) is False or (weight < 0 and weight > 1):
        #                compute.setTokenError(
        #                    "Chained weight must be float >= 0",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Chained weight must be float >= 0")
        #            if isinstance(variable, str) is False:
        #                compute.setTokenError(
        #                    "Chained variable must be string",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise Exception("Chained variable must be string")
        #            try:
        #                value = compute.getChained(
        #                    variable,
        #                    weight,
        #                    max_number,
        #                    joiner=joiner,
        #                    next_multiply=next_multiply,
        #                )
        #            except Exception as e:
        #                compute.setTokenError(
        #                    "Chained error",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #                raise e
        #            if isinstance(value, int) or isinstance(value, float):
        #                return True, {"type": TOKENTYPE.NUMBER, "value": value}
        #            elif isinstance(value, str):
        #                return True, {"type": TOKENTYPE.STRING, "value": value}
        #            else:
        #                compute.setTokenError(
        #                    "Chained parse error, must be int, float or string",
        #                    compute.token_start,
        #                    compute.token_end,
        #                    TOKENTYPE.ERROR,
        #                )
        #            return False
        #
        #       case "attribute":
        #           values = getValues(2, stack, args=args)
        #           attribute = values[0]["value"]
        #           variable = values[1]["value"]
        #           if isinstance(attribute, str) is False:
        #               compute.setTokenError(
        #                   "Attribute must be string",
        #                   compute.token_start,
        #                   compute.token_end,
        #                   TOKENTYPE.ERROR,
        #               )
        #               raise Exception("Attribute must be string")
        #           if isinstance(variable, str) is False:
        #               compute.setTokenError(
        #                   "Variable must be string",
        #                   compute.token_start,
        #                   compute.token_end,
        #                   TOKENTYPE.ERROR,
        #               )
        #               raise Exception("Variable must be string")
        #           try:
        #               value = compute.getAttribute(variable, attribute)
        #           except Exception as e:
        #               compute.setTokenError(
        #                   "Attribute error",
        #                   compute.token_start,
        #                   compute.token_end,
        #                   TOKENTYPE.ERROR,
        #               )
        #               raise e
        #           if isinstance(value, int) or isinstance(value, float):
        #               return True, {"type": TOKENTYPE.NUMBER, "value": value}
        #           elif isinstance(value, str):
        #               return True, {"type": TOKENTYPE.STRING, "value": value}
        #           else:
        #               compute.setTokenError(
        #                   "Attribute parse error, must be int, float or string",
        #                   compute.token_start,
        #                   compute.token_end,
        #                   TOKENTYPE.ERROR,
        #               )
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
