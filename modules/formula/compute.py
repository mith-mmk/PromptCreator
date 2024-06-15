import re

from .function import callFunction
from .operator import operation
from .token import TOKENTYPE
from .util import debug_print

operator_order = {
    # block literal
    # 1: {}  := { <formula> } (TOKEN.BLOCK) # ブロック # 実装しない
    # 2: ()  := ( <formula> ) (TOKEN.BRACKET)
    # 2: []  := <variable> [ <formula> ] (TOKEN.ARRAYBRACKET) # 配列
    # 2: .   := <variable>.<variable> (TOKEN.POINT) # オブジェクト # 実装しない
    # 2: <function> := <function>(<formula> , <formula>,...) (TOKEN.FUNCTION)
    # 単項演算子
    # 3: ++  := ++<variable> (TOKEN.OPERATOR)
    # 3: --  := --<variable> (TOKEN.OPERATOR)
    # 4: !   := !<variable> (TOKEN.OPERATOR)
    # 4: ~   := ~<variable> (TOKEN.OPERATOR)
    "PLUS": 4,  # := + <variable> (TOKEN.OPERATOR) # 個別実装
    "MINUS": 4,  # := - <variable> (TOKEN.OPERATOR) # 何もしない
    # 2項演算子 2
    "**": 5,  # べき乗
    "*": 6,  # 乗算
    "/": 6,  # 除算
    "%": 6,  # 剰余
    "+": 7,  # 加算
    "-": 7,  # 減算
    "<<": 9,  # 左シフト # 実装しない
    ">>": 9,  # 右シフト # 実装しない
    ">": 10,  # 大なり
    "<": 10,  # 小なり
    ">=": 10,  # 大なりイコール
    "<=": 10,  # 小なりイコール
    # 'in': 10,  # in # 配列の実装が先
    "==": 11,  # イコール
    "!=": 11,  # ノットイコール
    # '&': 12,   # ビットAND # 実装しない
    # '^': 13,   # ビットXOR # 実装しない
    # '|': 14,   # ビットOR # 実装しない
    "&&": 15,  # AND
    "||": 16,  # OR
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
    # ',': 18,   # カンマ <formula> , <formula>,... # 代入の実装が先
}


