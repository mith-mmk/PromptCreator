import copy
import json
import os
import random
import re

import yaml

from modules.callback_function import CallbackFunctions as Callback
from modules.formula import FormulaCompute
from modules.logger import getDefaultLogger
from modules.prompt import set_reserved

Logger = getDefaultLogger()

# v2 yaml formula
# # create text v2 yaml
# version:2 # > upto v2
# base_yaml: base.yaml # if base_yaml is exist, merge base_yaml and yaml
# options:
#   sd_model: sdxl   # set default model
#   vae: sdxl_vae.safetensors # set default vae
#   output: output.txt # set default output
#   number: 100 # set default random number
#   #  weight: # dispose
#   #  default_weight: # dispose only use 0.1
#   json: true # output json or text: true
#   verbose: true # verbose mode (with output variables)
#   api_mode: true # dispose
# # appends: # dispose
# variables:
#   do: do.ct2   # use create text v2 format
#   chars: chars.txt # use text format
#   color: color.json # use json format
#   day: ["0.1;night", "0.1;day"] # use inline format, cv1 format
#   number: # use cv2 format
#        - '["1","-1"],0.1,width:640,height:480'
#        - '["2","-2"],0.1'
#   json:  # use json format
#        variables: ["1","2"]
#        weight: 0.1
#        options: 1
# array:
# methods:
#   random: 100 # 0 is use max number

# commands:


def text_formula_v2(text, args):
    variables = args.get("variables", {})
    error_info = args.get("error_info", "")
    attributes = args.get("attributes", {})
    chained_var = args.get("chained_var", {})
    chained_attr = args.get("chained_attr", {})
    excludes = args.get("excludes", [])
    # Logger.debug(f"text_formula_v2 {text}")
    # Logger.debug(f"attributes {attributes}")

    compute = FormulaCompute()
    callback = Callback(compute)
    callback.setChainedVariables(chained_var, chained_attr)
    compute.setCallback(callback)
    compute.setVersion(2)
    formulas = re.findall(r"\$\{\=(.+?)\}", text)
    for formula in formulas:
        callback.setVariables(variables, attributes)
        replace_text = compute.getCompute(formula, variables, attributes)

        if replace_text is not None:
            text = text.replace("${=" + formula + "}", str(replace_text))
        else:
            error = compute.getError()
            raise Exception(f"Error happen formula {error_info} {formula}, {error}")
            # Logger.error(f"Error happen formula {error_info} {formula}, {error}")
            # return text
    simple_formulas = re.findall(r"\$\{(.+?)\}", text)
    # Logger.debug(f"simple_formulas {simple_formulas}")
    for formula in simple_formulas:
        _formula = formula.strip()
        # v1 formula ${variable,n} n = 1, 2, 3, ...
        # ${variable,n}  | ${variable[1]}
        if re.match(r"([a-zA-Z\-\_]?)\,(\d+)", _formula):
            # array formula
            try:
                array_formula = re.match(r"(.+?)\,(\d+)", formula)
                if array_formula is not None:
                    variable = array_formula.group(1)
                    array_index = int(array_formula.group(2)) - 1
                if variable in excludes:
                    continue
                if variable in variables:
                    try:
                        replace_text = variables.get(variable)[array_index]
                        text = text.replace("${" + formula + "}", str(replace_text))
                    except Exception:
                        Logger.verbose(
                            f"{formula} index {array_index} is not, set use empty in {text}"
                        )
                        text = text.replace("${" + formula + "}", "")
            except Exception as e:
                Logger.verbose(f"Error happen array formula {error_info} {formula} {e}")
        # v2 formula
        elif re.match(r"([a-zA-Z\-\_].*?)\s*\[\s*(\d+)\s*\]", _formula):
            # array formula ${variable[n]} n = 0, 1, 2, ...
            array_formula = re.match(r"(.+?)\s*\[\s*(\d+)\s*\]", formula)
            if array_formula is not None:
                variable = array_formula.group(1)
                array_index = int(array_formula.group(2)) - 1
            if variable in excludes:
                continue
            try:
                if variable in variables:
                    try:
                        replace_text = variables.get(variable, "")[array_index]
                        text = text.replace("${" + formula + "}", str(replace_text))
                    except Exception:
                        Logger.verbose(
                            f"{formula} index {array_index} is not, set use empty in {text}"
                        )
                        text = text.replace("${" + formula + "}", "")
            except Exception as e:
                Logger.verbose(f"Error happen array formula {error_info} {formula} {e}")
        # dict formula ${variable["key"]}
        elif re.match(
            r"([a-zA-Z\-\_].*?)\s*\[\s*\"(.+?)\"\s*\]|([a-zA-Z\-\_].*?)\s*\[\s*\'(.+?)\'\s*\]",
            _formula,
        ):
            dict_formula = re.match(
                r"(.+?)\s*\[\s*\"(.+?)\"\s*\]|([a-zA-Z\-\_].*?)\s*\[\s*\'(.+?)\'\s*\]",
                formula,
            )
            if dict_formula is not None:
                variable = dict_formula.group(1) or dict_formula.group(3)
                key = dict_formula.group(2) or dict_formula.group(4)
            Logger.debug(f"dict formula {variable} {key}")
            if variable in excludes:
                continue
            if variable in variables:
                try:
                    attribute = attributes.get(variable, {})
                    replace_text = attribute.get(key, None)
                    if replace_text is None:
                        Logger.warning(
                            f"variable {variable} not has '{key}', use empty"
                        )
                        replace_text = ""
                    text = text.replace("${" + formula + "}", str(replace_text))
                except Exception as e:
                    Logger.error(f"Error happen dict formula {formula} {e}")
            else:
                pass
                # Logger.error(f"Error happen dict formula {formula}")
        else:
            # simple formula ${variable}
            if formula in variables:
                if formula in excludes:
                    continue
                try:
                    replace_text = variables.get(formula)[0]
                    text = text.replace("${" + formula + "}", replace_text)
                except Exception:
                    Logger.error(f"Error happen simple formula illegal {formula}")
    return text


