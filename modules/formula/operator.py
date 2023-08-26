from .token import TOKENTYPE


def operation(compute, token, stack):
    # 2項演算子 ['**', '*', '/', '%', '+', '-', '<<', '>>', '>', '<', '>=', '<=', '==', '!=', '&', '^', '|', '&&', '||']
    if token['value'] in ['**', '*', '/', '%', '+', '-', '<<', '>>', '>', '<', '>=', '<=', '==', '!=', '&', '^', '|', '&&', '||']:
        right = stack.pop()['value']
        left = stack.pop()['value']
        if token['value'] == '+':
            # string + string
            if type(left) == str or type(right) == str:
                stack.append({'type': TOKENTYPE.STRING, 'value': str(left) + str(right)})
            else:
                stack.append({'type': TOKENTYPE.NUMBER, 'value': left + right})
        elif token['value'] == '-':
            # string is error
            if type(left) == str or type(right) == str:
                compute.setTokenError('String is not suport minus', compute.token_start, compute.token_end, TOKENTYPE.ERROR)
                return False
            stack.append({'type': TOKENTYPE.NUMBER, 'value': left - right})
        elif token['value'] == '*':
            # string * number
            if type(left) == str and type(right) == int:
                stack.append({'type': TOKENTYPE.STRING, 'value': left * right})
            elif type(left) == str or type(right) == str:
                compute.setTokenError('String is not suport multiply', compute.token_start, compute.token_end, TOKENTYPE.ERROR)
                return False
            stack.append({'type': TOKENTYPE.NUMBER, 'value': left * right})
        elif token['value'] == '/':
            if type(left) == str or type(right) == str:
                compute.setTokenError('String is not suport divide', compute.token_start, compute.token_end, TOKENTYPE.ERROR)
                return False
            stack.append({'type': TOKENTYPE.NUMBER, 'value': left / right})
        elif token['value'] == '%':
            if type(left) == str or type(right) == str:
                compute.setTokenError('String is not suport modulo', compute.token_start, compute.token_end, TOKENTYPE.ERROR)
                return False
            stack.append({'type': TOKENTYPE.NUMBER, 'value': left % right})
        elif token['value'] == '**':
            if type(left) == str or type(right) == str:
                compute.setTokenError('String is not suport power', compute.token_start, compute.token_end, TOKENTYPE.ERROR)
                return False
            stack.append({'type': TOKENTYPE.NUMBER, 'value': left ** right})
        elif token['value'] == '>':
            stack.append(compute.booleanToNumber(left > right))
        elif token['value'] == '<':
            stack.append(compute.booleanToNumber(left < right))
        elif token['value'] == '>=':
            stack.append(compute.booleanToNumber(left >= right))
        elif token['value'] == '<=':
            stack.append(compute.booleanToNumber(left <= right))
        elif token['value'] == '==':
            stack.append(compute.booleanToNumber(left == right))
        elif token['value'] == '!=':
            stack.append(compute.booleanToNumber(left != right))
        elif token['value'] == '&&':
            stack.append(compute.booleanToNumber(left and right))
        elif token['value'] == '||':
            stack.append(compute.booleanToNumber(left or right))
        else:
            compute.setTokenError('Unknown operator ' + token['value'], compute.token_start, compute.token_end, TOKENTYPE.ERROR)
            return False