class FormulaCompute:
    def __init__(self, formula="", variables={}, attributes={}, debug=False):
        self.formula = formula
        self.variables = variables
        self.attributes = attributes
        self.reslut = None
        self.debug = debug
        self.chained_variables = {}
        self.chained_attriblutes = {}
        self.mode = "init"

    def setDebug(self, debug):
        self.debug = debug

    def setFormula(self, formula):
        self.formula = formula
        self.reslut = None

    def setVariables(self, variables):
        self.variables = variables
        self.result = None

    def setChainedVariables(self, variables={}, attriblutes={}):
        self.chained_variables = variables
        self.chained_attriblutes = attriblutes
        self.result = None

    def getCompute(self, formula=None, variables={}, attributes={}):
        if formula is None:
            debug_print(f"formula: {formula}", debug=self.debug)
            self.compute()
            return self.result
        self.formula = formula
        self.variables = variables
        self.attributes = attributes
        self.compute()
        return self.result

    # V2 only function
    def getChained(self, variable, weight, max_number, next_multiply=1.0, joiner=", "):
        # get variavle var or var[1] or var["key"]
        # (.+?)\[\d+\]
        text = ""
        try:
            array = re.compile(r"(.+?)\[(\d+)\]")
            dict = re.compile(r"(.+?)\[\"(.+?)\"\]")
            subkey = None
            flag = "array"
            if array.match(variable):
                var, num = array.match(variable).groups()
                num = int(num) - 1
                flag = "array"
            elif dict.match(variable):
                var, subkey = dict.match(variable).groups()
                subkey = subkey
                flag = "dict"
            else:
                var = variable
                num = 0
            if num < 0:
                num = 0
            if var in self.chained_variables:
                values = self.chained_variables[var]
            import random

            from modules.prompt_v2 import choice_v2

            thresh = random.random()
            for _ in range(max_number):
                if thresh < weight:
                    choiced, attribute = choice_v2(values)
                    if flag == "array":
                        choice = choiced[num]
                    elif flag == "dict":
                        choice = attribute[subkey]
                    text = text.replace(choice + joiner, "")
                    text += choice + joiner
                else:
                    break
                weight *= next_multiply
        except Exception as e:
            print(e)
            raise e
        return text.strip()

    def getError(self):
        return self.token_error_message

    def compute(self):
        self.mode = "compute"
        self.result = None
        res = self.token()
        if not res:
            debug_print("token error", self.token_error_message, debug=self.debug)
            return False
        if not self.parse():
            debug_print("parse error", self.token_error_message, debug=self.debug)
            return False
        try:
            if not self.reverce_polish_notation():
                return False
        except Exception as e:
            debug_print(e, debug=self.debug)
            self.setTokenError(
                "Unknown error", self.token_start, self.token_end, TOKENTYPE.ERROR
            )
            return False
        return True

    def setTokenError(self, message, start, end, type):
        mode = self.mode
        self.token_error_message = message
        self.token_error_start = start
        self.token_error_end = end
        self.token_error_type = type
        if self.debug:
            debug_print(
                f"Error: {mode}: {message} start: {start} end: {end} type: {type}",
                debug=self.debug,
            )

    def parse(self):
        self.mode = "parse"
        parsed_tokens = []
        # 単項演算子と変数の処理
        for token in self.tokens:
            # variable -> number or string
            parsed_token = {}
            debug_print("token :", token, debug=self.debug)
            # variable or array
            if token["type"] == TOKENTYPE.VARIABLE:
                # key,1 => key[1] -> variables[key][0]
                if "," in token["value"]:
                    var, num = token["value"].split(",")
                    num = int(num) - 1
                else:
                    var = token["value"]
                    num = 0
                debug_print("var", var, num, debug=self.debug)
                # array key[1] => variables[key][0]
                array = re.compile(r"(.*)\[([0-9]+)\]")
                if array.match(var):
                    var, num = array.match(var).groups()
                    num = int(num) - 1
                    debug_print("array", var, num, debug=self.debug)
                # dict key["subkey"] => variables[key]["subkey"]
                subkey = None
                dict = re.compile(r"(.*)\[\"(.*)\"\]")
                if dict.match(var):
                    var, subkey = dict.match(var).groups()
                    debug_print("dict var subkey", var, subkey, debug=self.debug)
                if var in self.variables:
                    values = self.variables[var]
                    if subkey:
                        debug_print(f"subkey: {subkey}", debug=self.debug)
                        value = self.attributes.get(var, {}).get(subkey, None)
                    elif type(values) is list:
                        value = values[num]
                    else:
                        value = values
                    if type(value) is int or type(value) is float:
                        parsed_token["type"] = TOKENTYPE.NUMBER
                    elif type(value) is str:
                        parsed_token["type"] = TOKENTYPE.STRING
                    else:
                        self.setTokenError(
                            "Unknown variable type",
                            self.token_start,
                            self.token_end,
                            TOKENTYPE.ERROR,
                        )
                    parsed_token["value"] = value
                    debug_print("value", parsed_token, debug=self.debug)
                else:
                    self.setTokenError(
                        "Unknown variable",
                        self.token_start,
                        self.token_end,
                        TOKENTYPE.ERROR,
                    )
                    debug_print("Unknown variable", var, debug=self.debug)
                    return False
            # number
            elif token["type"] == TOKENTYPE.NUMBER:
                # int or float
                try:
                    if "." in token["value"]:
                        parsed_token["type"] = TOKENTYPE.NUMBER
                        parsed_token["value"] = float(token["value"])
                    else:
                        parsed_token["type"] = TOKENTYPE.NUMBER
                        parsed_token["value"] = int(token["value"])
                except ValueError:
                    self.setTokenError(
                        "Unknown number",
                        self.token_start,
                        self.token_end,
                        TOKENTYPE.ERROR,
                    )
                    debug_print("Unknown number", token["value"], debug=self.debug)
                    return False

            # string
            elif token["type"] == TOKENTYPE.STRING:
                parsed_token = token
            # function
            elif token["type"] == TOKENTYPE.FUNCTION:
                parsed_token = token
            elif token["type"] == TOKENTYPE.OPERATOR:
                parsed_token = token
            elif token["type"] == TOKENTYPE.BRACKET:
                parsed_token = token
            elif token["type"] == TOKENTYPE.COMMA:
                parsed_token = token
            elif token["type"] == TOKENTYPE.SPACE:
                pass
            elif token["type"] == TOKENTYPE.OTHER:
                debug_print("Unknown token", token["value"], debug=self.debug)
                self.setTokenError(
                    "Unknown token", self.token_start, self.token_end, TOKENTYPE.ERROR
                )
                return False
            elif token["type"] == TOKENTYPE.END:
                parsed_tokens.append(token)
                break
            else:
                value = token["value"]
                debug_print(f"Illegal syntax {value}", debug=self.debug)
                self.setTokenError(
                    f"Illegal syntax {value}",
                    self.token_start,
                    self.token_end,
                    TOKENTYPE.ERROR,
                )
                return False

            if parsed_token["type"] == TOKENTYPE.NUMBER:
                j = len(parsed_tokens)
                head = False
                if j == 1 and parsed_tokens[j - 1]["type"] == TOKENTYPE.OPERATOR:
                    ope = parsed_tokens[j - 1]["value"]
                    head = True
                elif j >= 2 and parsed_tokens[j - 1]["type"] == TOKENTYPE.OPERATOR:
                    ope = parsed_tokens[j - 1]["value"]
                    if parsed_tokens[j - 2]["type"] == TOKENTYPE.OPERATOR:
                        head = True
                    elif (
                        parsed_tokens[j - 2]["type"] == TOKENTYPE.BRACKET
                        and parsed_tokens[j - 2]["value"] == "("
                    ):
                        head = True
                if head:
                    if ope == "-":
                        parsed_token["value"] = -parsed_token["value"]
                        parsed_tokens.pop()
                    elif ope == "+":
                        parsed_tokens.pop()
            parsed_tokens.append(parsed_token)
            debug_print("parsed token", parsed_tokens)
        self.tokens = parsed_tokens
        debug_print(self.tokens, debug=self.debug)
        return True

    def function(self):
        pass

    def booleanToNumber(self, boolean):
        if boolean:
            return {"type": TOKENTYPE.NUMBER, "value": 1}
        else:
            return {"type": TOKENTYPE.NUMBER, "value": 0}

    def reverce_polish_notation(self):
        self.mode = "reverce_polish_notation"
        # 演算順位　=> operator_order
        # expression := <formula> + <formula> |
        #               <formula> - <formula> |
        # term       := <formula> * <formula>
        #               <formula> / <formula> |
        #               <formula> % <formula>
        # factor    :=  <formula> ^ <formula>
        # compare   :=  <formula> > <formula>
        #               <formula> < <formula>
        #               <formula> >= <formula>
        #               <formula> <= <formula>
        #               <formula> == <formula>
        #               <formula> != <formula>
        # and       :=  <formula> && <formula>
        # or        :=  <formula> || <formula>
        # function     <function>(<formula> , <formula>,...)
        # number       <number>
        # variable     <variable>
        # string       <string>
        # bracket      (<formula>)
        # formula       <expression> | <term> | <factor> | <compare> | <function> | <number> | <variable> | <string> | <bracket>
        # 追加実装部分
        # sentence     <formula> | <variable> = <formula> | var <variable> | <if> | <while> | <for> | <block>
        # block        { <sentence> } | { <sentence> ; <sentence> ; ... }
        # if           if (<formula>) <sentence> | if (<formula>) <sentence> else <sentence>
        # while        while (<formula>) <sentence>
        # for          for (<sentence> ; <formula> ; <sentence>) <sentence>
        # script       <sentence> | <sentence> ; <sentence> ; ...
        # 代入演
        # 算子
        # '=': 17,   # 代入 # 内部変数は未実装

        # 逆ポーランド記法に変換する
        reversed_polish = []
        stack = []
        debug_print(self.tokens, debug=self.debug)
        for token in self.tokens:
            debug_print(token, debug=self.debug)
            if (
                token["type"] == TOKENTYPE.NUMBER
                or token["type"] == TOKENTYPE.STRING
                or token["type"] == TOKENTYPE.VARIABLE
            ):
                reversed_polish.append(token)
            elif token["type"] == TOKENTYPE.FUNCTION:
                debug_print(token["value"], debug=self.debug)
                stack.append(token)
            elif token["type"] == TOKENTYPE.COMMA:
                while len(stack) > 0:
                    if stack[-1]["type"] == TOKENTYPE.BRACKET:
                        break
                    reversed_polish.append(stack.pop())
            elif token["type"] == TOKENTYPE.BRACKET:
                if token["value"] == "(":
                    stack.append(token)
                else:
                    while len(stack) > 0:
                        if stack[-1]["type"] == TOKENTYPE.BRACKET:
                            stack.pop()
                            break
                        reversed_polish.append(stack.pop())
            elif token["type"] == TOKENTYPE.OPERATOR:
                if len(stack) > 0 and stack[-1]["type"] == TOKENTYPE.BRACKET:
                    while len(stack) > 0:
                        if stack[-1]["type"] == TOKENTYPE.BRACKET:
                            break
                        reversed_polish.append(stack.pop())
                    stack.append(token)
                else:
                    if (
                        len(stack) > 0
                        and stack[-1]["type"] == TOKENTYPE.FUNCTION
                        and token["value"]
                        in [
                            "+",
                            "-",
                            "*",
                            "/",
                            "%",
                            "**",
                            ">",
                            "<",
                            ">=",
                            "<=",
                            "==",
                            "!=",
                            "&&",
                            "||",
                        ]
                    ):
                        reversed_polish.append(stack.pop())
                        stack.append(token)
                    elif len(stack) > 0 and stack[-1]["type"] == TOKENTYPE.OPERATOR:
                        order = operator_order[token["value"]]
                        preoder = operator_order[stack[-1]["value"]]
                        if order < preoder:
                            stack.append(token)
                        else:
                            reversed_polish.append(stack.pop())
                            stack.append(token)
                    else:
                        stack.append(token)
            elif token["type"] == TOKENTYPE.SPACE:
                pass
            elif token["type"] == TOKENTYPE.OTHER:
                self.setTokenError(
                    "Unknown token", self.token_start, self.token_end, TOKENTYPE.ERROR
                )
                return False
            elif token["type"] == TOKENTYPE.END:
                pass
        stack.reverse()
        reversed_polish.extend(stack)
        stack = []
        debug_print(
            "reverce porlad:", reversed_polish, stack, mode="value", debug=self.debug
        )
        # 逆ポーランド記法を計算する
        for token in reversed_polish:
            debug_print(token, stack, debug=self.debug)
            match token["type"]:
                case TOKENTYPE.NUMBER:
                    stack.append(token)
                case TOKENTYPE.STRING:
                    stack.append(token)
                case TOKENTYPE.VARIABLE:
                    stack.append(token)
                case TOKENTYPE.FUNCTION:
                    # TOKENから引数の数が分からないので、関数ごとに処理する
                    function = token["value"]
                    callFunction(self, function, stack)
                    debug_print(stack, debug=self.debug)
                case TOKENTYPE.OPERATOR:
                    operation(self, token, stack)
                case TOKENTYPE.END:
                    break
        debug_print("end", stack)
        if len(stack) != 1:
            self.setTokenError(
                "Formula error function argments too many?",
                self.token_start,
                self.token_end,
                TOKENTYPE.ERROR,
            )
            return False
        self.result = stack.pop()["value"]
        return True

    def token(self):
        self.mode = "token"
        self.tokens = []
        self.token = ""
        self.token_type = TOKENTYPE.NONE
        self.token_start = 0
        self.token_end = 0
        self.token_error = False
        self.token_error_message = ""
        self.token_error_start = 0
        self.token_error_end = 0
        self.token_error_type = 0
        count = 0
        typeSpace = re.compile(r"^\s+")
        typeNumber = re.compile(r"^[0-9]+(\.[0-9]+)?")
        typeVariable1 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_$]*")
        # info:abc[1]
        typeVariable2 = re.compile(
            r"^([a-zA-Z_$][a-zA-Z0-9__$]*\:)*[a-zA-Z_\-$][a-zA-Z0-9_$]*(\[([0-9]+|\*)\])*"
        )
        # abc,1
        typeVariable3 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_]*\,[0-9]+")
        # abc["abc"]
        typeVariable4 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_]*\[\".*?\"\]")
        # abc['abc']
        typeVariable5 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_]*\[\'.*?\'\]")
        typeOperator = re.compile(r"^(\+|\-|\*{1,2}|\/|\%|\^|>|<|>=|<=|==|!=|&&|\|\|)")
        typeBracket = re.compile(r"^(\(|\))")
        typeFunction = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*\(")
        typeComma = re.compile(r"^,")
        # " \" "
        typeString = re.compile(r'^("([^\\]|\\.)*?"|\'([^\\]|.)*?\')')
        typeEnd = re.compile(r"^$")

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
                debug_print(function, debug=self.debug)
                function = function.replace(" ", "", 1)
                function = function[:-1]
                self.tokens.append({"type": TOKENTYPE.FUNCTION, "value": function})
                count += len(typeFunction.match(current).group(0)) - 1
            elif typeNumber.match(current):
                self.token_type = TOKENTYPE.NUMBER
                self.token_start = count
                self.token_end = count + len(typeNumber.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.NUMBER,
                        "value": typeNumber.match(current).group(0),
                    }
                )
                count += len(typeNumber.match(current).group(0))
            elif typeOperator.match(current):
                self.token_type = TOKENTYPE.OPERATOR
                self.token_start = count
                self.token_end = count + len(typeOperator.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.OPERATOR,
                        "value": typeOperator.match(current).group(0),
                    }
                )
                count += len(typeOperator.match(current).group(0))
            elif typeVariable5.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable5.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable5.match(current).group(0),
                    }
                )
                count += len(typeVariable5.match(current).group(0))
            elif typeVariable4.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable4.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable4.match(current).group(0),
                    }
                )
                count += len(typeVariable4.match(current).group(0))
            elif typeVariable3.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable3.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable3.match(current).group(0),
                    }
                )
                count += len(typeVariable3.match(current).group(0))
            elif typeVariable2.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable2.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable2.match(current).group(0),
                    }
                )
                count += len(typeVariable2.match(current).group(0))
            elif typeVariable1.match(current):
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable1.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable1.match(current).group(0),
                    }
                )
                count += len(typeVariable1.match(current).group(0))
            elif typeBracket.match(current):
                self.token_type = TOKENTYPE.BRACKET
                self.token_start = count
                self.token_end = count + len(typeBracket.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.BRACKET,
                        "value": typeBracket.match(current).group(0),
                    }
                )
                count += len(typeBracket.match(current).group(0))
            elif typeComma.match(current):
                self.token_type = TOKENTYPE.COMMA
                self.token_start = count
                self.token_end = count + len(typeComma.match(current).group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.COMMA,
                        "value": typeComma.match(current).group(0),
                    }
                )
                count += len(typeComma.match(current).group(0))
            elif typeString.match(current):
                self.token_type = TOKENTYPE.STRING
                self.token_start = count
                self.token_end = count + len(typeString.match(current).group(0))
                string = typeString.match(current).group(0)
                # remove start and end "
                debug_print(string, debug=self.debug)
                string = string[1:-1]
                # replace escpcial char
                string = string.replace('\\"', '"')
                string = string.replace("\\'", "'")
                string = string.replace("\\n", "\n")
                string = string.replace("\\r", "\r")
                string = string.replace("\\t", "\t")
                string = string.replace("\\\\", "\\")
                self.tokens.append({"type": TOKENTYPE.STRING, "value": string})
                count += len(typeString.match(current).group(0))
            elif typeEnd.match(current):
                break
            else:
                self.setTokenError(
                    f"Syntax error {current}",
                    self.token_start,
                    self.token_end,
                    TOKENTYPE.ERROR,
                )
                return False
        self.token_type = TOKENTYPE.END
        self.token_start = count
        self.token_end = count
        self.tokens.append({"type": TOKENTYPE.END, "value": ""})
        return True

    # 静的関数
    @staticmethod
    def calculate(formula, variables={}, debug=False):
        from .compute import FormulaCompute

        compute = FormulaCompute(formula, variables, attributes={}, debug=debug)
        if compute.compute():
            return compute.getCompute()
        else:
            return None

    @staticmethod
    def calculate_debug(formula, variables={}):
        from .compute import FormulaCompute

        compute = FormulaCompute(formula, variables, debug=True)
        if compute.compute():
            return compute.getCompute(), None
        else:
            return None, compute.getError()