def nested_prompt_formula_v2(items, args):
    if items is None:
        return None
    if type(items) is str:
        return text_formula_v2(items, args)
    elif isinstance(items, float) or isinstance(items, int):
        return items
    elif type(items) is dict:
        for key in items:
            if type(items[key]) is str:
                items[key] = text_formula_v2(items[key], args)
            elif type(items[key]) is dict:
                items[key] = nested_prompt_formula_v2(items[key], args)
            elif type(items[key]) is list:
                for i, item in enumerate(items[key]):
                    if type(item) is str:
                        items[key][i] = text_formula_v2(item, args)
                    elif type(item) is dict:
                        items[key][i] = nested_prompt_formula_v2(item, args)
    elif type(items) is list:
        for i, item in enumerate(items):
            if type(item) is str:
                items[i] = text_formula_v2(item, args)
            elif type(item) is dict:
                items[i] = nested_prompt_formula_v2(item, args)
    else:
        raise Exception(f"Error happen nested_prompt_formula_v2 {type(items)}, {items}")
    return items


# in test
def prompt_formula_v2(
    new_prompt, variables, opt={}, error_info="", nested=0, attributes={}, excludes=[]
):
    try:
        if nested == 0:
            info = opt.get("info", {})
            for key, item in info.items():
                variables[f"info:{key}"] = item
    except Exception as e:
        Logger.error(f"Error happen info get info {info}, {error_info}")
        Logger.error(e)

    args = {
        "variables": variables,
        "error_info": error_info,
        "attributes": attributes,
        "chained_var": opt.get("weighted_variables", {}),
        "chained_attr": opt.get("attributes", {}),
        "excludes": excludes,
    }

    if type(new_prompt) is str:
        return text_formula_v2(new_prompt, args)
    elif isinstance(new_prompt, float) or isinstance(new_prompt, int):
        return new_prompt
    elif type(new_prompt) is dict:
        for key in new_prompt:
            # verbose は変換しない
            if key == "verbose":
                continue
            if type(new_prompt[key]) is str:
                new_prompt[key] = text_formula_v2(new_prompt[key], args)
            elif type(new_prompt[key]) is dict:
                new_prompt[key] = nested_prompt_formula_v2(new_prompt[key], args)
            elif type(new_prompt[key]) is list:
                new_prompt[key] = nested_prompt_formula_v2(new_prompt[key], args)
    elif type(new_prompt) is list:
        new_prompt[key] = nested_prompt_formula_v2(new_prompt[key], args)
    # シリアライズして ${.*?}があるか探す
    json_str = json.dumps(new_prompt)
    formulas = re.findall(r"\$\{(.+?)\}", json_str)
    # あれば再帰する
    if len(formulas) > 0:
        error_info = error_info.replace(" nested formula " + str(nested), "")
        nested = nested + 1
        error_info = error_info + " nested formula " + str(nested)
        if nested > 10:  # arrayの場合があるので10回まで
            return new_prompt
        new_prompt = prompt_formula_v2(
            new_prompt,
            variables,
            opt=opt,
            error_info=error_info,
            nested=nested,
            attributes=attributes,
        )
    return new_prompt


