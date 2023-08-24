import re


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


class FormulaCompute():
    def __init__(self, formula, variables):
        self.formula = formula
        self.variables = variables
        self.reslut = None

    def getCompute(self):
        return self.result
    
    def compute(self):
        self.result = None
        if not self.token():
            return False
        if not self.parse():
            return False
        return True
    
    def setTokenError(self, message, start, end, type):
        pass
      
    def parse(self):
        for i, token in enumerate(self.tokens):
            # variable -> number or string
            if token in self.variables:
                self.tokens[i] = self.variables[token]
            # number
            elif token.replace('.', '', 1).isdigit():
                # float -> float
                if '.' in token:
                    self.tokens[i] = float(token)
                # int -> int
                else:
                    self.tokens[i] = int(token)
            # string -> string
            elif token.startswith('"') and token.endswith('"'):
                self.tokens[i] = token[1:-1]
            # function -> function
            elif token.startswith('f_'):
                self.tokens[i] = token
            # other -> error
            else:
                self.token_error = True
                self.token_error_message = 'Unknown token'
                self.token_error_start = self.token_start
                self.token_error_end = self.token_end
                self.token_error_type = TOKENTYPE.ERROR
                return False

        # expression := <fomula> + <fomula> |
        #               <fomula> - <fomula> |
        # term       := <fomula> * <fomula>
        #               <fomula> / <fomula> |
        #               <fomula> % <fomula>
        # factor       <fomula> ^ <fomula>
        # function     <function>(<fomula>,<fomula>,...)
        # number       <number>
        # variable     <variable>
        # string       <string>
        # bracket      (<fomula>)
        # fomula       <expression> | <term> | <factor> | <function> | <number> | <variable> | <string> | <bracket>

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
        for token in self.tokens:
            if token['type'] == TOKENTYPE.NUMBER or token['type'] == TOKENTYPE.STRING or token['type'] == TOKENTYPE.VARIABLE:
                reversed_polish_notation.append(token)
            elif token['type'] == TOKENTYPE.FUNCTION:
                stack.append(token)
            elif token['type'] == TOKENTYPE.COMMA:
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
            elif token['type'] == TOKENTYPE.FUNCTION:
                stack.append(token)
            elif token['type'] == TOKENTYPE.END:
                pass
        stack.reverse()
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
                    function = stack.pop()
                    args = []
                    while len(stack) > 0:
                        if stack[-1]['type'] == TOKENTYPE.COMMA:
                            stack.pop()
                            break
                        args.append(stack.pop())
                    args.reverse()
                    stack.append(function['value'](args))
                case TOKENTYPE.OPERATOR:
                    right = stack.pop()
                    left = stack.pop()
                    if token['value'] == '+':
                        stack.append(left + right)
                    elif token['value'] == '-':
                        stack.append(left - right)
                    elif token['value'] == '*':
                        stack.append(left * right)
                    elif token['value'] == '/':
                        stack.append(left / right)
                    elif token['value'] == '%':
                        stack.append(left % right)
                    elif token['value'] == '^':
                        stack.append(left ** right)
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
        typeVariable = re.compile(r'^((command:|info:)[a-zA-Z_][a-zA-Z0-9_]*|([a-zA-Z_][a-zA-Z0-9_],[0-9]+|)')
        typeOperator = re.compile(r'^(\+|-|\*|/|%|\^)')
        typeBracket = re.compile(r'^(\(|\))')
        typeFunction = re.compile(r'^[a-zA-Z_][a-zA-Z0-9_]*\s*\(')
        typeComma = re.compile(r'^,')
        # " \" "
        typeString = re.compile(r'^("[^"]*"|\'[^\']*\'')

        count = 0
        while count < len(self.formula):
            current = self.formula[count:]
            match current:
                case typeSpace.match(current):
                    self.token_type = TOKENTYPE.SPACE
                    self.token_start = count
                    self.token_end = count + len(typeSpace.match(current).group(0))
                    count += len(typeSpace.match(current).group(0))
                case typeNumber.match(current):
                    self.token_type = TOKENTYPE.NUMBER
                    self.token_start = count
                    self.token_end = count + len(typeNumber.match(current).group(0))
                    self.tokens.append({'type': TOKENTYPE.NUMBER, 'value': typeNumber.match(current).group(0)})
                    count += len(typeNumber.match(current).group(0))
                case typeVariable.match(current):
                    self.token_type = TOKENTYPE.VARIABLE
                    self.token_start = count
                    self.token_end = count + len(typeVariable.match(current).group(0))
                    self.tokens.append({'type': TOKENTYPE.VARIABLE, 'value': typeVariable.match(current).group(0)})
                    count += len(typeVariable.match(current).group(0))
                case typeOperator.match(current):
                    self.token_type = TOKENTYPE.OPERATOR
                    self.token_start = count
                    self.token_end = count + len(typeOperator.match(current).group(0))
                    self.tokens.append({'type': TOKENTYPE.OPERATOR, 'value': typeOperator.match(current).group(0)})
                    count += len(typeOperator.match(current).group(0))
                case typeBracket.match(current):
                  
                    self.token_type = TOKENTYPE.BRACKET
                    self.token_start = count
                    self.token_end = count + len(typeBracket.match(current).group(0))
                    self.tokens.append({'type': TOKENTYPE.BRACKET, 'value': typeBracket.match(current).group(0)})
                    count += len(typeBracket.match(current).group(0))
                case typeFunction.match(current):
                    self.token_type = TOKENTYPE.FUNCTION
                    self.token_start = count
                    self.token_end = count + len(typeFunction.match(current).group(0))
                    function = typeFunction.match(current).group(0)
                    # remove space and (
                    function = function.replace(' ', '', 1)
                    function = function[:-1]
                    self.tokens.append({'type': TOKENTYPE.FUNCTION, 'value': function})
                    count += len(typeFunction.match(current).group(0) - 1)
                case typeComma.match(current):
                    self.token_type = TOKENTYPE.COMMA
                    self.token_start = count
                    self.token_end = count + len(typeComma.match(current).group(0))
                    count += len(typeComma.match(current).group(0))
                case typeString.match(current):
                    self.token_type = TOKENTYPE.STRING
                    self.token_start = count
                    self.token_end = count + len(typeString.match(current).group(0))
                    string = typeString.match(current).group(0)
                    # remove start and end "
                    string = string[1:-1]
                    escape = (r'\\(^[rnt]))')
                    string = re.sub(escape, r'\1', string)
                    self.tokens.append(string)
                    count += len(typeString.match(current).group(0))
                case _:
                    self.token_type = TOKENTYPE.OTHER
                    self.token_start = count
                    self.token_end = count + 1
                    self.tokens.append({'type': TOKENTYPE.OTHER, 'value': current[0]})
                    count += 1
        self.token_type = TOKENTYPE.END
        self.token_start = count
        self.token_end = count
        self.tokens.append({'type': TOKENTYPE.END, 'value': ''})
        return True
