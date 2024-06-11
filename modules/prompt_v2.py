import copy
import json
import os
import random
import re

import yaml

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


def text_formula_v2(text, variables, error_info="", attributes={}):
    compute = FormulaCompute()
    # Logger.debug(f"text_formula_v2 {text}")
    # Logger.debug(f"attributes {attributes}")

    formulas = re.findall(r"\$\{\=(.+?)\}", text)
    for formula in formulas:
        replace_text = compute.getCompute(formula, variables)
        if replace_text is not None:
            text = text.replace("${=" + formula + "}", str(replace_text))
        else:
            error = compute.getError()
            Logger.error(f"Error happen formula {error_info} {formula}, {error}")
    simple_formulas = re.findall(r"\$\{(.+?)\}", text)
    # Logger.debug(f"simple_formulas {simple_formulas}")
    for formula in simple_formulas:
        _formula = formula.strip()
        # v1 formula ${variable,n} n = 1, 2, 3, ...
        if re.match(r"(.+?)\,(\d+)", _formula):
            # array formula
            try:
                array_formula = re.match(r"(.+?)\,(\d+)", formula)
                variable = array_formula.group(1)
                array_index = int(array_formula.group(2)) - 1
                if variable in variables:
                    try:
                        replace_text = variables.get(variable)[array_index]
                        text = text.replace("${" + formula + "}", replace_text)
                    except Exception:
                        Logger.verbose(
                            f"{formula} index {array_index} is not, set use empty"
                        )
                        text = text.replace("${" + formula + "}", "")
            except Exception as e:
                Logger.verbose(f"Error happen array formula {error_info} {formula} {e}")
        # v2 formula
        elif re.match(r"(.+?)\s*\[\s*(\d+)\s*\]", _formula):
            # array formula ${variable[n]} n = 0, 1, 2, ...
            array_formula = re.match(r"(.+?)\s*\[\s*(\d+)\s*\]", formula)
            variable = array_formula.group(1)
            array_index = int(array_formula.group(2)) - 1
            try:
                if variable in variables:
                    try:
                        replace_text = variables.get(variable, "")[array_index]
                        text = text.replace("${" + formula + "}", replace_text)
                    except Exception:
                        Logger.verbose(
                            f"{formula} index {array_index} is not, set use empty"
                        )
                        text = text.replace("${" + formula + "}", "")
            except Exception as e:
                Logger.verbose(f"Error happen array formula {error_info} {formula} {e}")
        # dict formula ${variable["key"]}
        elif re.match(r"(.+?)\s*\[\s*\"(.+?)\"\s*\]", _formula):
            dict_formula = re.match(r"(.+?)\s*\[\s*\"(.+?)\"\s*\]", formula)
            variable = dict_formula.group(1)
            key = dict_formula.group(2)
            if variable in variables:
                try:
                    attribute = attributes.get(variable, {})
                    replace_text = attribute.get(key, None)
                    if replace_text is None:
                        Logger.warning(
                            f"varriable {variable} not has '{key}', use empty"
                        )
                        replace_text = ""
                    text = text.replace("${" + formula + "}", replace_text)
                except Exception:
                    Logger.error(f"Error happen dict formula {formula}")
            else:
                Logger.error(f"Error happen dict formula {formula}")
        else:
            # simple formula ${variable}
            if formula in variables:
                try:
                    replace_text = variables.get(formula)[0]
                    text = text.replace("${" + formula + "}", replace_text)
                except Exception:
                    Logger.error(f"Error happen simple formula illegal {formula}")
    return text