def update_nested_dict(original_dict, new_dict):
    for key, value in new_dict.items():
        if (
            isinstance(value, dict)
            and key in original_dict
            and isinstance(original_dict[key], dict)
        ):
            update_nested_dict(original_dict[key], value)
        else:
            original_dict[key] = value
    return original_dict


def recursive_yaml_load(filename):
    with open(filename, encoding="utf-8") as f:
        yml = yaml.safe_load(f)
    # if not v2 yaml error
    if "version" not in yml:
        Logger.error(f"File {filename} is not set version")
        raise NotImplementedError(f"File {filename} is not set version")
    if yml["version"] < 2:
        Logger.error(f"File {filename} is not v2 yaml")
        raise NotImplementedError(f"File {filename} is not v2 yaml")
    if "base_yaml" in yml:
        base_yaml = recursive_yaml_load(yml["base_yaml"])
        del yml["base_yaml"]
        yml = update_nested_dict(base_yaml, yml)
    return yml


def yaml_parse_v2(filename, opt={}):
    try:
        yml = recursive_yaml_load(filename)
    except FileNotFoundError:
        Logger.error(f"File {filename} is not found")
        raise FileNotFoundError(f"File {filename} is not found")
    except Exception as e:
        Logger.error(f"Error happen yaml {filename}")
        Logger.error(e)
        raise Exception(f"Error happen yaml {filename}")
    if "command" not in yml:
        yml["command"] = {}
    if "info" not in yml:
        yml["info"] = set_reserved({})

    command = yml.get("command", {})
    array = yml.get("array", {})
    override = yml.get("override", {})
    info = yml.get("info", {})

    if override is not None:
        for key, item in override.items():
            command[key] = item

    if info is not None:
        for key, item in info.items():
            yml["info"][key] = item
        array["$INFO"] = info

    return yml


def read_file_v2(filename, error_info=""):
    strs = []
    filenames = filename.split()
    for filename in filenames:
        Logger.debug(f"read_file_v2 {filename}")
        try:
            ext = os.path.splitext(filenames[0])[-1:][0]
            if re.match(r"(.+\.jsonl)\[(.+)\]", filename) or ext == ".jsonl":
                Logger.debug("load jsonl")
                if ext == ".jsonl":
                    query = "*"
                    queries = ["*"]
                else:
                    q = re.match(r"(.+\.jsonl)\[(.+)\]", filename)
                    if q is not None:
                        filename = q.group(1)
                        query = q.group(2)
                    queries = query.split(",")
                    # trim space
                    for i, q in enumerate(queries):
                        queries[i] = q.strip()
                Logger.debug(f"query {query}")
                with open(filename, "r", encoding="utf_8") as f:
                    all_text = f.read()
                    # /* */ を削除 \n をまたぐので注意
                    all_text = re.sub(r"/\*.*?\*/", "", all_text, flags=re.DOTALL)
                    lines = all_text.split("\n")
                    try:
                        for idx, item in enumerate(lines):
                            # comment out を削除
                            item = re.sub(r"\s*\/\/.*$", "", item)
                            # gg(f"line {idx + 1} item {item}")
                            if re.match(r"^\s*$", item):
                                continue
                            item = json.loads(item)
                            if item is None:
                                continue
                            # replace W => weight V => variables C => choice
                            if "W" in item:
                                item["weight"] = item.get("W", 0.1)
                                del item["W"]
                            else:
                                item["weight"] = 0.1
                            if "V" in item:
                                value = item.get("V", [])
                                if type(value) is not list:
                                    value = [value]
                                item["variables"] = value
                                del item["V"]
                            if "C" in item:
                                choice = item.get("C", [])
                                if isinstance(choice, str):
                                    choice = [choice]
                                item["choice"] = item.get("C", [])
                                del item["C"]
                                if isinstance(item.get("choice"), list):
                                    _query = ""
                                    for i, c in enumerate(item["choice"]):
                                        if isinstance(c, dict):
                                            keys = c.keys()
                                            for key in keys:
                                                if key in queries:
                                                    if _query != "":
                                                        _query = _query + "," + key
                                                        break
                                        if c != "*":
                                            if _query != "":
                                                _query = _query + "," + c
                                    item["query"] = _query.strip(",")

                            else:
                                item["choice"] = ["*"]
                            # Logger.debug(f"replaced item {item}")
                            choice = item.get("choice", ["*"])
                            if "choice" in item:
                                del item["choice"]
                            # queries にマッチするものを取り出す
                            for query in queries:
                                if "*" in choice or query == "*" or query in choice:
                                    strs.append(item)
                                else:  # keyを探す weight override
                                    for key in choice:
                                        if type(key) is not str:
                                            if query in key:
                                                Logger.debug(f"key {key}")
                                                item["weight"] = key[query]
                                                strs.append(item)
                                                break
                    except Exception as e:
                        Logger.error(
                            f"json decode error {filename} line{idx + 1} {item} {e}"
                        )
                Logger.debug(f"strs {strs}")
            elif ext == ".json":
                with open(filename, "r", encoding="utf_8") as f:
                    json_data = json.load(f)
                    if type(json_data) is list:
                        parsed = []
                        for item in json_data:
                            if "W" in item:
                                item["weight"] = item.get("W", 0.1)
                                del item["W"]
                            if "C" in item:
                                item["choice"] = item.get("C", [])
                                del item["C"]
                            if "V" in item:
                                item["variables"] = item.get("V", [])
                                del item["V"]
                            parsed.append(item)
                        strs.extend(parsed)
            else:
                with open(filename, "r", encoding="utf_8") as f:
                    for i, item in enumerate(f.readlines()):
                        if re.match(r"^\s*#.*", item) or re.match(r"^\s*$", item):
                            continue
                        item = re.sub(r"\s*#.*$", "", item)
                        try:
                            strs.append(item_split_txt(item))
                        except Exception:
                            Logger.error(
                                f"Error happen line {error_info} {filename} {i} {item}"
                            )
        except FileNotFoundError:
            Logger.error(f"{filename} is not found")
            raise FileNotFoundError(f"{filename} is not found")
    return strs


