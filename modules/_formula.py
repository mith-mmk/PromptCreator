import re
import random
import time


# 仕様 {= <formula> } の内部を計算する
# 変数は外部変数のみ
#   appendsで指定した場合、現在の参照値を返す
# 関数は内部関数のみ
# 変数の仕様
#  変数名は$もしくは英文字と_で始まり、英数字と_-$で構成される
#  大文字と小文字は区別される
#  aaaa,1 は配列の1番目 aaaa,2 は配列の2番目 aaaa,3 は配列の3番目 ... 1番目は1から始まる
#  aaaa は 配列の場合 aaaa,1 と同じ
#  aaaa[1] は aaaa,1 と同じ []内は数値のみ（式は未実装）
#  info:name は--infoで指定可能な変数 配列は未実装
#  $SYSTEMはシステム変数
# TODO! コードが長いのでmodule化してファイル分割


# debug_print
def debug_print(*args, mode=None):
    if __name__ == "__main__":
        if mode == 'value':
            text = ''
            for arg in args:
                if type(arg) == dict:
                    text += f'{arg["value"]} '
                elif type(arg) == list:
                    for i in arg:
                        if type(i) == dict:
                            text += f'{i["value"]} '
                        else:
                            text += f'{i} '
                else:
                    text += f'{arg} '
            print(text)
        else:
            print(*args)


class TOKENTYPE():
    NONE = 0
    NUMBER = 1
    VARIABLE = 2
    OPERATOR = 3
    EXPRESSION = 4
    TERM = 5
    FACTOR = 6
    AND = 7
    OR = 8
    COMPARE = 9
    BRACKET = 10
    FUNCTION = 11
    COMMA = 12
    SPACE = 13
    STRING = 14
    OTHER = 15
    END = 100
    ERROR = 99


