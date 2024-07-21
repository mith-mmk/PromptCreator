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
    def __init__(
        self,
        formula="",
        variables={},
        attributes={},
        debug=False,
        version=1.0,
        callback=None,
    ):
        self.formula = formula
        self.variables = variables
        self.attributes = attributes
        self.chained_variables = {}
        self.chained_attriblutes = {}
        self.reslut = None
        self.debug = debug
        self.mode = "init"
        self.version = version
        self.callback = callback

    def setVersion(self, version):
        self.version = version

    def setDebug(self, debug):
        self.debug = debug

    def setFormula(self, formula):
        self.formula = formula
        self.reslut = None

    def setVariables(self, variables):
        self.variables = variables
        self.result = None

    def setCallback(self, callback):
        self.callback = callback

    def getCompute(self, formula=None, variables={}, attributes={}):
        if formula is None:
            debug_print(f"formula: {formula}", debug=self.debug)
            self.compute()
            return self.result
        self.formula = formula
        self.variables = variables
        self.attributes = attributes
        self.error_stacks = ""
        self.compute()
        return self.result

    def callbackFunction(self, function, args):
        if self.callback is None:
            raise Exception("callback is None")
        return self.callback._callback(function, args)

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
            self.setTokenError(e, self.token_start, self.token_end, TOKENTYPE.ERROR)
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
        self.error_stacks = (
            self.error_stacks
            + f"Error: {mode}: {message} start: {start} end: {end} type: {type}\n"
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
                if self.version < 2:
                    if "," in token["value"]:
                        var, num = token["value"].split(",")
                        num = int(num) - 1
                    else:
                        var = token["value"]
                        num = 0
                    debug_print("var", var, num, debug=self.debug)

                    # v1 の処理　v2 は []　内を式として処理する

                    array = re.compile(r"(.*)\[([0-9]+)\]")
                    array_match = array.match(var)
                    if array_match:
                        var, num = array_match.groups()
                        num = int(num) - 1
                        debug_print("array", var, num, debug=self.debug)
                    # dict key["subkey"] => variables[key]["subkey"]
                    subkey = None
                    dict = re.compile(r"(.*)\[\"(.*)\"\]")
                    dict_match = dict.match(var)
                    if dict_match:
                        var, subkey = dict_match.groups()
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
                else:
                    # V2 では変数の処理は後で行う
                    parsed_token = token
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
            elif token["type"] == TOKENTYPE.ARRAYBRACKET:
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
                        parsed_tokens[j - 2]["type"] == TOKENTYPE.ARRAYBRACKET
                        and parsed_tokens[j - 2]["value"] == "["
                    ):
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
        # variable     <variable>　| <variable>[<formula>] | <variable>.<variable>
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
        debug_print(f"tokens {self.tokens}", debug=self.debug)
        for token in self.tokens:
            debug_print(token, debug=self.debug)
            if token["type"] == TOKENTYPE.NUMBER or token["type"] == TOKENTYPE.STRING:
                reversed_polish.append(token)
            elif token["type"] == TOKENTYPE.VARIABLE:
                stack.append(token)
            elif token["type"] == TOKENTYPE.FUNCTION:
                debug_print(token["value"], debug=self.debug)
                stack.append(token)
            elif token["type"] == TOKENTYPE.COMMA:
                while len(stack) > 0:
                    if stack[-1]["type"] == TOKENTYPE.BRACKET:
                        break
                    reversed_polish.append(stack.pop())
                reversed_polish.append(token)
            elif token["type"] == TOKENTYPE.ARRAYBRACKET:
                if token["value"] == "[":
                    # 一つ前がVARIABLEならば、ARRAYOBJECTに変換する
                    if len(stack) > 0 and stack[-1]["type"] == TOKENTYPE.VARIABLE:
                        stack[-1]["type"] = TOKENTYPE.ARRAYOBJECT
                        stack[-1]["value"] = stack[-1]["value"]
                    stack.append(token)
                else:
                    while len(stack) > 0:
                        if stack[-1]["type"] == TOKENTYPE.ARRAYBRACKET:
                            stack.pop()
                            break
                        reversed_polish.append(stack.pop())
            elif token["type"] == TOKENTYPE.BRACKET:
                if token["value"] == "(":
                    reversed_polish.append(token)
                    stack.append(token)
                else:
                    while len(stack) > 0:
                        if stack[-1]["type"] == TOKENTYPE.BRACKET:
                            stack.pop()
                            break
                        reversed_polish.append(stack.pop())
                    # ) を挿入
                    reversed_polish.append(token)

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
                        and (
                            stack[-1]["type"] == TOKENTYPE.FUNCTION
                            or stack[-1]["type"] == TOKENTYPE.ARRAYOBJECT
                        )
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
        # blancket check
        if self.version >= 2:
            debug_print(
                "reverce porlad:", reversed_polish, mode="value", debug=self.debug
            )

            def search_functionend(reversed_polish, pos, is_nested=False):
                is_function = False
                blancket = 0
                while pos >= 0:
                    token = reversed_polish[pos]
                    if token["type"] == TOKENTYPE.BRACKET:
                        if token["value"] == ")":
                            blancket += 1
                            pos -= 1
                            continue
                        elif token["value"] == "(":
                            if blancket > 0:
                                blancket -= 1
                                pos -= 1
                                continue
                    if token["type"] == TOKENTYPE.FUNCTION:
                        pos -= 1
                    if token["type"] == TOKENTYPE.BRACKET:
                        if token["value"] == "(":
                            is_function = False
                            token["type"] = TOKENTYPE.FUNCTIONEND
                            token["value"] = "$$$FUNCTIONEND$$$"
                    pos -= 1
                return pos

            pos = len(reversed_polish) - 1
            search_functionend(reversed_polish, pos)

            """
            nest = 0
            is_function = False
            pos = len(reversed_polish) - 1
            while pos >= 0:  # pos > 0 から pos >= 0 へ変更
                token = reversed_polish[pos]
                if token["type"] == TOKENTYPE.FUNCTION:
                    is_function = True
                elif token["type"] == TOKENTYPE.BRACKET and is_function:
                    if token["value"] == ")":
                        nest += 1
                    elif token["value"] == "(":  # 正しい括弧の種類を確認
                        nest -= 1
                        if nest == 0:
                            is_function = False
                            token["type"] = TOKENTYPE.FUNCTIONEND
                            token["value"] = "$$$FUNCTIONEND$$$"
                pos -= 1
            """
            debug_print(
                "reverce porlad:", reversed_polish, mode="value", debug=self.debug
            )
            debug_print(
                "reverce porlad:", reversed_polish, mode="type", debug=self.debug
            )

        # 逆ポーランド記法を計算する
        # for token in reversed_polish:
        while len(reversed_polish) > 0:
            token = reversed_polish.pop(0)
            debug_print(token, stack, debug=self.debug)
            match token["type"]:
                case TOKENTYPE.NUMBER:
                    stack.append(token)
                case TOKENTYPE.STRING:
                    stack.append(token)

                case TOKENTYPE.VARIABLE:
                    var = token["value"]
                    if var in self.variables:
                        values = self.variables[var]
                        if type(values) is list:
                            stack.append(
                                {
                                    "type": TOKENTYPE.NUMBER,
                                    "value": values[0],
                                }
                            )
                        else:
                            stack.append(
                                {
                                    "type": TOKENTYPE.NUMBER,
                                    "value": values,
                                }
                            )
                case TOKENTYPE.ARRAYOBJECT:
                    if len(stack) > 0:
                        var = token["value"]
                        key = stack.pop()["value"]
                        debug_print(f"var {var}[{key}]", debug=self.debug)
                        values = self.variables.get(var, [])
                        attributes = self.attributes.get(var, {})
                        if key in attributes:
                            stack.append(
                                {
                                    "type": TOKENTYPE.NUMBER,
                                    "value": attributes[key],
                                }
                            )
                        else:
                            try:
                                num = int(key) - 1
                                if num < 0:
                                    num = 0
                                stack.append(
                                    {
                                        "type": TOKENTYPE.NUMBER,
                                        "value": values[num],
                                    }
                                )
                            except Exception as e:
                                debug_print(e, debug=self.debug)
                                stack.append(
                                    {
                                        "type": TOKENTYPE.NUMBER,
                                        "value": values[0],
                                    }
                                )
                        debug_print(stack, debug=self.debug)
                case TOKENTYPE.FUNCTION:

                    def function_parse(function, stack):
                        args = []
                        # FANCTIONENDまでの引数を取得する
                        while len(stack) > 0:
                            arg = stack.pop()
                            debug_print(f"arg {arg}", debug=self.debug)
                            if arg["type"] == TOKENTYPE.FUNCTIONEND:
                                break
                            elif arg["type"] == TOKENTYPE.FUNCTION:
                                ret, val = function_parse(arg["value"], stack)
                                if not ret:
                                    raise Exception(f"function error {arg['value']}")
                                args.append(val)
                            args.append(arg)
                        debug_print(
                            f"function {function} args {args}",
                            mode="value",
                            debug=self.debug,
                        )
                        ret, val = callFunction(self, function, args, args)  # type: ignore
                        return ret, val

                    # TOKENから引数の数が分からないので、関数ごとに処理する
                    function = token["value"]
                    if self.version >= 2:
                        # FANCTIONENDまでの引数を取得する
                        ret, val = function_parse(function, stack)
                    else:
                        ret, val = callFunction(self, function, stack)  # type: ignore
                    if not ret:
                        debug_print(f"function error {function}", debug=self.debug)
                        raise Exception(f"function error {function}")
                    stack.append(val)

                    debug_print(stack, debug=self.debug)
                case TOKENTYPE.FUNCTIONEND:
                    if self.version >= 2:
                        stack.append(token)
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
        # self.token = ""
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
        # V2では配列に式を入れることができる
        typeVariable1 = re.compile(
            r"^[a-zA-Z_$][a-zA-Z0-9_$]*|^([a-zA-Z_$][a-zA-Z0-9__$]*\:)*[a-zA-Z_\-$][a-zA-Z0-9_$]"
        )
        # info:abc[1] V1 only
        typeVariable2 = re.compile(
            r"^([a-zA-Z_$][a-zA-Z0-9__$]*\:)*[a-zA-Z_\-$][a-zA-Z0-9_$]*(\[([0-9]+|\*)\])*"
        )
        # abc,1 V1 only
        typeVariable3 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_]*\,[0-9]+")
        # abc["abc"] V1 only
        typeVariable4 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_]*\[\".*?\"\]")
        # abc['abc'] V1 only
        typeVariable5 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_]*\[\'.*?\'\]")
        # abc.abc V2 only
        typeVariable6 = re.compile(r"^[a-zA-Z_$][a-zA-Z0-9_]*\.[a-zA-Z_$][a-zA-Z0-9_]*")
        typeOperator = re.compile(r"^(\+|\-|\*{1,2}|\/|\%|\^|>|<|>=|<=|==|!=|&&|\|\|)")
        typeBracket = re.compile(r"^(\(|\))")
        typeArrayBracket = re.compile(r"^\[|\]")
        typeFunction = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*\s*\(")
        typeComma = re.compile(r"^,")
        # " \" "
        typeString = re.compile(r'^("([^\\]|\\.)*?"|\'([^\\]|.)*?\')')
        typeEnd = re.compile(r"^$")

        count = 0
        while count < len(self.formula):
            current = self.formula[count:]
            typeSpace_match = typeSpace.match(current)
            typeFunction_match = typeFunction.match(current)
            typeNumber_match = typeNumber.match(current)
            typeOperator_match = typeOperator.match(current)
            typeVariable1_match = typeVariable1.match(current)
            typeVariable2_match = typeVariable2.match(current)
            typeVariable3_match = typeVariable3.match(current)
            typeVariable4_match = typeVariable4.match(current)
            typeVariable5_match = typeVariable5.match(current)
            typeVariable6_match = typeVariable6.match(current)
            typeBracket_match = typeBracket.match(current)
            typeArrayBracket_match = typeArrayBracket.match(current)
            typeComma_match = typeComma.match(current)
            typeString_match = typeString.match(current)
            typeEnd_match = typeEnd.match(current)
            if typeSpace_match:
                self.token_type = TOKENTYPE.SPACE
                self.token_start = count
                self.token_end = count + len(typeSpace_match.group(0))
                count += len(typeSpace_match.group(0))
            elif typeFunction_match:
                self.token_type = TOKENTYPE.FUNCTION
                self.token_start = count
                self.token_end = count + len(typeFunction_match.group(0))
                function = typeFunction_match.group(0)
                debug_print(function, debug=self.debug)
                function = function.replace(" ", "", 1)
                function = function[:-1]
                self.tokens.append({"type": TOKENTYPE.FUNCTION, "value": function})
                count += len(typeFunction_match.group(0)) - 1
            elif typeNumber_match:
                self.token_type = TOKENTYPE.NUMBER
                self.token_start = count
                self.token_end = count + len(typeNumber_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.NUMBER,
                        "value": typeNumber_match.group(0),
                    }
                )
                count += len(typeNumber_match.group(0))
            elif typeOperator_match:
                self.token_type = TOKENTYPE.OPERATOR
                self.token_start = count
                self.token_end = count + len(typeOperator_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.OPERATOR,
                        "value": typeOperator_match.group(0),
                    }
                )
                count += len(typeOperator_match.group(0))
            elif typeVariable5_match and self.version < 2:
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable5_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable5_match.group(0),
                    }
                )
                count += len(typeVariable5_match.group(0))
            elif typeVariable4_match and self.version < 2:
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable4_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable4_match.group(0),
                    }
                )
                count += len(typeVariable4_match.group(0))
            elif typeVariable3_match and self.version < 2:
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable3_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable3_match.group(0),
                    }
                )
                count += len(typeVariable3_match.group(0))
            elif typeVariable6_match and self.version >= 2:
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable6_match.group(0),
                    }
                )
                count += len(typeVariable6_match.group(0))
            elif typeVariable2_match and self.version < 2:
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable2_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable2_match.group(0),
                    }
                )
                count += len(typeVariable2_match.group(0))
            elif typeVariable1_match:
                self.token_type = TOKENTYPE.VARIABLE
                self.token_start = count
                self.token_end = count + len(typeVariable1_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.VARIABLE,
                        "value": typeVariable1_match.group(0),
                    }
                )
                count += len(typeVariable1_match.group(0))
            elif typeBracket_match:
                self.token_type = TOKENTYPE.BRACKET
                self.token_start = count
                self.token_end = count + len(typeBracket_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.BRACKET,
                        "value": typeBracket_match.group(0),
                    }
                )
                count += len(typeBracket_match.group(0))
            elif typeArrayBracket_match and self.version >= 2:
                self.token_type = TOKENTYPE.ARRAYBRACKET
                self.token_start = count
                self.token_end = count + len(typeArrayBracket_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.ARRAYBRACKET,
                        "value": typeArrayBracket_match.group(0),
                    }
                )
                count += len(typeArrayBracket_match.group(0))
            elif typeComma_match:
                self.token_type = TOKENTYPE.COMMA
                self.token_start = count
                self.token_end = count + len(typeComma_match.group(0))
                self.tokens.append(
                    {
                        "type": TOKENTYPE.COMMA,
                        "value": typeComma_match.group(0),
                    }
                )
                count += len(typeComma_match.group(0))
            elif typeString_match:
                self.token_type = TOKENTYPE.STRING
                self.token_start = count
                self.token_end = count + len(typeString_match.group(0))
                string = typeString_match.group(0)
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
                count += len(typeString_match.group(0))
            elif typeEnd_match:
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
    def calculate(formula, variables={}, debug=False, version=1):
        from .compute import FormulaCompute

        compute = FormulaCompute(
            formula, variables, attributes={}, debug=debug, version=version
        )
        if compute.compute():
            return compute.getCompute()
        else:
            return None

    @staticmethod
    def calculate_debug(formula, variables={}, attributes={}, version=1):
        from .compute import FormulaCompute

        compute = FormulaCompute(
            formula, variables, attributes={}, debug=True, version=version
        )
        if compute.compute():
            return compute.getCompute(), None
        else:
            return None, compute.getError()
