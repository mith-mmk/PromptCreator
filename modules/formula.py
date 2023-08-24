import re
import random
import time


# debug_print
def debug_print(*args):
    if __name__ == "__main__":
        print(*args)


class TOKENTYPE():
    NONE = 0
    NUMBER = 1
    VARIABLE = 2
    OPERATOR = 3
    BRACKET = 4
    FUNCTION = 5
    COMMA = 6
    SPACE = 7
    STRING = 8
    OTHER = 9
    END = 10
    ERROR = 11


def formula(formula, variables={}):
    compute = FormulaCompute(formula, variables)
    if compute.compute():
        return compute.getCompute()
    else:
        return None


class FormulaCompute():
    def __init__(self, formula='', variables={}):
        self.formula = formula
        self.variables = variables
        self.reslut = None

    def setFormula(self, formula):
        self.formula = formula
        self.reslut = None

    def setVariables(self, variables):
        self.variables = variables
        self.result = None

    def getCompute(self, formula=None, variables={}):
        if formula is None:
            self.compute()
            return self.result
        self.formula = formula
        self.variables = variables
        self.compute()
        return self.result
    
    def getError(self):
        return self.token_error_message
        
    def compute(self):
        self.result = None
        if not self.token():
            debug_print('token error', self.token_error_message)
            return False
        if not self.parse():
            debug_print('parse error', self.token_error_message)
            return False
        try:
            if not self.reverce_polish_notation():
                return False
        except Exception as e:
            debug_print(e)
            self.setTokenError('Unknown error', self.token_start, self.token_end, TOKENTYPE.ERROR)
            return False
        return True
    
    def setTokenError(self, message, start, end, type):
        self.token_error_message = message
        self.token_error_start = start
        self.token_error_end = end
        self.token_error_type = type
    
    def parse(self):
        for i, token in enumerate(self.tokens):
            # variable -> number or string
            if token['type'] == TOKENTYPE.VARIABLE:
                if ',' in token['value']:
                    var, num = token['value'].split(',')
                    num = int(num) - 1
                else:
                    var = token['value']
                    num = 0
                if var in self.variables:
                    if type(self.variables[var]) == int or type(self.variables[var]) == float:
                        self.tokens[i]['type'] = TOKENTYPE.NUMBER
                    elif type(self.variables[var]) == str:
                        self.tokens[i]['type'] = TOKENTYPE.STRING
                    else:
                        self.setTokenError('Unknown variable type', self.token_start, self.token_end, TOKENTYPE.ERROR)
                    values = self.variables[var]

                    if type(values) == list:
                        value = values[num]
                    else:
                        value = values
                    self.tokens[i]['value'] = value
                else:
                    self.setTokenError('Unknown variable', self.token_start, self.token_end, TOKENTYPE.ERROR)
                    debug_print('Unknown variable', var)
                    return False
            # number
            elif token['type'] == TOKENTYPE.NUMBER:
                # int or float
                try:
                    if '.' in token['value']:
                        self.tokens[i]['value'] = float(token['value'])
                    else:
                        self.tokens[i]['value'] = int(token['value'])
                except ValueError:
                    self.setTokenError('Unknown number', self.token_start, self.token_end, TOKENTYPE.ERROR)
                    debug_print('Unknown number', token['value'])
                    return False
                
            # string
            elif token['type'] == TOKENTYPE.STRING:
                pass
            # function
            elif token['type'] == TOKENTYPE.FUNCTION:
                pass
            elif token['type'] == TOKENTYPE.OPERATOR:
                pass
            elif token['type'] == TOKENTYPE.BRACKET:
                pass
            elif token['type'] == TOKENTYPE.COMMA:
                pass
            elif token['type'] == TOKENTYPE.SPACE:
                pass
            elif token['type'] == TOKENTYPE.OTHER:
                debug_print('Unknown token', token['value'])
                self.setTokenError('Unknown token', self.token_start, self.token_end, TOKENTYPE.ERROR)
                return False
            elif token['type'] == TOKENTYPE.END:
                break
            else:
                value = token['value']
                debug_print(f'Illegal syntax {value}')
                self.setTokenError(f'Illegal syntax {value}', self.token_start, self.token_end, TOKENTYPE.ERROR)

                return False

        debug_print(self.tokens)
        return True
    
    def reverce_polish_notation(self):
        # expression := <fomula> + <fomula> |
        #               <fomula> - <fomula> |
        # term       := <fomula> * <fomula>
        #               <fomula> / <fomula> |
        #               <fomula> % <fomula>
        # factor    :=  <fomula> ^ <fomula>
        # compare   :=  <fomula> > <fomula>
        #               <fomula> < <fomula>
        #               <fomula> >= <fomula>
        #               <fomula> <= <fomula>
        #               <fomula> == <fomula>
        #               <fomula> != <fomula>
        # function     <function>(<fomula> , <fomula>,...)
        # number       <number>
        # variable     <variable>
        # string       <string>
        # bracket      (<fomula>)
        # fomula       <expression> | <term> | <factor> | <compare> | <function> | <number> | <variable> | <string> | <bracket>

        # 逆ポーランド記法に変換
        # 1. 数字はそのまま出力
        # 2. 演算子はスタックに積む
        # 3. 関数はスタックに積む
        # 4. カンマはスタックのトップからカンマまでの演算子を出力
        # 5. カッコはスタックのトップからカッコまでの演算子を出力
        # 6. スタックの残りを出力
        # 7. スタックが空になるまで繰り返す
        # 8. 逆ポーランド記法を計算する
        # 9. 計算結果を返す
        # 10. エラーがあればFalseを返す

        # 1 + 1 -> 1 1 +
        # "str" + "str" -> "str" "str" +
        # 1 + 1 * 2 -> 1 1 2 * +
        # 1 + 1 * 2 + 3 -> 1 1 2 * + 3 +
        # 1 + 1 * 2 + 3 * 4 -> 1 1 2 * + 3 4 * +
        # (1 + 1) * 2 + 3 * 4 + 5 -> 1 1 + 2 * 3 4 * + 5 +
        # fuction(1 + 1 , 2 + 1) -> 1 1 + 2 1 + function
        # fuction(1 + 1 , 2 + 1) + 1 -> 1 1 + 2 1 + function 1 +

        reversed_polish_notation = []
        stack = []
        debug_print(self.tokens)
        for token in self.tokens:
            debug_print(token)
            if token['type'] == TOKENTYPE.NUMBER or token['type'] == TOKENTYPE.STRING or token['type'] == TOKENTYPE.VARIABLE:
                reversed_polish_notation.append(token)
            elif token['type'] == TOKENTYPE.FUNCTION:
                debug_print(token['value'])
                stack.append(token)
            elif token['type'] == TOKENTYPE.COMMA:
                debug_print(stack)
                while len(stack) > 0:
                    if stack[-1]['type'] == TOKENTYPE.BRACKET:
                        break
                    reversed_polish_notation.append(stack.pop())
            elif token['type'] == TOKENTYPE.BRACKET:
                if token['value'] == '(':
                    stack.append(token)
                else:
                    while len(stack) > 0:
                        if stack[-1]['type'] == TOKENTYPE.BRACKET:
                            stack.pop()
                            break
                        reversed_polish_notation.append(stack.pop())
            elif token['type'] == TOKENTYPE.OPERATOR:
                while len(stack) > 0:
                    if stack[-1]['type'] == TOKENTYPE.BRACKET:
                        break
                    reversed_polish_notation.append(stack.pop())
                stack.append(token)
            elif token['type'] == TOKENTYPE.SPACE:
                pass
            elif token['type'] == TOKENTYPE.OTHER:
                self.setTokenError('Unknown token', self.token_start, self.token_end, TOKENTYPE.ERROR)
                return False
            elif token['type'] == TOKENTYPE.END:
                pass
        stack.reverse()
        debug_print(stack)
        for token in stack:
            reversed_polish_notation.append(token)
        # 逆ポーランド記法を計算する
        for token in reversed_polish_notation:
            match token['type']:
                case TOKENTYPE.NUMBER:
                    stack.append(token['value'])
                case TOKENTYPE.STRING:
                    stack.append(token['value'])
                case TOKENTYPE.VARIABLE:
                    stack.append(token['value'])
                case TOKENTYPE.FUNCTION:
                    function = token['value']
                    match function:
                        case 'pow':
                            right = stack.pop()
                            left = stack.pop()
                            # どちらかが文字列ならエラー
                            if type(left) == str or type(right) == str:
                                self.setTokenError('String is not suport power', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            stack.append(left ** right)
                        case 'int':
                            value = stack.pop()
                            stack.append(int(value))
                        case 'float':
                            value = stack.pop()
                            stack.append(float(value))
                        case 'str':
                            value = stack.pop()
                            stack.append(str(value))
                        case 'len':
                            value = stack.pop()
                            stack.append(len(value))
                        case 'max':
                            right = stack.pop()
                            left = stack.pop()
                            stack.append(max(right, left))
                        case 'min':
                            right = stack.pop()
                            left = stack.pop()
                            stack.append(min(right, left))
                        case 'replace':  # replace(string, old, new)
                            new = stack.pop()
                            old = stack.pop()
                            string = stack.pop()
                            stack.append(string.replace(old, new))
                        case 'split':  # split(string, separator)
                            separator = stack.pop()
                            string = stack.pop()
                            stack.append(string.split(separator))
                        case 'upper':  # upper(string)
                            string = stack.pop()
                            stack.append(string.upper())
                        case 'lower':  # lower(string)
                            string = stack.pop()
                            stack.append(string.lower())
                        case 'if':  # if(condition, true, false)
                            false = stack.pop()
                            true = stack.pop()
                            condition = stack.pop()
                            if condition == 1:
                                stack.append(true)
                            else:
                                stack.append(false)
                        case 'not':  # not(condition)
                            condition = stack.pop()
                            if condition == 1:
                                stack.append(0)
                            else:
                                stack.append(1)
                        case 'and':  # and(condition, condition)
                            right = stack.pop()
                            left = stack.pop()
                            if right == 1 and left == 1:
                                stack.append(1)
                            else:
                                stack.append(0)
                        case 'or':  # or(condition, condition)
                            right = stack.pop()
                            left = stack.pop()
                            if right == 1 or left == 1:
                                stack.append(1)
                            else:
                                stack.append(0)
                        case 'match':  # match(string, pattern)
                            pattern = stack.pop()
                            string = stack.pop()
                            if re.match(pattern, string):
                                stack.append(1)
                            else:
                                stack.append(0)
                        case 'substring':  # substring(string, start, end)
                            end = stack.pop()
                            start = stack.pop()
                            string = stack.pop()
                            stack.append(string[start:end])
                        case 'random':  # random(start, end)
                            end = stack.pop()
                            start = stack.pop()
                            if start > end:
                                self.setTokenError('Random error start > end', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            try:
                                if type(start) == float or type(end) == float:
                                    stack.append(random.uniform(start, end))
                                else:
                                    stack.append(random.randint(start, end))
                            except ValueError:
                                self.setTokenError('Random error must number', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                        case 'random_int':  # randomint(0, 2^64 -1)
                            try:
                                stack.append(random.randint(0, 2**64 - 1))
                            except ValueError:
                                self.setTokenError('Random error', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                        case 'random_float':  # randomfloat(0, 1)
                            try:
                                stack.append(random.random())
                            except ValueError:
                                self.setTokenError('Random error', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                        case 'random_string':  # randomstring(length)
                            length = stack.pop()
                            stack.append(''.join([random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for i in range(length)]))
                        case 'uuid':  # uuid()
                            import uuid
                            stack.append(str(uuid.uuid4()))
                        case 'time':  # time() as hh:mm:ss
                            stack.append(time.strftime('%H:%M:%S'))
                        case 'date':  # date() as yyyy-mm-dd
                            stack.append(time.strftime('%Y-%m-%d'))
                        case 'datetime':  # datetime() as yyyy-mm-dd hh:mm:ss
                            stack.append(time.strftime('%Y-%m-%d %H:%M:%S'))
                        case 'timestamp':  # timestamp() as yyyy-mm-dd hh:mm:ss
                            stack.append(time.strftime('%Y-%m-%d %H:%M:%S'))
                        case 'year':  # year() as yyyy
                            stack.append(time.strftime('%Y'))
                        case 'month':  # month() as mm
                            stack.append(time.strftime('%m'))
                        case 'day':  # day() as dd
                            stack.append(time.strftime('%d'))
                        case 'hour':  # hour() as hh
                            stack.append(time.strftime('%H'))
                        case 'minute':  # minute() as mm
                            stack.append(time.strftime('%M'))
                        case 'second':  # second() as ss
                            stack.append(time.strftime('%S'))
                        case 'weekday':  # weekday() as 0-6
                            stack.append(time.strftime('%w'))
                        case 'week':  # week() as 0-53
                            stack.append(time.strftime('%U'))
                        case _:
                            self.setTokenError('Unknown function', self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False
                case TOKENTYPE.OPERATOR:
                    right = stack.pop()
                    left = stack.pop()
                    if token['value'] == '+':
                        # string + string
                        if type(left) == str or type(right) == str:
                            stack.append(str(left) + str(right))
                        else:
                            stack.append(left + right)
                    elif token['value'] == '-':
                        # string is error
                        if type(left) == str or type(right) == str:
                            self.setTokenError('String is not suport minus', self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False
                        stack.append(left - right)
                    elif token['value'] == '*':
                        # string * number
                        if type(left) == str and type(right) == int:
                            stack.append(left * right)
                        elif type(left) == str or type(right) == str:
                            self.setTokenError('String is not suport multiply', self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False
                        stack.append(left * right)
                    elif token['value'] == '/':
                        if type(left) == str or type(right) == str:
                            self.setTokenError('String is not suport divide', self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False
                        stack.append(left / right)
                    elif token['value'] == '%':
                        if type(left) == str or type(right) == str:
                            self.setTokenError('String is not suport modulo', self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False
                        stack.append(left % right)
                    elif token['value'] == '^':
                        if type(left) == str or type(right) == str:
                            self.setTokenError('String is not suport power', self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False
                        stack.append(left ** right)
                    elif token['value'] == '>':
                        result = left > right
                        if result:
                            stack.append(1)
                        else:
                            stack.append(0)
                    elif token['value'] == '<':
                        result = left < right
                        if result:
                            stack.append(1)
                        else:
                            stack.append(0)
                    elif token['value'] == '>=':
                        result = left >= right
                        if result:
                            stack.append(1)
                        else:
                            stack.append(0)
                    elif token['value'] == '<=':
                        result = left <= right
                        if result:
                            stack.append(1)
                        else:
                            stack.append(0)
                    elif token['value'] == '==':
                        result = left == right
                        if result:
                            stack.append(1)
                        else:
                            stack.append(0)
                    elif token['value'] == '!=':
                        result = left != right
                        if result:
                            stack.append(1)
                        else:
                            stack.append(0)
                    else:
                        self.setTokenError('Unknown operator', self.token_start, self.token_end, TOKENTYPE.ERROR)
                        return False

        self.result = stack.pop()
        return True

    def token(self):
        self.tokens = []
        self.token = ''
        self.token_type = TOKENTYPE.NONE
        self.token_start = 0
        self.token_end = 0
        self.token_error = False
        self.token_error_message = ''
        self.token_error_start = 0
        self.token_error_end = 0
        self.token_error_type = 0
        self.token_error_message = ''
        self.token_error_start = 0
        self.token_error_end = 0
        self.token_error_type = 0
        self.token_error_message = ''
        count = 0
        typeSpace = re.compile(r'^\s+')
        typeNumber = re.compile(r'^[0-9]+(\.[0-9]+)?')
        typeVariable1 = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*')
        typeVariable2 = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*\:[a-zA-Z_][a-zA-Z0-9_]*')
        # abc,1
        typeVariable3 = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*\,[0-9]+')

        typeOperator = re.compile(r'^(\+|-|\*|/|%|\^|>|<|>=|<=|==|!=)')
        typeBracket = re.compile(r'^(\(|\))')
        typeFunction = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(')
        typeComma = re.compile(r'^,')
        # " \" "
        typeString = re.compile(r'^("[^"]*"|\'[^\']*\')')
        typeEnd = re.compile(r'^$')

        count = 0
        while count < len(self.formula):
            current = self.formula[count:]
            if typeSpace.match(current):
                self.token_type = TOKENTYPE.SPACE
                self.token_start = count
                self.token_end = count + len(typeSpace.match(current).group(0))
                count += len(typeSpace.match(current).group(0))
            elif typeFunction.match(current):
                self.token_type = TOKENTYPE.FUNCTION
                self.token_start = count
                self.token_end = count + len(typeFunction.match(current).group(0))
                function = typeFunction.match(current).group(0)
                debug_print(function)
                function = function.replace(' ', '', 1)
                function = function[:-1]
                self.tokens.append({'type': TOKENTYPE.FUNCTION, 'value': function})
                count += len(typeFunction.match(current).group(0)) - 1
            elif typeNumber.match(current):
                self.token_type = TOKENTYPE.NUMBER
                self.token_start = count
                self.token_end = count + len(typeNumber.match(current).group(0))
                self.tokens.append({'type': TOKENTYPE.NUMBER, 'value': typeNumber.match(current).group(0)})
                count += len(typeNumber.match(current).group(0))
            elif typeVariable3.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable3.match(current).group(0))
                self.tokens.append({'type': TOKENTYPE.VARIABLE, 'value': typeVariable3.match(current).group(0)})
                count += len(typeVariable3.match(current).group(0))
            elif typeVariable2.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable2.match(current).group(0))
                self.tokens.append({'type': TOKENTYPE.VARIABLE, 'value': typeVariable2.match(current).group(0)})
                count += len(typeVariable2.match(current).group(0))
            elif typeVariable1.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable1.match(current).group(0))
                self.tokens.append({'type': TOKENTYPE.VARIABLE, 'value': typeVariable1.match(current).group(0)})
                count += len(typeVariable1.match(current).group(0))
            elif typeOperator.match(current):
                self.token_type = TOKENTYPE.OPERATOR
                self.token_start = count
                self.token_end = count + len(typeOperator.match(current).group(0))
                self.tokens.append({'type': TOKENTYPE.OPERATOR, 'value': typeOperator.match(current).group(0)})
                count += len(typeOperator.match(current).group(0))
            elif typeBracket.match(current):
                self.token_type = TOKENTYPE.BRACKET
                self.token_start = count
                self.token_end = count + len(typeBracket.match(current).group(0))
                self.tokens.append({'type': TOKENTYPE.BRACKET, 'value': typeBracket.match(current).group(0)})
                count += len(typeBracket.match(current).group(0))
            elif typeComma.match(current):
                self.token_type = TOKENTYPE.COMMA
                self.token_start = count
                self.token_end = count + len(typeComma.match(current).group(0))
                self.tokens.append({'type': TOKENTYPE.COMMA, 'value': typeComma.match(current).group(0)})
                count += len(typeComma.match(current).group(0))
            elif typeString.match(current):
                self.token_type = TOKENTYPE.STRING
                self.token_start = count
                self.token_end = count + len(typeString.match(current).group(0))
                string = typeString.match(current).group(0)
                # remove start and end "
                string = string[1:-1]
                self.tokens.append({'type': TOKENTYPE.STRING, 'value': string})
                count += len(typeString.match(current).group(0))
            elif typeEnd.match(current):
                self.token_type = TOKENTYPE.END
                self.token_start = count
                self.token_end = count
                self.tokens.append({'type': TOKENTYPE.END, 'value': ''})
                count += 1
            else:
                self.setTokenError(f'Syntax error {current}', self.token_start, self.token_end, TOKENTYPE.ERROR)
                return False
        self.token_type = TOKENTYPE.END
        self.token_start = count
        self.token_end = count
        self.tokens.append({'type': TOKENTYPE.END, 'value': ''})
        return True


# test
if __name__ == "__main__":
    import os
    import json
    args = os.sys.argv
    if len(args) < 2:
        f = 'if(1 + 1 == 2, "true", "false")'
    else:
        f = args[1]
    if len(args) < 3:
        variables = {'aa': ["sd"]}
    else:
        variables = json.loads(args[2])
    compute = FormulaCompute(f, variables)
    debug_print(compute.getCompute())