operator_order = {
    # block literal
    # 1: {}  := { <fomula> } (TOKEN.BLOCK) # ブロック # 実装しない
    # 2: ()  := ( <fomula> ) (TOKEN.BRACKET)
    # 2: []  := <variable> [ <fomula> ] (TOKEN.BRACKET) # 配列
    # 2: .   := <variable>.<variable> (TOKEN.POINT) # オブジェクト # 実装しない
    # 2: <function> := <function>(<fomula> , <fomula>,...) (TOKEN.FUNCTION)
    # 単項演算子
    # 3: ++  := ++<variable> (TOKEN.OPERATOR)
    # 3: --  := --<variable> (TOKEN.OPERATOR)
    # 4: !   := !<variable> (TOKEN.OPERATOR)
    # 4: ~   := ~<variable> (TOKEN.OPERATOR)
    'PLUS': 4,   # := + <variable> (TOKEN.OPERATOR) # 個別実装
    'MINUS': 4,  # := - <variable> (TOKEN.OPERATOR) # 何もしない
    # 2項演算子 2
    '**': 5,   # べき乗
    '*': 6,    # 乗算
    '/': 6,    # 除算
    '%': 6,    # 剰余
    '+': 7,    # 加算
    '-': 7,    # 減算
    '<<': 9,   # 左シフト # 実装しない
    '>>': 9,   # 右シフト # 実装しない
    '>': 10,   # 大なり
    '<': 10,   # 小なり
    '>=': 10,  # 大なりイコール
    '<=': 10,  # 小なりイコール
    # 'in': 10,  # in # 配列の実装が先
    '==': 11,  # イコール
    '!=': 11,  # ノットイコール
    # '&': 12,   # ビットAND # 実装しない
    # '^': 13,   # ビットXOR # 実装しない
    # '|': 14,   # ビットOR # 実装しない
    '&&': 15,  # AND
    '||': 16,  # OR
    # 代入演算子
    # '=': 17,   # 代入 # 内部変数は未実装
    # '+=': 17,  # 加算代入 # 内部変数は未実装
    # '-=': 17,  # 減算代入 # 内部変数は未実装
    # '*=': 17,  # 乗算代入 # 内部変数は未実装
    # '/=': 17,  # 除算代入 # 内部変数は未実装
    # '%=': 17,  # 剰余代入 # 内部変数は未実装
    # '**=': 17,  # べき乗代入 # 内部変数は未実装
    # '<<=': 17,  # 左シフト代入 # 内部変数は未実装
    # '>>=': 17,  # 右シフト代入 # 内部変数は未実装
    # '&=': 17,   # ビットAND代入 # 内部変数は未実装
    # '^=': 17,   # ビットXOR代入 # 内部変数は未実装
    # '|=': 17,   # ビットOR代入 # 内部変数は未実装
    # その他
    # ',': 18,   # カンマ <fomula> , <fomula>,... # 代入の実装が先
}


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
        parsed_tokens = []
        # 単項演算子と変数の処理
        for token in self.tokens:
            # variable -> number or string
            parsed_token = {}
            if token['type'] == TOKENTYPE.VARIABLE:
                if ',' in token['value']:
                    var, num = token['value'].split(',')
                    num = int(num) - 1
                else:
                    var = token['value']
                    num = 0
                array = re.compile(r'(.*)\[([0-9]+)\]')
                if array.match(var):
                    var, num = array.match(var).groups()
                    num = int(num) - 1
                    debug_print('array', var, num)
                if var in self.variables:
                    values = self.variables[var]
                    if type(values) == list:
                        value = values[num]
                    else:
                        value = values
                    if type(value) == int or type(value) == float:
                        parsed_token['type'] = TOKENTYPE.NUMBER
                    elif type(value) == str:
                        parsed_token['type'] = TOKENTYPE.STRING
                    else:
                        self.setTokenError('Unknown variable type', self.token_start, self.token_end, TOKENTYPE.ERROR)
                    parsed_token['value'] = value
                    debug_print('value', parsed_token)
                else:
                    self.setTokenError('Unknown variable', self.token_start, self.token_end, TOKENTYPE.ERROR)
                    debug_print('Unknown variable', var)
                    return False
            # number
            elif token['type'] == TOKENTYPE.NUMBER:
                # int or float
                try:
                    if '.' in token['value']:
                        parsed_token['type'] = TOKENTYPE.NUMBER
                        parsed_token['value'] = float(token['value'])
                    else:
                        parsed_token['type'] = TOKENTYPE.NUMBER
                        parsed_token['value'] = int(token['value'])
                except ValueError:
                    self.setTokenError('Unknown number', self.token_start, self.token_end, TOKENTYPE.ERROR)
                    debug_print('Unknown number', token['value'])
                    return False

            # string
            elif token['type'] == TOKENTYPE.STRING:
                parsed_token = token
            # function
            elif token['type'] == TOKENTYPE.FUNCTION:
                parsed_token = token
            elif token['type'] == TOKENTYPE.OPERATOR:
                parsed_token = token
            elif token['type'] == TOKENTYPE.BRACKET:
                parsed_token = token
            elif token['type'] == TOKENTYPE.COMMA:
                parsed_token = token
            elif token['type'] == TOKENTYPE.SPACE:
                pass
            elif token['type'] == TOKENTYPE.OTHER:
                debug_print('Unknown token', token['value'])
                self.setTokenError('Unknown token', self.token_start, self.token_end, TOKENTYPE.ERROR)
                return False
            elif token['type'] == TOKENTYPE.END:
                parsed_tokens.append(token)
                break
            else:
                value = token['value']
                debug_print(f'Illegal syntax {value}')
                self.setTokenError(f'Illegal syntax {value}', self.token_start, self.token_end, TOKENTYPE.ERROR)
                return False

            if parsed_token['type'] == TOKENTYPE.NUMBER:
                j = len(parsed_tokens)
                print('j', j)
                try:
                    print('head', parsed_tokens[0])
                except Exception:
                    pass
                head = False
                if j == 1 and parsed_tokens[j - 1]['type'] == TOKENTYPE.OPERATOR:
                    ope = parsed_tokens[j - 1]['value']
                    head = True
                elif j >= 2 and parsed_tokens[j - 1]['type'] == TOKENTYPE.OPERATOR:
                    ope = parsed_tokens[j - 1]['value']
                    if parsed_tokens[j - 2]['type'] == TOKENTYPE.OPERATOR:
                        head = True
                    elif parsed_tokens[j - 2]['type'] == TOKENTYPE.BRACKET and parsed_tokens[j - 2]['value'] == '(':
                        head = True
                if head:
                    if ope == '-':
                        parsed_token['value'] = - parsed_token['value']
                        parsed_tokens.pop()
                    elif ope == '+':
                        parsed_tokens.pop()
            parsed_tokens.append(parsed_token)
            print('parsed token', parsed_tokens)
        self.tokens = parsed_tokens
        debug_print(self.tokens)
        return True

    def function(self):
        pass

    def booleanToNumber(self, boolean):
        if boolean:
            return {'type': TOKENTYPE.NUMBER, 'value': 1}
        else:
            return {'type': TOKENTYPE.NUMBER, 'value': 0}

    def reverce_polish_notation(self):
        # 演算順位　=> operator_order
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
        # and       :=  <fomula> && <fomula>
        # or        :=  <fomula> || <fomula>
        # function     <function>(<fomula> , <fomula>,...)
        # number       <number>
        # variable     <variable>
        # string       <string>
        # bracket      (<fomula>)
        # fomula       <expression> | <term> | <factor> | <compare> | <function> | <number> | <variable> | <string> | <bracket>
        # 逆ポーランド記法に変換する
        reversed_polish = []
        stack = []
        debug_print(self.tokens)
        for token in self.tokens:
            debug_print(token)
            # if (len(reversed_polish) == 0 or reversed_polish[-1]['type'] == TOKENTYPE.OPERATOR):
            #    if token['type'] == TOKENTYPE.OPERATOR and token['value'] == '-':
            #        # ( -1 * <formula> ) として扱う
            #        reversed_polish.append({'type': TOKENTYPE.NUMBER, 'value': -1})
            #        stack.append({'type': TOKENTYPE.OPERATOR, 'value': '*'})
            #        continue
            if token['type'] == TOKENTYPE.NUMBER or token['type'] == TOKENTYPE.STRING or token['type'] == TOKENTYPE.VARIABLE:
                reversed_polish.append(token)
            elif token['type'] == TOKENTYPE.FUNCTION:
                debug_print(token['value'])
                stack.append(token)
            elif token['type'] == TOKENTYPE.COMMA:
                while len(stack) > 0:
                    if stack[-1]['type'] == TOKENTYPE.BRACKET:
                        break
                    reversed_polish.append(stack.pop())
            elif token['type'] == TOKENTYPE.BRACKET:
                if token['value'] == '(':
                    stack.append(token)
                else:
                    while len(stack) > 0:
                        if stack[-1]['type'] == TOKENTYPE.BRACKET:
                            stack.pop()
                            break
                        reversed_polish.append(stack.pop())
            elif token['type'] == TOKENTYPE.OPERATOR:
                if len(stack) > 0 and stack[-1]['type'] == TOKENTYPE.BRACKET:
                    while len(stack) > 0:
                        if stack[-1]['type'] == TOKENTYPE.BRACKET:
                            break
                        reversed_polish.append(stack.pop())

                stack.append(token)
                print('token', token['value'])
                print('reverced polish', reversed_polish)
                print('stack', stack)
            elif token['type'] == TOKENTYPE.SPACE:
                pass
            elif token['type'] == TOKENTYPE.OTHER:
                self.setTokenError('Unknown token', self.token_start, self.token_end, TOKENTYPE.ERROR)
                return False
            elif token['type'] == TOKENTYPE.END:
                pass
        stack.reverse()
        debug_print('reverce porlad:', reversed_polish, stack, mode='value')
        for token in stack:
            reversed_polish.append(token)
        # 逆ポーランド記法を計算する
        for token in reversed_polish:
            debug_print(token, stack)
            match token['type']:
                case TOKENTYPE.NUMBER:
                    stack.append(token)
                case TOKENTYPE.STRING:
                    stack.append(token)
                case TOKENTYPE.VARIABLE:
                    stack.append(token)
                case TOKENTYPE.FUNCTION:
                    # TOKENから引数の数が分からないので、関数ごとに処理する
                    function = token['value']
                    match function:
                        case 'pow':
                            right = stack.pop()['value']
                            left = stack.pop()['value']
                            # どちらかが文字列ならエラー
                            if type(left) == str or type(right) == str:
                                self.setTokenError('String is not suport power', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': left ** right})
                        case 'int':
                            value = stack.pop()['value']
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(value)})
                        case 'float':
                            value = stack.pop()['value']
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': float(value)})
                        case 'str':
                            value = stack.pop()['value']
                            stack.append({'type': TOKENTYPE.STRING, 'value': str(value)})
                        case 'len':
                            value = stack.pop()['value']
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': len(value)})
                        case 'max':
                            right = stack.pop()['value']
                            left = stack.pop()['value']
                            if type(right) == str or type(left) == str:
                                tokentype = TOKENTYPE.STRING
                            stack.append({'type': tokentype, 'value': max(right, left)})
                        case 'min':
                            right = stack.pop()['value']
                            left = stack.pop()['value']
                            tokentype = TOKENTYPE.NUMBER
                            if type(right) == str or type(left) == str:
                                tokentype = TOKENTYPE.STRING
                            stack.append({'type': tokentype, 'value': min(right, left)})
                        case 'replace':  # replace(string, old, new)
                            new = str(stack.pop()['value'])
                            old = str(stack.pop()['value'])
                            string = str(stack.pop()['value'])
                            stack.append({'type': TOKENTYPE.STRING, 'value': string.replace(old, new)})
                        case 'split':  # split(string, separator)
                            separator = str(stack.pop()['value'])
                            string = str(stack.pop()['value'])
                            stack.append({'type': TOKENTYPE.STRING, 'value': string.split(separator)})
                        case 'upper':  # upper(string)
                            string = str(stack.pop()['value'])
                            stack.append({'type': TOKENTYPE.STRING, 'value': string.upper()})
                        case 'lower':  # lower(string)
                            string = str(stack.pop()['value'])
                            stack.append({'type': TOKENTYPE.STRING, 'value': string.lower()})
                        case 'if':  # if(condition, true, false)
                            false = stack.pop()
                            true = stack.pop()
                            condition = stack.pop()['value']
                            if condition == 1:
                                stack.append(true)
                            else:
                                stack.append(false)
                        case 'not':  # not(condition)
                            condition = stack.pop()['value']
                            if condition == 1:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 0})
                            else:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 1})
                        case 'and':  # and(condition, condition)
                            right = stack.pop()['value']
                            left = stack.pop()['value']
                            if right == 1 and left == 1:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 1})
                            else:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 0})
                        case 'or':  # or(condition, condition)
                            right = stack.pop()['value']
                            left = stack.pop()['value']
                            if right == 1 or left == 1:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 1})
                            else:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 0})
                        case 'match':  # match(string, pattern)
                            pattern = stack.pop()['value']
                            string = stack.pop()['value']
                            if re.match(pattern, string):
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 1})
                            else:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': 0})
                        case 'substring':  # substring(string, start, end)
                            end = stack.pop()['value']
                            start = stack.pop()['value']
                            string = stack.pop()['value']
                            stack.append({'type': TOKENTYPE.STRING, 'value': string[start:end]})
                        case 'random':  # random(start, end)
                            end = stack.pop()['value']
                            start = stack.pop()['value']
                            if start > end:
                                self.setTokenError('Random error start > end', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            try:
                                if type(start) == float or type(end) == float:
                                    stack.append({'type': TOKENTYPE.NUMBER, 'value': random.uniform(start, end)})
                                else:
                                    stack.append({'type': TOKENTYPE.NUMBER, 'value': random.randint(start, end)})
                            except ValueError:
                                self.setTokenError('Random error must number', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                        case 'random_int':  # randomint(0, 2^64 -1)
                            try:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': random.randint(0, 2**64 - 1)})
                            except ValueError:
                                self.setTokenError('Random error', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                        case 'random_float':  # randomfloat(0, 1)
                            try:
                                stack.append({'type': TOKENTYPE.NUMBER, 'value': random.random()})
                            except ValueError:
                                self.setTokenError('Random error', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                        case 'random_string':  # randomstring(length)
                            length = stack.pop()
                            stack.append({'type': TOKENTYPE.STRING,
                                          'value':
                                          ''.join([random.choice('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789') for i in range(length)])})
                        case 'uuid':  # uuid()
                            import uuid
                            stack.append({'type': TOKENTYPE.STRING, 'value': str(uuid.uuid4())})
                        case 'time':  # time() as hh:mm:ss
                            stack.append({'type': TOKENTYPE.STRING, 'value': time.strftime('%H:%M:%S')})
                        case 'date':  # date() as yyyy-mm-dd
                            stack.append({'type': TOKENTYPE.STRING, 'value': time.strftime('%Y-%m-%d')})
                        case 'datetime':  # datetime() as yyyy-mm-dd hh:mm:ss
                            stack.append({'type': TOKENTYPE.STRING, 'value': time.strftime('%Y-%m-%d %H:%M:%S')})
                        case 'timestamp':  # timestamp() as yyyy-mm-dd hh:mm:ss
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.time())})
                        case 'year':  # year() as yyyy
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%Y'))})
                        case 'month':  # month() as mm
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%m'))})
                        case 'day':  # day() as dd
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%d'))})
                        case 'hour':  # hour() as hh
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%H'))})
                        case 'minute':  # minute() as mm
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%M'))})
                        case 'second':  # second() as ss
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%S'))})
                        case 'weekday':  # weekday() as 0-6
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%w'))})
                        case 'week':  # week() as 0-53
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': int(time.strftime('%W'))})
                        case _:
                            self.setTokenError('Unknown function', self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False
                    debug_print(stack)
                case TOKENTYPE.OPERATOR:
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
                                self.setTokenError('String is not suport minus', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': left - right})
                        elif token['value'] == '*':
                            # string * number
                            if type(left) == str and type(right) == int:
                                stack.append({'type': TOKENTYPE.STRING, 'value': left * right})
                            elif type(left) == str or type(right) == str:
                                self.setTokenError('String is not suport multiply', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': left * right})
                        elif token['value'] == '/':
                            if type(left) == str or type(right) == str:
                                self.setTokenError('String is not suport divide', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': left / right})
                        elif token['value'] == '%':
                            if type(left) == str or type(right) == str:
                                self.setTokenError('String is not suport modulo', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': left % right})
                        elif token['value'] == '**':
                            if type(left) == str or type(right) == str:
                                self.setTokenError('String is not suport power', self.token_start, self.token_end, TOKENTYPE.ERROR)
                                return False
                            stack.append({'type': TOKENTYPE.NUMBER, 'value': left ** right})
                        elif token['value'] == '>':
                            stack.append(self.booleanToNumber(left > right))
                        elif token['value'] == '<':
                            stack.append(self.booleanToNumber(left < right))
                        elif token['value'] == '>=':
                            stack.append(self.booleanToNumber(left >= right))
                        elif token['value'] == '<=':
                            stack.append(self.booleanToNumber(left <= right))
                        elif token['value'] == '==':
                            stack.append(self.booleanToNumber(left == right))
                        elif token['value'] == '!=':
                            stack.append(self.booleanToNumber(left != right))
                        elif token['value'] == '&&':
                            stack.append(self.booleanToNumber(left and right))
                        elif token['value'] == '||':
                            stack.append(self.booleanToNumber(left or right))
                        else:
                            self.setTokenError('Unknown operator ' + token['value'], self.token_start, self.token_end, TOKENTYPE.ERROR)
                            return False

        self.result = stack.pop()['value']
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
        typeVariable1 = re.compile(r'^[a-zA-Z_$][a-zA-Z0-9_\-$]*')
        # info:abc[1]
        typeVariable2 = re.compile(r'^([a-zA-Z_$][a-zA-Z0-9__\-$]*\:)*[a-zA-Z_\-$][a-zA-Z0-9__\-$]*(\[([0-9]+|\*)\])*')
        # abc,1
        typeVariable3 = re.compile(r'^[a-zA-Z_$][a-zA-Z0-9_]*\,[0-9]+')
        typeOperator = re.compile(r'^(\+|\-|\*|\/|\%|\^|>|<|>=|<=|==|!=|&&|\|\|)')
        # typeExpression = re.compile(r'^\+|\-')
        # tyepTerm = re.compile(r'^\*|\/|\%')
        # typeFactor = re.compile(r'^\^')
        # typeAnd = re.compile(r'^&&')
        # typeOr = re.compile(r'^\|\|')
        # typeCompare = re.compile(r'^>|<|>=|<=|==|!=')
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