# create_prompt v2
def item_split_txt(item, error_info="", default_weight=0.1):
    if type(item) is not str:
        if type(item) is dict:
            item["variables"] = item.get("V", [])
            if item["variables"] is not list:
                item["variables"] = [item["variables"]]
            if "V" in item:
                del item["V"]
            item["weight"] = item.get("W", default_weight)
            if "W" in item:
                del item["W"]
            if "C" in item:
                del item["C"]
            return item
        Logger.warning(f"item {item} is not str {type(item)}")
        return {"variables": [str(item)], "weight": default_weight}
    item = item.replace("\n", " ").strip().replace(r"\;", r"${semicolon}")
    split = item.split(";")

    if type(split) is list:
        for i in range(0, len(split)):
            split[i] = split[i].replace(r"${semicolon}", ";")
    try:
        weight = float(split[0])
        if len(split) == 1:
            return {"weight": default_weight, "variables": [weight]}
    except ValueError:
        Logger.debug(f"weight convert error use defaut {error_info} {split[0]}")
        weight = default_weight
        return {"weight": weight, "variables": split}
    variables = split[1:]
    return {"weight": weight, "variables": variables}


def prompt_multiple_v2(yml, variable, array, input=[]):
    Logger.debug("prompt_multiple_v2 start")
    output = [{}] * len(array) * len(input) if len(input) > 0 else [{}] * len(array)
    i = 0
    if len(input) == 0:
        input = [copy.deepcopy(yml.get("command", {}))]
        Logger.debug(f"input {input}")

    for parts in input:
        for item in array:
            Logger.debug(f"prompt_multiple_v2 {item}")
            args = {}
            attributes = item.copy()
            del attributes["variables"]
            args[variable] = item.get("variables", [])
            Logger.debug(f"item {args}")
            if parts is None:
                parts = {}
            output[i] = copy.deepcopy(parts)
            verbose = output[i].get("verbose", {})
            if "variables" not in verbose:
                verbose["variables"] = {}
            verbose["variables"][variable] = item.get("variables", [])
            if attributes:
                if "attributes" not in verbose:
                    verbose["attributes"] = {}
                verbose["attributes"][variable] = attributes
            current = prompt_formula_v2(
                output[i], args, opt=yml, attributes={variable: attributes}
            )
            if isinstance(current, dict):
                value = item.get("variables", [])[0]
                Logger.debug(f"get value {value}")
                if "values" not in verbose:
                    verbose["values"] = {}
                verbose["values"][variable] = value
                output[i] = current
                output[i]["verbose"] = verbose
            else:
                raise Exception(
                    f"Error happen prompt_multiple_v2 return type{type(current)} {current}"
                )
            i = i + 1
    Logger.debug("prompt_multiple_v2 end")
    return output


