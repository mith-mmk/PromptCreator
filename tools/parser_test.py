# commandline
import argparse
import sys

from modules.formula import FormulaCompute
from modules.logger import getDefaultLogger

parser = argparse.ArgumentParser(description="Formula Parser")
parser.add_argument(
    "formula",
    type=str,
    help="Formula to parse",
    default=None,
)


parser.add_argument(
    "--variables",
    type=str,
    help="Variables to use in the formula",
    default=None,
)


parser.add_argument(
    "--version",
    type=int,
    help="Version of the parser",
    default=2.0,
)

parser.add_argument(
    "--debug",
    type=bool,
    help="Debug mode",
    default=False,
    const=True,
    nargs="?",
)


args = parser.parse_args()


def test():
    formulas = [
        {
            "f": 'if("aa" == aa[1], "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "false",
        },
        {
            "f": 'if("aa" == aa[2], "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "true",
        },
        {
            "f": 'if("aa" != aa[2], "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "false",
        },
        {
            "f": 'if("aa" != aa[2], "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "false",
        },
        {
            "f": 'if("aa" != aa[1], "true", "false")',
            "var": {"aa": ["sd", "aa"]},
            "result": "true",
        },
        {"f": "2 * 3 + 2", "var": {"aa": ["sd"]}, "result": 8},
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
        {"f": "random_float()", "var": {"aa": [4, 5]}, "result": None},  # 0.0. - 1.
        {"f": "contains(aa, 'abc')", "var": {"aa": ["abcde", "ddddd"]}, "result": 1},
        {"f": "contains(aa[2], 'abc')", "var": {"aa": ["abcde", "ddddd"]}, "result": 0},
        {
            "f": 'aa["c"]',
            "var": {"aa": ["abcde", "ddddd"]},
            "attr": {"aa": {"c": "xyx"}},
            "result": "xyx",
        },
        {
            "f": 'aa["d"]',
            "var": {"aa": ["abcde", "ddddd"]},
            "attr": {"aa": {"c": "xyx", "d": "xyz"}},
            "result": "xyz",
        },
        {
            "f": 'if(aa["d"]=="xyz", aa[1], aa[2])',
            "var": {"aa": ["abcde", "ddddd"]},
            "attr": {"aa": {"c": "xyx", "d": "xyz"}},
            "result": "abcde",
        },
        {
            "f": 'if(aa["d"]!="xyz", aa[1], aa[2])',
            "var": {"aa": ["abcde", "ddddd"]},
            "attr": {"aa": {"c": "xyx", "d": "xyz"}},
            "result": "ddddd",
        },
        {
            "f": "if(contains(aa[1], 'abc'), 'true', 'false')",
            "var": {"aa": ["abcde", "ddddd"]},
            "result": "true",
        },
        {
            "f": "contains(aa, 'aac', 'aab', 'cde')",
            "var": {"aa": ["abcde", "ddddd"]},
            "result": 1,
        },
        {
            "f": "contains(aa, 'aac', 'aab', 'cdf')",
            "var": {"aa": ["abcde", "ddddd"]},
            "result": 0,
        },
        {
            "f": "if(contains(aa[1], 'abd'), 'true', if(contains(aa[2], 'ddd'), 'true', 'false')",
            "var": {"aa": ["abcde", "ddddd"]},
            "result": "true",
        },
        {
            "f": "if(contains(aa[1], 'abd'), 'true', if(contains(aa[1], 'ddd'), 'true', 'false')",
            "var": {"aa": ["abcde", "ddddd"]},
            "result": "false",
        },
    ]

    for formula in formulas:
        print(f"Formula: {formula['f']}")
        if "attr" in formula:
            attributes = formula["attr"]
        else:
            attributes = {}
        compute = FormulaCompute(
            formula["f"],
            variables=formula["var"],
            attributes=attributes,
            # debug=True,
            version=2,
        )

        if formula["result"] is not None:
            result = compute.getCompute()
            print(f"Result: {result}")
            assert result == formula["result"]
            print(f"Ok: {formula['result']}")
        else:
            res = compute.getCompute()
            print(f"Result: {res}")


Logger = getDefaultLogger()
Logger.setPrintModes(["debug", "info", "warning", "error", "critical", "verbose"])

args = parser.parse_args()
if args.formula is not None:
    formula = args.formula
    variables = {}
    attributes = {}
    if args.variables is not None:
        vals = args.variables  # width=100, height=200, name="test, weight=0.1"
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
                    if key in attributes:
                        attributes[key][subkey] = value
                    else:
                        attributes[key] = {subkey: value}
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
    print(f"attributes: {attributes}")
    version = args.version

    compute = FormulaCompute(
        formula,
        variables=variables,
        attributes=attributes,
        debug=args.debug,
        version=version,
    )
    res = compute.getCompute()
    if res is None:
        error = compute.getError()
        print(error)
    else:
        print(res)
    exit()
else:
    print("run test")
    test()
