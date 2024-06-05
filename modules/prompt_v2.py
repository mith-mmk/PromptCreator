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


def text_formula_v2(text, variables, error_info=""):
    compute = FormulaCompute()

    formulas = re.findall(r"\$\{\=(.+?)\}", text)
    for formula in formulas:
        replace_text = compute.getCompute(formula, variables)
        if replace_text is not None:
            text = text.replace("${=" + formula + "}", str(replace_text))
        else:
            error = compute.getError()
            Logger.error(f"Error happen formula {error_info} {formula}, {error}")
    simple_formulas = re.findall(r"\$\{(.+?)\}", text)

    for formula in simple_formulas:
        _formula = formula.strip()
        # v1 formula
        if re.match(r"(.+?)\,(\d+)", _formula):
            # array formula
            try:
                array_formula = re.match(r"(.+?)\,(\d+)", formula)
                variable = array_formula.group(1)
                array_index = int(array_formula.group(2)) - 1
                replace_text = variables.get(variable, "")[array_index]
            except Exception as e:
                Logger.verbose(f"Error happen array formula {error_info} {formula} {e}")
                replace_text = ""
            text = text.replace("${" + formula + "}", replace_text)
        # v2 formula
        elif re.match(r"(.+?)\S*\[\S*(\d+)\*\]", _formula):
            # array formula
            array_formula = re.match(r"(.+?)\S*\[\S*(\d+)\*\]", formula)
            variable = array_formula.group(1)
            array_index = int(array_formula.group(2))
            try:
                replace_text = variables.get(variable, "")[array_index]
            except Exception as e:
                Logger.verbose(f"Error happen array formula {error_info} {formula} {e}")
                replace_text = ""
            text = text.replace("${" + formula + "}", replace_text)
        else:
            # simple formula
            try:
                replace_text = variables.get(formula, [""])[0]
            except Exception as e:
                Logger.verbose(
                    f"Error happen simple formula {error_info} {formula} {e}"
                )
            text = text.replace("${" + formula + "}", replace_text)
    return text