# [
# {weight: 0.1, variables: ["red", "blue"]},
# {weight: 0.2, variables: ["green", "yellow"]},
# ]
def weight_calc_v2(variable, default_weight=0.1, key=""):
    # 0.0 - 0.1 に正規化する
    weight = 0.0
    weight_append = []
    for i, item in enumerate(variable):
        if "weight" in item:
            try:
                weight = weight + float(item["weight"])
            except ValueError:
                Logger.debug(f"float convert error append line {i} {item} use default")
                weight = weight + default_weight
        else:
            weight = weight + default_weight
    # 係数を計算
    if weight == 0.0:
        Logger.warning(f"key {key} all weight is 0.0, choise empty")
        weight_txt = {
            "choice_start": 0.0,
            "choice_end": 1.0,
            "variables": "",
        }
        weight_append = [weight_txt]
        return weight_append
    coef = 1.0 / weight
    weight = 0.0
    for i, item in enumerate(variable):
        start_weight = weight
        weight = item.get("weight", default_weight) * coef + weight
        if weight == 0.0:
            continue
        # deep copy item to variable
        keys = list(item.keys())
        weight_txt = {}
        for key in keys:
            weight_txt[key] = item[key]
        weight_txt["choice_start"] = start_weight
        weight_txt["choice_end"] = weight
        del weight_txt["weight"]
        weight_append.append(weight_txt)
    # Logger.debug(f"weight_calc_v2 {weight_append}")
    return weight_append


# {choice_start: 0, choice_end:0.1, variables: ["red", "blue"]}  0 =< choise < 0.1
def choice_v2(array, choice=None):
    if choice is None:
        choice = random.random()
    else:
        try:
            choice = float(choice)
        except ValueError:
            Logger.error("choice_v2 choice is not float")
            raise ValueError("choice_v2 choice is not float")
    # use binary search
    length = len(array)
    if length == 0:
        Logger.warning("choice_v2 array is empty")
        return []
    while length > 1:
        middle = int(length / 2)
        if choice < array[middle]["choice_start"]:
            array = array[:middle]
        else:
            array = array[middle:]
        length = len(array)
    attributes = None
    for key in array[0]:
        if key != "variables" and key != "choice_start" and key != "choice_end":
            if attributes is None:
                attributes = {}
            attributes[key] = array[0][key]
    Logger.debug(f"choice_v2 {array[0]}")
    return array[0]["variables"], attributes


def calc_weighted_variables(yml):
    weighted_variables = {}
    if not yml.get("weight_calced"):
        appends = yml.get("variables", {})
        keys = list(appends.keys())
        for key in keys:
            try:
                weighted = weight_calc_v2(appends[key], key=key)
                weighted_variables[key] = weighted
            except Exception as e:
                Logger.error(f"Error happen weight calc {key}")
                Logger.error(e)
                raise Exception(f"Error happen weight calc {key}")
        yml["weighted_variables"] = weighted_variables
        yml["weight_calced"] = True
        if "verbose" in Logger.getPrintLevel():
            for key in weighted_variables:
                Logger.verbose(f"key {key}")
                for item in weighted_variables[key]:
                    weight = (item.get("choice_end") - item.get("choice_start")) * 100
                    item = copy.deepcopy(item)
                    del item["choice_start"]
                    del item["choice_end"]
                    Logger.verbose(f"weight {weight:.3f}% {item}")
    return yml


