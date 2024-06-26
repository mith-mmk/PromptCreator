import re

import modules.formula.compute as compute
from modules.formula.util import debug_print


class CallbackFunctions:
    def __init__(self, compute: compute.FormulaCompute | None = None) -> None:
        self.compute = compute
        pass

    def _callback(self, function, args):
        try:
            match function:
                case "chained":

                    if len(args) == 3:
                        return self.getChained(args[0], args[1], args[2])
                    if len(args) == 4:
                        return self.getChained(args[0], args[1], args[2], args[3])
                    if len(args) == 5:
                        return self.getChained(
                            args[0], args[1], args[2], args[3], args[4]
                        )
                case "choice":
                    return self.getChained(args[0])
                case "value":
                    return self.getValue(args[0])
                case "attribute":
                    return self.getAttribute(args[0], args[1])
                case "choice_index":
                    return self.getChoiceIndex(args[0], args[1], args[2])
                case "choice_attribute":
                    return self.getChoiceAttribute(args[0], args[1], args[2])
                case "test":
                    return "testdayo"
                case _:
                    raise Exception(f"callback error {function}")
        except Exception as e:
            debug_print(e)
            raise Exception(f"callback error {function} {e}")

    def setCompute(self, compute):
        self.compute = compute

    # V2 only function Callbackに分割する
    def getChained(
        self, variable, weight=1, max_number=1, joiner=", ", next_multiply=1.0
    ):
        # get variavle var or var[1] or var["key"]
        # (.+?)\[\d+\]
        if self.compute is None:
            raise Exception("compute is None")
        compute = self.compute
        text = ""
        try:
            array = re.compile(r"(.+?)\[(\d+)\]")
            dict = re.compile(r"(.+?)\[\"(.+?)\"\]|(.+?)\[\'(.+?)\'\]")
            subkey = None
            flag = "array"
            if array.match(variable):
                match = array.match(variable)
                if match:
                    var, num = match.groups()
                    num = int(num) - 1
                    flag = "array"
                else:
                    raise Exception(f"getChained error {variable}")
            elif dict.match(variable):
                match = dict.match(variable)
                if match:
                    var, subkey = match.groups()
                    subkey = subkey
                    flag = "dict"
                else:
                    raise Exception(f"getChained error {variable}")
            else:
                var = variable
                num = 0
            if num < 0:
                num = 0
            if var in compute.chained_variables:
                values = compute.chained_variables[var]
            import random

            from modules.prompt_v2 import choice_v2

            thresh = random.random()
            for _ in range(max_number):
                if thresh < weight:
                    choiced, attribute = choice_v2(values)
                    if attribute is None:
                        attribute = {}
                    if flag == "array":
                        choice = choiced[num]
                    elif flag == "dict":
                        if subkey in attribute:
                            choice = attribute[subkey]
                        choice = attribute[subkey]
                    text = text.replace(str(choice) + joiner, "")
                    text += str(choice) + joiner
                else:
                    break
                weight *= next_multiply
        except Exception as e:
            debug_print(e)
            raise Exception(f"getChained error {variable} {e}")
        return text.strip()

    # call from modules.prompt_v2 import prompt_formula_v2
    def getValue(self, variable):
        if self.compute is None:
            raise Exception("compute is None")
        compute = self.compute
        try:
            from modules.prompt_v2 import text_formula_v2

            variable = text_formula_v2(
                variable,
                args={
                    "variables": compute.variables,
                    "attributes": compute.attributes,
                    "chained_variables": compute.chained_variables,
                    "chained_attriblutes": compute.chained_attriblutes,
                },
            )
        except Exception as e:
            debug_print(e)
            raise Exception(f"getValue error {variable} {e}")
        return variable

    def getAttribute(self, variable, key, choice=None):
        if self.compute is None:
            raise Exception("compute is None")
        compute = self.compute
        if isinstance(choice, float):
            if choice < 0.0:
                choice = 0.0
            if choice > 1.0:
                choice = 1.0
            from modules.prompt_v2 import choice_v2

            _, attribute = choice_v2(compute.chained_variables[variable], choice)
            if attribute is None:
                attribute = {}
            if key in attribute:
                return attribute[key]
            return None

        if variable in compute.attributes:
            if key in compute.attributes[variable]:
                return compute.attributes[variable][key]
        return None

    def getChoiceIndex(self, variable, choice, index=1):
        if self.compute is None:
            raise Exception("compute is None")
        compute = self.compute
        from modules.prompt_v2 import choice_v2

        try:
            choiced, _attribute = choice_v2(compute.chained_variables[variable], choice)
        except Exception as e:
            debug_print(e)
            raise Exception(f"getChoiceIndex error {variable} {choice} {e}")
        return choiced[index - 1]

    def getChoiceAttribute(self, variable, choice, attribute):
        if self.compute is None:
            raise Exception("compute is None")
        compute = self.compute
        from modules.prompt_v2 import choice_v2

        try:
            choiced, attributes = choice_v2(compute.chained_variables[variable], choice)
            if attributes is None:
                attributes = {}
        except Exception as e:
            debug_print(e)
            raise Exception(f"getChoiceAttribute error {variable} {choice} {e}")
        if attribute in attributes:
            return attributes.get(attribute, None)
        return None