# in test
def prompt_formula_v2(new_prompt, variables, info=None, error_info="", nested=0):
    try:
        if info is not None:
            for key, item in info.items():
                variables[f"info:{key}"] = item
    except Exception as e:
        Logger.error(f"Error happen info {info}, {error_info}")
        Logger.error(e)

    if type(new_prompt) is str:
        return text_formula_v2(new_prompt, variables, error_info)
    elif type(new_prompt) is dict:
        for key in new_prompt:
            # verbose は変換しない
            if key == "verbose":
                continue
            if type(new_prompt[key]) is str:
                new_prompt[key] = text_formula_v2(
                    new_prompt[key], variables, error_info
                )
            elif type(new_prompt[key]) is dict:
                for key2 in new_prompt[key]:
                    if type(new_prompt[key][key2]) is str:
                        new_prompt[key][key2] = text_formula_v2(
                            new_prompt[key][key2], variables, error_info
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
            new_prompt, variables, info=info, error_info=error_info, nested=nested
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
    if "options" in yml and "json" in yml["options"] and yml["options"]["json"]:
        mode = "json"

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
    prompts = ""

    if mode == "text":
        for key, item in command.items():
            if type(item) is str:
                prompts = prompts + "--" + key + ' "' + item + '" '
            else:
                prompts = prompts + "--" + key + " " + str(item) + " "
    elif mode == "json":
        prompts = command
    return yml


def read_file_v2(filename, error_info=""):
    strs = []
    filenames = filename.split()
    for filename in filenames:
        try:
            # extention is ct2 ?
            ext = os.path.splitext(filenames[0])[-1:][0]
            if ext == ".ct2":
                with open(filename, "r", encoding="utf_8") as f:
                    for idx, item in enumerate(f.readlines()):
                        item = item_split_ct2(
                            item, error_info=f"{error_info} {filename} {idx}"
                        )
                        strs.append(item)
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
        return {"variable": [str(item)], "weight": default_weight}
    item = item.replace("\n", " ").strip().replace(r"\;", r"${semicolon}")
    split = item.split(";")

    if type(split) is list:
        for i in range(0, len(split)):
            split[i] = split[i].replace(r"${semicolon}", ";")
    try:
        weight = float(split[0])
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


def prompt_replace(object, replace_texts, var):
    # key ごとに検索
    for key in object:
        if type(object[key]) is str:
            object[key] = object[key].replace("${variable}", var)
        elif type(object[key]) is dict:
            object[key] = prompt_replace(object[key], replace_texts, var)
    return object


def prompt_multiple_v2(yml, variable, array, input=[]):
    output = [None] * len(array) * len(input) if len(input) > 0 else [None] * len(array)
    i = 0
    for item in enumerate(input):
        for item in array:
            output[i] = {}
            for key in yml["command"]:
                output[i][key] = yml["command"][key]
            verbose = {}
            for key in yml["info"]:
                verbose = yml["info"][key]
            for key in yml["array"]:
                verbose = yml["array"][key]
            output[i] = verbose
            # ${variable} を置換
            output[i] = prompt_replace(output[i], item, variable)
            i = i + 1
    return output


# [
# {weight: 0.1, variables: ["red", "blue"]},
# {weight: 0.2, variables: ["green", "yellow"]},
# ]
def weight_calc_v2(variable, default_weight=0.1):
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
    for item in array:
        try:
            if item["choice_start"] <= choice < item["choice_end"]:
                return item["variables"]
        except Exception as e:
            Logger.error(f"Error happen choice_v2 {array}")
            Logger.error(e)
            raise e
    return ""


def prompt_random_v2(yml, max_number, input=[]):
    weighted_variables = {}
    if not yml.get("weight_calced"):
        Logger.debug("weight calc")
        appends = yml.get("variables", {})
        keys = list(appends.keys())
        for key in keys:
            try:
                Logger.debug(f"process weight calc {key}")
                weighted = weight_calc_v2(appends[key])
                weighted_variables[key] = weighted
            except Exception as e:
                Logger.error(f"Error happen weight calc {key}")
                Logger.error(e)
                raise e
        yml["weighted_variables"] = weighted_variables
        yml["weight_calced"] = True

    Logger.debug(f"prompt_random_v2 {max_number}")
    variables = yml.get("weighted_variables", {})
    Logger.debug(f"variables {variables}")

    current_variables = {}
    for key in variables:
        current_variables[key] = choice_v2(variables[key])
    Logger.debug("choice end")

    if len(input) == 0:
        output = [None] * max_number
    else:
        output = input

    for idx, current in enumerate(output):
        Logger.debug(f"prompt_random_v2 {idx}")
        if current is None:
            current = {}
            # yml commands を コピー
            Logger.debug("deep copy command")
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
        current = prompt_formula_v2(current, current_variables, None, error_info="")
        current["verbose"] = verbose
        current.get("verbose", {})["variables"] = current_variables
        Logger.debug(f"current {current}")
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
    override = expand_arg_v2(opt.get("override"))
    info = expand_arg_v2(opt.get("info"))
    Logger.debug(f"override {override}")
    Logger.debug(f"info {info}")
    Logger.debug(f"json {opt.get('json')}")
    if opt.get("json") or opt.get("api_mode"):
        mode = "json"
    else:
        mode = "text"

    prompt_file = opt.get("input")
    output = opt.get("output")
    verbose = opt.get("verbose_json", False)
    ext = os.path.splitext(prompt_file)[-1:][0]
    yml = {
        "version": 2,
        "options": {
            "output": output,
            "json": mode,
            "verbose": verbose,
            "api_mode": opt.get("api_mode"),
        },
        "command": {},
        "info": {},
        "variables": {},
        "methods": [],
        "array": {},
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
    set_reserved(yml["variables"])

    Logger.debug(f"info {info}")
    # console mode is dispose

    options = yml["options"]
    yml["weight_calced"] = False
    output = []

    variables = yml.get("variables", {})
    for key, item in variables.items():
        Logger.debug(f"key {key}")
        if type(item) is str:
            variables[key] = read_file_v2(item, error_info=f"variables {key}")
        elif type(item) is list:
            for i, txt in enumerate(item):
                variables[key][i] = item_split_txt(
                    txt, error_info=f"variables {key} {i}"
                )
        Logger.debug(f"variables {key} {variables[key]}")

    if "methods" not in yml:
        Logger.error("Yaml parse error, 'methods' is not found")
        raise NotImplementedError

    for method in yml.get("methods", []):
        key = list(method.keys())[0]
        Logger.debug(f"method {key}")
        if key == "random":
            max_number = method.get(key, options.get("number", 10))
            Logger.debug(f"max_number {max_number}")
            if max_number == 0:
                max_number = options.get("number", 10)
            try:
                max_number = int(max_number)
            except ValueError:
                Logger.error(f"Error happen random number {max_number}")
                max_number = 10
            Logger.debug(f"create random {max_number}")
            output = prompt_random_v2(yml, max_number, output)
        elif key == "multiple":
            variable = method["multiple"]
            array = yml.get("array", [])
            Logger.debug("multiple")
            output = prompt_multiple_v2(yml, variable, array, output)

    Logger.debug(f"output {output}")
    mode = "json" if yml.get("options", {}).get("json") else "text"

    if mode == "text":
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
                text = text + " --" + key + " " + item[key]
            output_text = output_text + text + "\n"
        return {
            "options": options,
            "yml": yml,
            "output_text": output_text,
            "mode": mode,
        }
    else:
        return {"options": options, "yml": yml, "output_text": output, "mode": mode}