def prompt_random_v2(yml, max_number, input=[], pre_choice=[], excludes=[]):
    Logger.debug(f"prompt_random_v2 count max {max_number}")
    try:
        variables = yml.get("weighted_variables", {})
    except Exception as e:
        Logger.error(f"Error happen get weighted_variables {e}")
        raise Exception(f"Error happen get weighted_variables {e}")
    # Logger.debug(f"variables {variables}")

    if len(input) == 0:
        output = [None] * max_number
    else:
        output = input

    Logger.debug(f"prompt_random_v2 {output}")
    for idx, current in enumerate(output):
        Logger.debug(f"prompt_random_v2 {idx} {current}")
        if current is not None:
            current_variables = current.get("verbose", {}).get("variables", {})
            attributes = current.get("verbose", {}).get("attributes", {})
        else:
            current_variables = {}
            attributes = None
        Logger.debug(f"variables pre-choices")
        for key in pre_choice:
            parsed_choice = parced_choice(yml, key)
            current_variables[key] = parsed_choice["variables"]
            if "attributes" in parsed_choice:
                if attributes is None:
                    attributes = {}
                    attributes[key] = parsed_choice["attributes"]
        Logger.debug(f"variables choices")
        for key in variables:
            if key not in pre_choice:
                current_variables[key], attribute = choice_v2(variables[key])
                if attributes is None:
                    attributes = {}
                if attribute is not None:
                    attributes[key] = attribute
        Logger.debug(f"current check")
        if current is None:
            # yml commands を コピー
            current = copy.deepcopy(yml.get("command", {}))
            verbose = {}
            verbose["variables"] = {}
            verbose["array"] = {}
            # current_variables をコピー
            for key in current_variables:
                verbose["variables"][key] = current_variables[key]
            for key in yml.get("array", {}):
                verbose["array"][key] = yml["array"][key]
            # info をコピー
            for key in yml.get("info", {}):
                verbose[key] = yml["info"][key]
            Logger.debug(json.dumps(current, ensure_ascii=False, indent=4))
            current["verbose"] = verbose
            Logger.debug(f"copy current end")
        Logger.verbose(f"promt formula {idx}")
        try:
            Logger.debug(f"prompt_random_v2 {idx}")
            current = prompt_formula_v2(
                current,
                current_variables,
                opt=yml,
                error_info="",
                attributes=attributes,
                excludes=excludes,
            )
        except Exception as e:
            Logger.warning(f"Error happen prompt_formula_v2 {e}")
            Logger.debug(f"{current}")
        Logger.debug(f"prompt_random_v2 {idx} {current}")
        if isinstance(current, dict):
            Logger.debug(f"get verbose {current}")
            current.get("verbose", {})["variables"] = current_variables
            if attributes:
                current.get("verbose", {})["attributes"] = attributes
            values = copy.deepcopy(current_variables)
            values = prompt_formula_v2(
                values, current_variables, opt=yml, attributes=attributes
            )
            current.get("verbose", {})["values"] = values
        output[idx] = current
    return output


def parced_choice(yml, key):
    Logger.debug("parced_choice start")
    try:
        variables = yml.get("weighted_variables", {})
    except Exception as e:
        Logger.error(f"Error happen get weighted_variables {e}")
        raise Exception(f"Error happen get weighted_variables {e}")
    try:
        current_variable, attribute = choice_v2(variables[key])
        current_variable = copy.deepcopy(current_variable)
        attribute = copy.deepcopy(attribute)
    except Exception as e:
        Logger.error(f"Error happen choice_v2 {e}")
        raise Exception(f"Error happen choice_v2 {e}")
    # precalc
    for idx, value in enumerate(current_variable):
        try:
            value = text_formula_v2(
                value,
                {"variables": {key: current_variable}, "attributes": {key: attribute}},
            )
        except Exception as e:
            Logger.error(f"Error happen text_formula_v2 in parced_choice {value}")
            raise Exception(f"Error happen text_formula_v2 in parced_choice  {value}")
        current_variable[idx] = value
    if attribute is None:
        attribute = {}
    for key in attribute:
        value = attribute[key]
        attribute[key] = text_formula_v2(
            value,
            {"variables": {key: current_variable}, "attributes": {key: attribute}},
        )
    Logger.debug("parced_choice end")
    return {"variables": current_variable, "attributes": attribute}


def expand_arg_v2(args):
    array = None
    if args is not None:
        array = {}
        for arg in args:
            for col in arg.split(","):
                items = col.split("=")
                key = items[0].strip()
                item = "=".join(items[1:]).strip()
                array[key] = item
    return array


