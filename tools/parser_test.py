# commandline
import os

from modules.formula import FormulaCompute
from modules.logger import getDefaultLogger

Logger = getDefaultLogger()
Logger.setPrintModes(["debug", "info", "warning", "error", "critical", "verbose"])

args = os.sys.argv
if len(args) > 1:
    formula = args[1]
    variables = {}
    if len(args) > 2:
        vals = args[2]  # width=100, height=200, name="test, weight=0.1"
        vals = vals.split(",")
        for val in vals:
            val = val.split("=")
            if len(val) == 2:
                key = val[0].strip()
                value = val[1].strip()
                # float ?
                if value.replace(".", "").isdigit():
                    value = float(value)
                # int ?
                elif value.isdigit():
                    value = int(value)
                print(f"Key: {key}, Value: {value}")
                if "." in key:
                    print(key)
                    key, subkey = key.split(".")
                    if key in variables:
                        if isinstance(variables[key], dict):
                            variables[key][subkey] = value
                        else:
                            variables[key] = {subkey: value}
                    else:
                        variables[key] = {subkey: value}
                    continue

                if key in variables:
                    # key width.xl=1280 => width = {xl: 1280}

                    if isinstance(variables[key], list):
                        variables[key].append(value)
                    else:
                        variables[key] = [variables[key], value]
                else:
                    variables[key] = value
    print(f"Formula: {formula}")
    print(f"Variables: {variables}")
    compute = FormulaCompute(formula, variables=variables, debug=True)
    res = compute.getCompute()
    if res is None:
        error = compute.getError()
        print(error)
    else:
        print(res)
    exit()


def test():
    formulas = [
        {
            "f": 'if("aa" == aa, "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "false",
        },
        {
            "f": 'if("aa" == aa,2, "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "true",
        },
        {
            "f": 'if("aa,1" == aa,2, "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "false",
        },
        {
            "f": 'if("aa,1" != aa,2, "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "true",
        },
        {"f": "2 * 3 + 2", "var": {}, "result": 8},
        {"f": "2 + 3 * 2", "var": {}, "result": 8},
        {"f": "(2 + 3) * 2", "var": {}, "result": 10},
        {"f": "2 + 3 * 2 + 1", "var": {}, "result": 9},
        {"f": "2 + 3 * (2 + 1)", "var": {}, "result": 11},
        {"f": "2 - 3", "var": {}, "result": -1},
        {"f": "2 - 3 - 1", "var": {}, "result": -2},
        {"f": "- 2 + 3", "var": {}, "result": 1},
        {"f": "int(- 2 + 3 / -1)", "var": {}, "result": -5},
        {"f": '"abc" + "bcd"', "var": {}, "result": "abcbcd"},
        {"f": 'int("12") + "bcd"', "var": {}, "result": "12bcd"},
        {"f": 'int("12") + int("24")', "var": {}, "result": 36},
        {"f": 'aa[2] + "bcd"', "var": {"aa": [4, 5]}, "result": "5bcd"},
        {"f": "aa[2] + aa[1]", "var": {"aa": [4, 5]}, "result": 9},
        {"f": '"aa\\"" == "aa\\""', "var": {"aa": [4, 5]}, "result": 1},
        {"f": '"aa\\"" == \'aa"\'', "var": {"aa": [4, 5]}, "result": 1},
    ]

    for formula in formulas:
        compute = FormulaCompute(formula["f"], variables=formula["var"])
        assert compute.getCompute() == formula["result"]