# in test
def prompt_formula_v2(
    new_prompt, variables, info=None, error_info="", nested=0, attributes={}
):
    try:
        if info is not None:
            for key, item in info.items():
                variables[f"info:{key}"] = item
    except Exception as e:
        Logger.error(f"Error happen info get info {info}, {error_info}")
        Logger.error(e)

    if type(new_prompt) is str:
        return text_formula_v2(new_prompt, variables, error_info, attributes)
    elif type(new_prompt) is dict:
        for key in new_prompt:
            # verbose は変換しない
            if key == "verbose":
                continue
            if type(new_prompt[key]) is str:
                new_prompt[key] = text_formula_v2(
                    new_prompt[key], variables, error_info, attributes
                )
            elif type(new_prompt[key]) is dict:
                for key2 in new_prompt[key]:
                    if type(new_prompt[key][key2]) is str:
                        new_prompt[key][key2] = text_formula_v2(
                            new_prompt[key][key2], variables, error_info, attributes
                        )
    # シリアライズして ${.*?}があるか探す
    json_str = json.dumps(new_prompt)
    formulas = re.findall(r"\$\{(.+?)\}", json_str)
    # あれば再帰する
    if len(formulas) > 0:
        nested = nested + 1
        error_info = error_info + " nested formula " + str(nested)
        if nested > 10:  # arrayの場合があるので10回まで
            return new_prompt
        new_prompt = prompt_formula_v2(
            new_prompt,
            variables,
            info=info,
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
        raise NotImplementedError
    if yml["version"] < 2:
        Logger.error(f"File {filename} is not v2 yaml")
        raise NotImplementedError
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
        raise FileNotFoundError
    except Exception as e:
        Logger.error(f"Error happen yaml {filename}")
        Logger.error(e)
        raise e
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
            if ext == ".ct2":
                with open(filename, "r", encoding="utf_8") as f:
                    for idx, item in enumerate(f.readlines()):
                        item = item_split_ct2(
                            item, error_info=f"{error_info} {filename} {idx}"
                        )
                        strs.append(item)
            # is <filename>.jsonl[(.+)] or <filename>.jsonl
            elif re.match(r"(.+\.jsonl)\[(.+)\]", filename) or ext == ".jsonl":
                Logger.debug("load jsonl")
                if ext == ".jsonl":
                    query = "*"
                    queries = ["*"]
                else:
                    q = re.match(r"(.+\.jsonl)\[(.+)\]", filename)
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
                            Logger.debug(f"line {idx + 1} item {item}")
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
                            else:
                                item["choice"] = ["*"]
                            Logger.debug(f"replaced item {item}")
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
                    strs.append(json.load(f))
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
            raise FileNotFoundError
    return strs


# create_prompt v2
def item_split_txt(item, error_info="", default_weight=0.1):
    if type(item) is not str:
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


# create_prompt v2
def item_split_ct2(item, error_info="", default_weight=0.1):
    # ["red,,","blue",""yellow"], 0.1, options: 1 => {"weight": 0.1, "variables": ["red,,"blue",""yellow"], "options": 1}
    # "" で括られている , は無視
    items = re.split(r'(?<!")\s*,\s*(?!")', item)
    weight = 0.1
    row = items[0].trim()
    # [] で括られている場合は json に変換
    if row[0] == "[" and row[-1] == "]":
        # array なので json に変換
        try:
            variables = json.loads(row)
        except json.JSONDecodeError:
            Logger.error(f"json decode error {error_info} {row}")
            variables = [row]
    else:  # 通常の文字列
        variables = [row]

    if len(items) >= 2:
        try:
            weight = float(items[1])
        except ValueError:
            Logger.debug(f"weight convert error use defaut {error_info} {items[1]}")
            weight = default_weight
    variables = {}
    if len(items) >= 3:  # json format without {}
        try:
            variables = json.loads("{" + items[2] + "}")
        except json.JSONDecodeError:
            Logger.error(f"json decode error {error_info} {items[2]}")
    variables["weight"] = weight
    variables["variables"] = items[0]
    return variables


def prompt_multiple_v2(yml, variable, array, input=[], attributes=None):
    Logger.debug("prompt_multiple_v2 start")
    output = [None] * len(array) * len(input) if len(input) > 0 else [None] * len(array)
    i = 0
    if len(input) == 0:
        input = [copy.deepcopy(yml.get("command", {}))]
        Logger.debug(f"input {input}")

    for parts in input:
        # Logger.debug(f"prompt_multiple_v2 {parts}")
        for item in array:
            args = {}
            args[variable] = item
            # Logger.debug(f"item {args}")
            output[i] = copy.deepcopy(parts)
            verbose = output[i].get("verbose", {})
            if "variables" not in verbose:
                verbose["variables"] = {}
            verbose["variables"][variable] = item
            if attributes:
                verbose["attributes"] = attributes
            output[i] = prompt_formula_v2(
                output[i], args, info=None, attributes=attributes
            )
            output[i]["verbose"] = verbose
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
def choice_v2(array):
    choice = random.random()
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
    return array[0]["variables"], attributes


def prompt_random_v2(yml, max_number, input=[]):
    weighted_variables = {}
    if not yml.get("weight_calced"):
        Logger.debug("weight calc")
        appends = yml.get("variables", {})
        keys = list(appends.keys())
        for key in keys:
            try:
                Logger.debug(f"process weight calc {key}")
                weighted = weight_calc_v2(appends[key], key=key)
                weighted_variables[key] = weighted
            except Exception as e:
                Logger.error(f"Error happen weight calc {key}")
                Logger.error(e)
                raise e
        yml["weighted_variables"] = weighted_variables
        yml["weight_calced"] = True

    # Logger.debug(f"prompt_random_v2 {max_number}")
    variables = yml.get("weighted_variables", {})
    # Logger.debug(f"variables {variables}")

    if len(input) == 0:
        output = [None] * max_number
    else:
        output = input

    for idx, current in enumerate(output):
        # Logger.debug(f"prompt_random_v2 {idx} {current}")
        current_variables = {}
        attributes = None
        for key in variables:
            current_variables[key], attribute = choice_v2(variables[key])
            if attribute is not None:
                if attributes is None:
                    attributes = {}
                attributes[key] = attribute
        if current is None:
            current = {}
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
            current["verbose"] = verbose
        current = prompt_formula_v2(
            current, current_variables, None, error_info="", attributes=attributes
        )
        current.get("verbose", {})["variables"] = current_variables
        if attributes:
            current.get("verbose", {})["attributes"] = attributes
        output[idx] = current
    return output


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
        raise NotImplementedError

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
            raise NotImplementedError

    options["output"] = (
        output if output is not None else options.get("output", "output.txt")
    )
    options["verbose"] = verbose if verbose else options.get("verbose", False)
    options["api_mode"] = (
        opt.get("api_mode") if opt.get("api_mode") else options.get("api_mode", False)
    )
    Logger.debug(f"options {options}")
    yml["weight_calced"] = False

    variables = yml.get("variables", {})
    for key, item in variables.items():
        Logger.debug(f"key {key}")
        if type(item) is str:
            variables[key] = read_file_v2(item, error_info=f"variables {key}")
        elif type(item) is list:
            Logger.debug(f"type list item {item}")
            variables[key] = []
            for i, txt in enumerate(item):
                variables[key].append(
                    item_split_txt(txt, error_info=f"variables {key} {i}")
                )
        Logger.debug(f"variables {key} {variables[key]}")

    Logger.debug("array")
    array = yml.get("array", {})

    for key, item in array.items():
        array[key] = []
        Logger.debug(f"key {key}")
        if type(item) is str:
            array[key] = read_file_v2(item, error_info=f"array {key}")
        elif type(item) is list:
            Logger.debug(f"type list item {item}")
            array[key] = []
            for i, txt in enumerate(item):
                array[key].append(
                    item_split_txt(txt, error_info=f"variables {key} {i}")
                )
        an_array = []
        for item in array[key]:
            an_array.append(item.get("variables", []))
        array[key] = an_array
    output = []
    if "methods" not in yml:
        yml["methods"] = []
        yml["methods"].append({"random": 0})

    for method in yml.get("methods", []):
        Logger.debug(f"method {method}")
        key = list(method.keys())[0]
        Logger.debug(f"method {key}")
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
            output = prompt_random_v2(yml, max_number, output)
        elif key == "multiple":
            multiple = method["multiple"]
            Logger.debug(f"multiple {multiple}")
            if type(multiple) is str:
                multiple = multiple.split(" ")
            for variable in multiple:
                array = yml.get("array", {}).get(variable, [])
                # Logger.debug(f"create multiple {variable} {array}")
                output = prompt_multiple_v2(yml, variable, array, output)
        elif key == "cleanup":
            Logger.debug(f"cleanup {method}")
            cleanup = method["cleanup"]
            if type(cleanup) is str:
                keys = cleanup.split(" ")
            Logger.debug(f"cleanup {keys}")
            for item in output:
                for key in keys:
                    if key in item:
                        Logger.debug(f"cleanup {key} {item[key]}")
                        if key in item:
                            # remove space
                            item[key] = re.sub(r"\s+", " ", item[key])
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

        else:
            Logger.error(f"method {key} is not support, skip")

    is_json = options.get("json", False)
    Logger.debug(f"is json {is_json}")

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