def create_text_v2(opt):
    profile = opt.get("profile")
    override = expand_arg_v2(opt.get("override"))
    option_max_number = opt.get("max_number", 0)
    Logger.debug(f"max_number {option_max_number}")
    info = expand_arg_v2(opt.get("info"))
    Logger.debug(f"override {override}")
    Logger.debug(f"info {info}")
    Logger.debug(f"json {opt.get('json')}")

    prompt_file = opt.get("input")
    output = opt.get("output")
    verbose = opt.get("json_verbose", False)
    Logger.debug(f"verbose {verbose}")
    ext = os.path.splitext(prompt_file)[-1:][0]
    is_json = opt.get("json", False) or opt.get("api_mode", False)
    yml = {
        "version": 2,
        "options": {
            "output": output,
            "json": is_json,
            "verbose": verbose,
            "api_mode": opt.get("api_mode"),
        },
        "command": {},
        "info": {},
        "variables": {},
        "methods": [],
        "array": {},
        "profiles": {},
    }

    if ext == ".yaml" or ext == ".yml":
        # yaml mode
        Logger.debug(f"yaml mode {prompt_file}")
        yml = yaml_parse_v2(prompt_file, yml)
        Logger.debug(f"yml {yml}")
    else:
        Logger.error(f"not support extention {ext}")
        # dispose text mode
        raise NotImplementedError(f"not support extention {ext}")

    Logger.debug("set reserved")
    if "variables" not in yml:
        yml["variables"] = {}
    set_reserved(yml["variables"])
    Logger.debug(f"info {info}")
    # console mode is dispose

    options = yml["options"]

    Logger.debug(f"profile {profile}")

    if profile:
        if profile in yml.get("profiles", {}):
            profile = yml["profiles"][profile]
            if "profile" in profile:  # deny nested profile
                del profile["profile"]
                Logger.error(f"nested profile is not support in {profile}")
            Logger.debug(f"override yml from profile {profile}")
            load_profile = profile.get("load_profile", [])
            Logger.debug(f"load_profile {load_profile}")
            if load_profile:
                if type(load_profile) is str:
                    load_profile = [load_profile]
                for profile_name in load_profile:
                    pre_profile = yml.get("profiles", {}).get(profile_name, {})
                    Logger.debug(f"pre_profile {pre_profile}")
                    yml = update_nested_dict(yml, pre_profile)
            yml = update_nested_dict(yml, profile)
        else:
            Logger.error(f"profile {profile} is not found")
            raise NotImplementedError(f"profile {profile} is not found")

    if isinstance(yml["command"], str):
        Logger.info(f"command loads from {yml['command']}")
        json_file = yml["command"]
        with open(json_file, "r", encoding="utf_8") as f:
            yml["command"] = json.load(f)

    options["output"] = (
        output if output is not None else options.get("output", "output.txt")
    )
    options["verbose"] = verbose if verbose else options.get("verbose", False)
    options["api_mode"] = (
        opt.get("api_mode") if opt.get("api_mode") else options.get("api_mode", False)
    )
    # Logger.debug(f"options {options}")
    yml["weight_calced"] = False

    Logger.debug("variables")
    variables = yml.get("variables", {})
    for key, item in variables.items():
        # Logger.debug(f"key {key}")
        if type(item) is str:
            variables[key] = read_file_v2(item, error_info=f"variables {key}")
        elif type(item) is list:
            # Logger.debug(f"type list item {item}")
            variables[key] = []
            for i, txt in enumerate(item):
                variables[key].append(
                    item_split_txt(txt, error_info=f"variables {key} {i}")
                )
        # Logger.debug(f"variables {key} {variables[key]}")

    Logger.debug("array")
    array = yml.get("array", {})

    for key, item in array.items():
        array[key] = []
        # Logger.debug(f"key {key}")
        if type(item) is str:
            array[key] = read_file_v2(item, error_info=f"array {key}")
        elif type(item) is list:
            # Logger.debug(f"type list item {item}")
            array[key] = []
            for i, txt in enumerate(item):
                array[key].append(
                    item_split_txt(txt, error_info=f"variables {key} {i}")
                )
    output = []

    calc_weighted_variables(yml)
    pre_choices = []
    excludes = []
    if "methods" not in yml:
        yml["methods"] = []
        yml["methods"].append({"random": 0})

    for method in yml.get("methods", []):
        Logger.debug(f"method {method}")
        try:
            key = list(method.keys())[0]
        except Exception as e:
            Logger.error(
                f"Error {method} is illigal syntax, write like 'random: 0' or 'multiple: variable'"
            )
            raise Exception(
                f"Error {method} is illigal syntax, write like 'random: 0' or 'multiple: variable'"
            )
        Logger.debug(f"method option {key}")
        if key == "random":
            Logger.debug(f"max_number is not set {option_max_number} {options}")
            if option_max_number < 0:
                max_number = method.get(key, options.get("max_number", 0))
                if max_number == 0:
                    max_number = options.get("number", max_number)
                try:
                    max_number = int(max_number)
                except ValueError:
                    Logger.error(f"Error happen random number {max_number}")
                    max_number = 10
            else:
                max_number = option_max_number
            Logger.debug(f"max_number {max_number}")
            try:
                output = prompt_random_v2(
                    yml, max_number, output, pre_choices, excludes
                )
                pre_choices = []
                excludes = []
            except Exception as e:
                Logger.error(f"Error happen prompt_random_v2 {e}")
                raise Exception(f"Error happen random {e}")
            excludes = []
        elif key == "multiple":
            multiple = method["multiple"]
            Logger.debug(f"multiple {multiple}")
            if type(multiple) is str:
                multiple = multiple.split(" ")

            for variable in multiple:
                array = yml.get("array", {}).get(variable, [])
                try:
                    output = prompt_multiple_v2(yml, variable, array, output)
                except Exception as e:
                    Logger.error(f"Error happen prompt_multiple_v2 {e}")
                    raise Exception(f"Error happen multiple {e}")
        elif key == "choice":
            Logger.debug(f"choice {method}")
            choices = method["choice"]
            if type(choices) is str:
                choices = choices.split(" ")

            pre_choices.extend(choices)
        elif key == "preset":
            Logger.debug(f"preset {method}")
            presets = method["preset"]
            if type(presets) is str:
                presets = presets.split(" ")
            for preset in presets:
                if preset not in variables:
                    Logger.error(f"preset {preset} is not found")
                    continue
                Logger.verbose(f"preset {preset}")
                weighted_variables = yml.get("weighted_variables", {})

                value, attributes = choice_v2(weighted_variables[preset])
                Logger.verbose(f"preset {preset} {value}")
                weighted_variables[preset] = [
                    {
                        "variables": value,
                        "choice_start": 0.0,
                        "choice_end": 1.0,
                    }
                ]
                if attributes is not None:
                    for attribute in attributes:
                        weighted_variables[preset][0][attribute] = attributes[attribute]

        elif key == "exclude":
            excludes = method["exclude"]
            if type(excludes) is str:
                excludes = excludes.split(" ")
            excludes.extend(excludes)
        elif key == "cleanup":
            Logger.debug(f"cleanup {method}")
            cleanup = method["cleanup"]
            if type(cleanup) is str:
                keys = cleanup.split(" ")
            Logger.debug(f"cleanup {keys}")
            if output is None:
                Logger.error(f"output is None")
                return None
            Logger.debug(f"cleanup {output}")
            for item in output:
                Logger.debug(f"cleanup {item}")
                for key in keys:
                    if key in item:
                        Logger.debug(f"cleanup {key} {item[key]}")
                        if key in item:
                            # remove space
                            item[key] = re.sub(r"\s+", " ", item[key])
                            # remove (,\s*)+ => ,
                            item[key] = re.sub(r"(,\s*)+", ",", item[key])
                            # remove space after ,
                            item[key] = re.sub(r"\s*,+\s*", ", ", item[key])
                            # remove space after (
                            item[key] = re.sub(r"\(\s*", "(", item[key])
                            # remove space before )
                            item[key] = re.sub(r"\s*\)", ")", item[key])
                            # remove space after [
                            item[key] = re.sub(r"\[\s*", "[", item[key])
                            # remove space before ]
                            item[key] = re.sub(r"\s*\]", "]", item[key])
                            # remove last , and space
                            item[key] = re.sub(r",\s*$", "", item[key])
                            # trim
                            item[key] = item[key].strip()
        else:
            Logger.error(f"method {key} is not support, skip")

    is_json = options.get("json", False)
    Logger.debug(f"is json {is_json}")

    if output is None:
        output = {}

    if not is_json:
        Logger.debug("text mode")
        output_text = ""
        for item in output:
            text = "--prompt "
            text = text + item.get("prompt", "")
            if "prompt" in item:
                del item["prompt"]
            if "verbose" in item:
                del item["verbose"]
            keys = list(item.keys())
            for key in keys:
                text = text + " --" + str(key) + " " + str(item[key])
            output_text = output_text + text + "\n"
        return {
            "options": options,
            "yml": yml,
            "output_text": output_text,
            "mode": "text",
        }
    else:
        Logger.debug("json mode")
        return {
            "options": options,
            "yml": yml,
            "output_text": output,
            "is_json": is_json,
        }
