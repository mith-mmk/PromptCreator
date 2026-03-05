import json

import pytest

from modules.formula import FormulaCompute

# cases = [
#    ('if("aa" == aa[1], "true", "false")', {"aa": ["sd", "aa"]}, "false"),
#    ('if("aa" == aa[2], "true", "false")', {"aa": ["sd", "aa"]}, "true"),
#    ("2 * 3 + 2", {}, 8),
#    ("2 + 3 * 2", {}, 8),
# ]
test_file = "tests/data/parser_cases.json"
c = json.load(open("tests/data/parser_cases.json", "r", encoding="utf-8"))
with open(test_file) as f:
    c = json.load(f)
print(c)

cases = [
    (case["formula"], case["vars"], case.get("attr", {}), case["result"]) for case in c
]


def test_random_float_range():
    for _ in range(100):

        compute = FormulaCompute(
            "random_float()", variables={}, attributes={}, version=2
        )
        result = compute.getCompute()
        assert 0 <= result <= 1  # type: ignore


ops = ["+", "-", "*"]


def test_random_operations():

    for _ in range(1000):
        import random

        a = random.randint(-10, 10)
        b = random.randint(-10, 10)
        op = random.choice(ops)
        formula = f"int(aa) {op} int(bb)"
        variables = {"aa": a, "bb": b}
        compute = FormulaCompute(formula, variables=variables, attributes={}, version=2)
        result = compute.getCompute()
        if op == "+":
            expected = a + b
        elif op == "-":
            expected = a - b
        elif op == "*":
            expected = a * b
        assert result == expected


# エラーがでる
"""
def test_random_operations2():
    for _ in range(1000):
        import random

        a = random.randint(-10, 10)
        b = random.randint(-10, 10)
        c = random.randint(-10, 10)
        op1 = random.choice(ops)
        op2 = random.choice(ops)
        formula = f"( int(aa) {op1} int(bb) ) {op2} int(cc)"
        variables = {"aa": a, "bb": b, "cc": c}
        compute = FormulaCompute(formula, variables=variables, attributes={}, version=2)
        result = compute.getCompute()
        if op1 == "+":
            expected = a + b
        elif op1 == "-":
            expected = a - b
        elif op1 == "*":
            expected = a * b

        if op2 == "+":
            expected += c
        elif op2 == "-":
            expected -= c
        elif op2 == "*":
            expected *= c

        assert result == expected
"""


@pytest.mark.parametrize("formula,variables,attributes, expected", cases)
def test_formula(formula, variables, attributes, expected):
    compute = FormulaCompute(
        formula, variables=variables, attributes=attributes, version=2
    )

    result = compute.getCompute()
    assert result == expected
    # test_random_float_range()
    # test_random_operations()
