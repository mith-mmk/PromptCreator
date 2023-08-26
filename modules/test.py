from formula import FormulaCompute

if __name__ == "__main__":
    import os
    args = os.sys.argv
    if len(args) > 1:
        formula = args[1]
        compute = FormulaCompute(formula, variables={}, debug=True)
        res = compute.getCompute()
        if res is None:
            error = compute.getError()
            print(error)
        else:
            print(res)
        exit()

    formulas = [
        {'f': 'if("aa" == aa, "true", "false")', 'var': {'aa': ["sd", "aa"]}, 'result': 'false'},
        {'f': 'if("aa" == aa,2, "true", "false")', 'var': {'aa': ["sd", "aa"]}, 'result': 'true'},
        {'f': 'if("aa,1" == aa,2, "true", "false")', 'var': {'aa': ["sd", "aa"]}, 'result': 'false'},
        {'f': 'if("aa,1" != aa,2, "true", "false")', 'var': {'aa': ["sd", "aa"]}, 'result': 'true'},
        {'f': '2 * 3 + 2', 'var': {}, 'result': 8},
        {'f': '2 + 3 * 2', 'var': {}, 'result': 8},
        {'f': '(2 + 3) * 2', 'var': {}, 'result': 10},
        {'f': '2 + 3 * 2 + 1', 'var': {}, 'result': 9},
        {'f': '2 + 3 * (2 + 1)', 'var': {}, 'result': 11},
        {'f': '2 - 3', 'var': {}, 'result': -1},
        {'f': '2 - 3 - 1', 'var': {}, 'result': -2},
        {'f': '- 2 + 3', 'var': {}, 'result': 1},
        {'f': 'int(- 2 + 3 / -1)', 'var': {}, 'result': -5},
        {'f': '"abc" + "bcd"', 'var': {}, 'result': 'abcbcd'},
        {'f': 'int("12") + "bcd"', 'var': {}, 'result': '12bcd'},
        {'f': 'int("12") + int("24")', 'var': {}, 'result': 36},
        {'f': 'aa[2] + "bcd"', 'var': {'aa': [4, 5]}, 'result': '5bcd'},
        {'f': 'aa[2] + aa[1]', 'var': {'aa': [4, 5]}, 'result': 9},
    ]

    for formula in formulas:
        compute = FormulaCompute(formula['f'], variables=formula["var"])
        res = compute.getCompute()
        print(f'formula: {formula["f"]}, var: {formula["var"]}')
        if res is None:
            error = compute.getError()
            print(error)
        else:
            print('result', res, formula['result'])
            if res != formula['result']:
                assert False
