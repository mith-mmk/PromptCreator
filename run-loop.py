#!/usr/bin/env python3
import csv
import datetime
import glob
import os
import random
import shutil
import subprocess
import time

import yaml

import create_prompts
# import logging
import img2img
import modules.logger as logger
import modules.share as share

# from modules.logger import Print

# FULL AUTOMATIC CRATE IMAGES FROM STABLE DIFFUSION script
# MIT License (C) 2023 mith@mmk

# Todo replace logger,logiing to Logger.py

# sample fuction call from create_prompts.py and img2img_from_args()

# API
HOST = "http://localhost:7860"

IMG2IMG_BASE = "./outputs/$retake/"
OUTPUT_DIR = "./outputs/"
IMG2IMG_OUTPUR_DIR = "./outputs/"
CONFIG_BASE = "./prompts/"

# LOG
LOG_PATH = "./log/runloop.log"
LOG_DAYS = 7

# MODEL BASE model clone from nas, if exists
MODEL_CLONE = False
MODEL_SRC = "test:/ai/models/"
MODEL_DEST = "/var/ai/models/"

PROMPT_BASE = "./prompts/"
CONFIG = CONFIG_BASE + "config.yaml"

PROMPT_PREFIX = "prompts-girls-"
PROMPT_EXCEPTION_PREFIX = "prompts-"
PROMPT_SUFFIX = ".yaml"

FOLDER_SUFFIX = "-images"

# CONFIG COMPATIBLE
MODEL_CSV = os.path.join(CONFIG_BASE, "models.csv")
PROMPT_CSV = os.path.join(CONFIG_BASE, "prompts.csv")
EXCEPTION_LIST = os.path.join(CONFIG_BASE, "prompts.txt")

# IMG2IMG DIRECTORIES
INPUT_DIR = os.path.join(IMG2IMG_BASE, "batch")
WORK_DIR = os.path.join(IMG2IMG_BASE, ".work")
INPUT_APPEND = os.path.join(IMG2IMG_BASE + "modified")
INPUT_MASK = os.path.join(IMG2IMG_BASE, "mask")
ENDED_DIR = os.path.join(IMG2IMG_BASE, "$end")

# DEFAULT OPTIONS
START_HOUR = 7
STOP_HOUR = 18
IMG2IMG_STEPS = 6
IMG2IMG_DENOSING_STRINGTH = 0.6
IMG2IMG_N_ITER = 1
IMG2IMG_BATCH_SIZE = 1

ABORT_MATRIX = {
    "BOTH": ["sfw", "nsfw"],
    "SFW": ["sfw"],
    "NSFW": ["nsfw"],
    "XL": ["xl", "xl-sfw", "xl-nsfw"],
    "XLSFW": ["xl-sfw"],
    "XLNSFW": ["xl-nsfw"],
    "SKIP": None,
}

DefaultLogger = logger.getDefaultLogger()
Logger = logger.getLogger("run-loop")


def arg_split(args):
    results = []
    csv_reader = csv.reader([args], delimiter=" ")
    for row in csv_reader:
        results.extend(row)
    return results


def load_models_csv(filename):
    # file check
    if not (os.path.exists(filename)):
        return []
    models = []
    with open(filename) as f:
        reader = csv.reader(f)
        # model_name,vae,mode,
        for row in reader:
            model = {
                "model_name": row[0],
                "vae": row[1],
                "mode": row[2],
            }
            models.append(model)
    return models


def load_prompts_csv(filename):
    if not (os.path.exists(filename)):
        return []
    prompts = []
    with open(PROMPT_CSV) as f:
        reader = csv.reader(f)
        # prompt_name,folder,number,genre,
        for row in reader:
            if len(row) < 4:
                continue
            prompt = {
                "prompt_name": row[0],
                "folder": row[1],
                "number": row[2],
                "genre": row[3],
                "file_pattern": row[4],
            }
            prompts.append(prompt)
    return prompts


def load_not_default(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            not_girls = f.read().splitlines()
        return not_girls
    else:
        return []


def set_txt2img_config(config, yaml_config):
    txt2img = config["txt2img"]
    if "txt2img" in yaml_config:
        txt_config = yaml_config["txt2img"]
    else:
        txt_config = {}
    if "info" in txt_config:
        txt2img["info"] = txt_config["info"]
    if "output" in txt_config:
        txt2img["output"] = txt_config["output"]
    if "overrides" in txt_config:
        txt2img["overrides"] = txt_config["overrides"]
    if "direct_call" in txt_config:
        txt2img["direct_call"] = txt_config["direct_call"]
    if "prompts" in txt_config:
        if type(txt_config["prompts"]) is str:
            txt2img["prompts"] = load_prompts_csv(txt_config["prompts"])
        else:
            prompts = []
            for prompt in txt_config["prompts"]:
                [prompt_name, folder, number, genre, file_pattern] = prompt.split(
                    ","
                )
                prompt = {
                    "prompt_name": prompt_name,
                    "folder": folder,
                    "number": number,
                    "genre": genre,
                    "file_pattern": file_pattern,
                }
                prompts.append(prompt)
            txt2img["prompts"] = prompts
    if "abort_matrix" in txt_config:
        txt2img["abort_matrix"] = txt_config["abort_matrix"]
    if "coef_matrix" in txt_config:
        txt2img["coef_matrix"] = txt_config["coef_matrix"]
    if "folder_suffix" in yaml_config:
        config["folder_suffix"] = yaml_config["folder_suffix"]
    if "prefix" in txt_config:
        prefix = txt_config["prefix"]
        if "default" in prefix:
            txt2img["prefix"]["default"] = prefix["default"]
        if "exception" in prefix:
            txt2img["prefix"]["exception"] = prefix["exception"]
        if "exception_list" in prefix:
            txt2img["prefix"]["exception_list"] = prefix["exception_list"]
        if "suffix" in prefix:
            txt2img["prefix"]["suffix"] = prefix["suffix"]
    if "models" in txt_config:
        if type(txt_config["models"]) is str:
            txt2img["models"] = load_models_csv(txt_config["models"])
        else:
            list = txt_config["models"]
            models = []
            for model in list:
                [model_name, vae, mode] = model.split(",")
                model = {
                    "model_name": model_name,
                    "vae": vae,
                    "mode": mode,
                }
                models.append(model)
            txt2img["models"] = models


# replace config from default config to load config
def replace_config(use_config, load_config, parent=None):
    if type(load_config) is dict:
        keys = load_config.keys()
        for key in keys:
            if type(load_config[key]) is dict:
                if key not in use_config:
                    use_config[key] = load_config[key]
                elif type(use_config[key]) is not dict:
                    use_config[key] = load_config[key]
                else:
                    replace_config(use_config[key], load_config[key], key)
            elif type(load_config[key]) is list:
                use_config[key] = load_config[key]
            else:
                try:
                    use_config[key] = load_config[key]
                except Exception as e:
                    Logger.error(f"replace error {e} {key} {load_config[key]}")


# build default config
def default_config():
    prefix = {
        "default": PROMPT_PREFIX,
        "exception": PROMPT_EXCEPTION_PREFIX,
        "exception_list": EXCEPTION_LIST,
        "suffix": PROMPT_SUFFIX,
    }
    txt2img = {
        "prompts": None,
        "prompt_base": PROMPT_BASE,
        "output": OUTPUT_DIR,
        "models": None,
        "prefix": prefix,
        "abort_matrix": ABORT_MATRIX,
        "coef_matrix": [],
        "folder_suffix": FOLDER_SUFFIX,
        "overrides": "",
        "info": "",
        "direct_call": False,
    }
    image_dirs = {
        "input": INPUT_DIR,
        "work": WORK_DIR,
        "append": INPUT_APPEND,
        "mask": INPUT_MASK,
        "ended": ENDED_DIR,
        "output": IMG2IMG_OUTPUR_DIR,
        "folder_suffix": FOLDER_SUFFIX,
    }
    img2img = {
        "steps": IMG2IMG_STEPS,
        "denosing_strength": IMG2IMG_DENOSING_STRINGTH,
        "n_iter": IMG2IMG_N_ITER,
        "batch_size": IMG2IMG_BATCH_SIZE,
        "file_pattern": "[num]-[seed]",
        "dir": image_dirs,
        "direct_call": False,
    }
    img2txt2img = {
        "models": None,
        "overrides": "",
        "input": INPUT_DIR,
        "output": OUTPUT_DIR,
        "folder_suffix": FOLDER_SUFFIX,
        "overrides": "",
    }
    log = {
        "path": LOG_PATH,
        "days": LOG_DAYS,
        "level": "info",
    }
    clone = {
        "clone": MODEL_CLONE,
        "src": MODEL_SRC,
        "dest": MODEL_DEST,
        "folders": ["Stable-Diffusion", "Lora", "embeddings", "vae"],
    }
    loop = {
        "mode": False,
        "loop_count": 0,
        "commands": ["clone", "check", "ping", "txt2img", "img2img", "sleep 1"],
    }
    config = {
        "host": HOST,
        "prompt_base": PROMPT_BASE,
        "start_hour": START_HOUR,
        "stop_hour": STOP_HOUR,
        "txt2img": txt2img,
        "img2img": img2img,
        "img2txt2img": img2txt2img,
        "log": log,
        "clone": clone,
        "custom": {},  # dispose custom
        "loop": loop,
        "direct_call": True,
    }
    return config


# loopごとに読み直す
def load_config(config_file):
    config = default_config()
    txt2img = config["txt2img"]
    # CONFIG ファイルがない場合
    if not os.path.exists(config_file):
        txt2img["prompts"] = load_prompts_csv(PROMPT_CSV)
        txt2img["models"] = load_models_csv(MODEL_CSV)
        txt2img["exception_list"] = load_not_default(EXCEPTION_LIST)
        config["txt2img"] = txt2img
        return config

    with open(config_file, "r", encoding="utf-8") as f:
        yaml_config = yaml.safe_load(f)

        replace_config(config, yaml_config)
        set_txt2img_config(config, yaml_config)
        """
        if "host" in yaml_config:
            config["host"] = yaml_config["host"]
        if "promppt_base" in yaml_config:
            config["prompt_base"] = yaml_config["prompt_base"]
        if "schedule" in yaml_config:
            schedule = yaml_config["schedule"]
            if "start" in schedule:
                config["start_hour"] = schedule["start"]
            if "stop" in yaml_config["schedule"]:
                config["stop_hour"] = schedule["stop"]
        if "loop" in yaml_config:
            loop_config = yaml_config["loop"]
        else:
            loop_config = {}
        if "mode" in loop_config:
            config["loop"]["mode"] = loop_config["mode"]
        if "loop_count" in loop_config:
            config["loop"]["loop_count"] = loop_config["loop_count"]
        if "commands" in loop_config:
            config["loop"]["commands"] = loop_config["commands"]

        if "clone" in yaml_config:
            clone = config["clone"]
            clone_config = yaml_config["clone"]
            if "clone" in clone:
                clone["clone"] = clone_config["clone"]
            if "src" in clone:
                clone["src"] = clone_config["src"]
            if "dest" in clone:
                clone["dest"] = clone_config["dest"]
            if "folders" in clone:
                clone["folders"] = clone_config["folders"]
        if "txt2img" in yaml_config:
            txt_config = yaml_config["txt2img"]
        else:
            txt_config = {}

        if "info" in txt_config:
            txt2img["info"] = txt_config["info"]

        if "output" in txt_config:
            txt2img["output"] = txt_config["output"]

        if "overrides" in txt_config:
            txt2img["overrides"] = txt_config["overrides"]

        if "direct_call" in txt_config:
            txt2img["direct_call"] = txt_config["direct_call"]

        if "prompts" in txt_config:
            if type(txt_config["prompts"]) is str:
                txt2img["prompts"] = load_prompts_csv(txt_config["prompts"])
            else:
                prompts = []
                for prompt in txt_config["prompts"]:
                    [prompt_name, folder, number, genre, file_pattern] = prompt.split(
                        ","
                    )
                    prompt = {
                        "prompt_name": prompt_name,
                        "folder": folder,
                        "number": number,
                        "genre": genre,
                        "file_pattern": file_pattern,
                    }
                    prompts.append(prompt)
                txt2img["prompts"] = prompts

        if "abort_matrix" in txt_config:
            txt2img["abort_matrix"] = txt_config["abort_matrix"]

        if "coef_matrix" in txt_config:
            txt2img["coef_matrix"] = txt_config["coef_matrix"]

        if "folder_suffix" in yaml_config:
            config["folder_suffix"] = yaml_config["folder_suffix"]

        if "prefix" in txt_config:
            prefix = txt_config["prefix"]
            if "default" in prefix:
                txt2img["prefix"]["default"] = prefix["default"]
            if "exception" in prefix:
                txt2img["prefix"]["exception"] = prefix["exception"]
            if "exception_list" in prefix:
                txt2img["prefix"]["exception_list"] = prefix["exception_list"]
            if "suffix" in prefix:
                txt2img["prefix"]["suffix"] = prefix["suffix"]

        if "models" in txt_config:
            if type(txt_config["models"]) is str:
                txt2img["models"] = load_models_csv(txt_config["models"])
            else:
                list = txt_config["models"]
                models = []
                for model in list:
                    [model_name, vae, mode] = model.split(",")
                    model = {
                        "model_name": model_name,
                        "vae": vae,
                        "mode": mode,
                    }
                    models.append(model)
                txt2img["models"] = models
        if "log" in yaml_config:
            log = yaml_config["log"]
            if not ("days" in log):
                log["days"] = LOG_DAYS
            if not ("path" in log):
                log["path"] = LOG_PATH
            if "level" not in log:
                log["level"] = "info"
            if "print_levels" not in log:
                log["print_levels"] = ["info"]
            config["log"] = log

        dirs = config["img2img"]["dir"]

        if "img2img" in yaml_config:
            img2img = config["img2img"]
            img_config = yaml_config["img2img"]
            if "steps" in img_config:
                img2img["steps"] = img_config["steps"]
            if "denosing_strength" in img_config:
                img2img["denosing_strength"] = img_config["denosing_strength"]
            if "n_iter" in img_config:
                img2img["n_iter"] = img_config["n_iter"]
            if "batch_size" in img_config:
                img2img["batch_size"] = img_config["batch_size"]
            if "file_pattern" in img_config:
                img2img["file_pattern"] = img_config["file_pattern"]
            if "direct_call" in img_config:
                img2img["direct_call"] = img_config["direct_call"]
            if "overrides" in img_config:
                img2img["overrides"] = img_config["overrides"]
            if "dir" in img_config:
                dirs = img_config["dir"]
                image_dirs = img2img["dir"]
                Logger.debug(dirs)
                if "input" in dirs:
                    image_dirs["input"] = dirs["input"]
                if "work" in dirs:
                    image_dirs["work"] = dirs["work"]
                if "append" in dirs:
                    image_dirs["append"] = dirs["append"]
                if "mask" in dirs:
                    image_dirs["mask"] = dirs["mask"]
                if "ended" in dirs:
                    image_dirs["ended"] = dirs["ended"]
                if "output" in dirs:
                    image_dirs["output"] = dirs["output"]
                if "folder_suffix" in dirs:
                    image_dirs["folder_suffix"] = dirs["folder_suffix"]
                Logger.debug(image_dirs)
            config["img2img"] = img2img
        if "img2txt2img" in yaml_config:
            img2txt2img = config["img2txt2img"]
            if "overrides" in yaml_config["img2txt2img"]:
                img2txt2img["overrides"] = yaml_config["img2txt2img"]["overrides"]
            if "input" in yaml_config["img2txt2img"]:
                img2txt2img["input"] = yaml_config["img2txt2img"]["input"]
            if "output" in yaml_config["img2txt2img"]:
                img2txt2img["output"] = yaml_config["img2txt2img"]["output"]
            if "folder_suffix" in yaml_config["img2txt2img"]:
                img2txt2img["folder_suffix"] = yaml_config["img2txt2img"][
                    "folder_suffix"
                ]
            config["img2txt2img"] = img2txt2img
        if "custom" in yaml_config:
            config["custom"] = yaml_config["custom"]
        """
    # set Logger
    log = config["log"]
    DefaultLogger.setConfig(
        log["path"], log["print_levels"], log["level"], log["days"]
    )
    Logger.setConfig(log["path"], log["print_levels"], log["level"], log["days"])
    share.set("config", config)
    return config


# sleep time
def check_time(config_file):
    config = load_config(config_file)
    start_hour = config["start_hour"]
    stop_hour = config["stop_hour"]
    now = datetime.datetime.now()
    if not (now.hour >= start_hour and now.hour < stop_hour):
        Logger.info(
            f"sleeping...{now.hour} running between {start_hour} and {stop_hour}"
        )
    while not (now.hour >= start_hour and now.hour < stop_hour):
        time.sleep(60)
        config = load_config(config_file)
        start_hour = config["start_hour"]
        stop_hour = config["stop_hour"]
        now = datetime.datetime.now()


def custom(args):
    result = subprocess.run(args)
    if result.returncode == 0:
        Logger.info(f"custom command finished {args}")
        return True
    else:
        Logger.error(f"custom command failed {args}")
        return False


def run_plugin(plugin_name, config, args):
    try:
        Logger.info(f"custom {plugin_name} {args}")
        if plugin_name == "subprocess":
            result = custom(args[1:])
        elif os.path.isdir(os.path.join("./plugins", plugin_name)):
            import importlib

            plugin_module = importlib.import_module(f"plugins.{plugin_name}")
            result = plugin_module.run_plugin(args[1:], config)
        else:
            Logger.error(f"plugin {plugin_name} not found")
            return False
        return result
    except Exception as e:
        Logger.error(f"plugin error {e}")
        return False


def model_copy(clone):
    src_dir = clone["src"]
    dest_dir = clone["dest"]
    folders = clone["folders"]
    for folder in folders:
        src = os.path.join(src_dir, folder)
        dest = os.path.join(dest_dir, folder)
        if not os.path.exists(dest):
            os.makedirs(dest)
        Logger.info(f"copying {src} to {dest}")
        if os.name == "nt":
            subprocess.Popen(
                ["robocopy", src, dest, "/NP", "/J", "/R:1", "/W:1", "/FFT"],
                stdout=subprocess.DEVNULL,
            )
            Logger.verbose("robocopy", src, dest, "/NP", "/J", "/R:1", "/W:1", "/FFT")
        else:
            dest = dest.replace("\\", "/")
            # dest の最後を / にする
            if dest[-1] != "/":
                dest = dest + "/"
            subprocess.Popen(["rsync", "-av", src, dest], stdout=subprocess.DEVNULL)
            Logger.verbose("rsync", "-av", src, dest)


def run_img2img(config):
    host = config["host"]
    img_config = config["img2img"]
    img2img_steps = img_config["steps"]
    img2img_denosing_stringth = img_config["denosing_strength"]
    img2img_n_iter = img_config["n_iter"]
    img2img_batch_size = img_config["batch_size"]
    file_pattern = img_config["file_pattern"]
    dirs = img_config["dir"]
    input_dir = dirs["input"]
    work_dir = dirs["work"]
    input_append = dirs["append"]
    input_mask = dirs["mask"]
    ended_dir = dirs["ended"]
    output_dir = dirs["output"]
    folder_suffix = dirs["folder_suffix"]

    Logger.debug(config)

    # INPUT_DIRの下のフォルダ取得する
    folders = glob.glob(os.path.join(input_dir, "*"))
    Logger.verbose(input_dir)
    Logger.verbose(folders)

    for folder in folders:
        Logger.verbose(f"processing folder {folder}")
        files = glob.glob(os.path.join(folder, "*.png"))
        files.extend(glob.glob(os.path.join(folder, "*.jpg")))
        if len(files) == 0:
            Logger.verbose(f"no files in {folder}")
            continue
        # direct call が True の場合は modules/img2img.py を直接呼び出す
        if config.get("direct_call") is True or img_config.get("direct_call") is True:
            Logger.debug("direct_call")
            import modules.img2img

            overrides = {
                "steps": img2img_steps,
                "denoising_strength": img2img_denosing_stringth,
                "n_iter": img2img_n_iter,
                "batch_size": img2img_batch_size,
            }

            items = [
                "denoising_strength",
                "seed",
                "subseed",
                "subseed_strength",
                "batch_size",
                "n_iter",
                "steps",
                "cfg_scale",
                "width",
                "height",
                "prompt",
                "negative_prompt",
                "sampler_index",
                "mask_blur",
                "inpainting_fill",
                "inpaint_full_res",
                "inpaint_full_res_padding",
                "inpainting_mask_invert",
            ]

            if "overrides" in img_config:
                if type(img_config["overrides"]) is dict:
                    for item in img_config["overrides"]:
                        if item in items:
                            overrides[item] = img_config["overrides"][item]
                else:
                    Logger.debug("overrides is None")
            opt = {
                "filename_pattern": file_pattern,
                "mask_dir": input_mask,
                "alt_image_dir": input_append,
            }
            if config.get("userpass"):
                opt["userpass"] = config.get("userpass")
            if img_config.get("overrides"):
                opt["overrides"] = img_config.get("overrides")
            output = os.path.join(output_dir, os.path.basename(folder) + folder_suffix)
            Logger.verbose(f"output {output}, opt: {opt}")
            try:
                modules.img2img.img2img(
                    imagefiles=files,
                    overrides=overrides,
                    base_url=host,
                    output_dir=output,
                    opt=opt,
                )
                Logger.info(f"img2img.py finished {folder}")
                try:
                    for file in files:
                        shutil.move(file, ended_dir)
                except Exception as e:
                    Logger.debug(e)
            except Exception as e:
                Logger.error(e)
                Logger.error(f"img2img.py failed {folder}")
        else:
            for file in files:
                Logger.verbose(f"move {file} to {work_dir}")
                shutil.move(file, work_dir)

            # img2img.pyのrun_from_args_img2img()
            args = [
                "--filename-pattern",
                file_pattern,
                "--api-base",
                host,
                "--steps",
                str(img2img_steps),
                "--mask-dir",
                input_mask,
                "--alt-image-dir",
                input_append,
                "--output",
                os.path.join(output_dir, os.path.basename(folder) + folder_suffix),
                "--denoising_strength",
                str(img2img_denosing_stringth),
                "--n_iter",
                str(img2img_n_iter),
                "--batch_size",
                str(img2img_batch_size),
                work_dir,
            ]
            Logger.verbose(args)
            result = img2img.run_from_args_img2img(args)
            result = True
            if result:
                Logger.info(f"img2img.py finished {folder}")
                try:
                    # *.png, *.jpg を ended_dir に移動
                    files = glob.glob(os.path.join(work_dir, "*.png"))
                    files.extend(glob.glob(os.path.join(work_dir, "*.jpg")))
                    for file in files:
                        shutil.move(file, ended_dir)
                except Exception as e:
                    Logger.debug(e)
            else:
                Logger.error(f"img2img.py failed {folder}")
                try:
                    files = glob.glob(os.path.join(work_dir, "*.png"))
                    files.extend(glob.glob(os.path.join(work_dir, "*.jpg")))
                    for file in files:
                        shutil.move(file, folder)
                except Exception as e:
                    Logger.error(e)


def escape_split(str, split):
    import re

    regex = re.compile(r'".*?[^\\]*"')
    # 条件を満たす regex を抽出
    regex_list = regex.findall(str)
    # regex_list の 頭と後ろの" を削除
    regex_list = [regex[1:-1] for regex in regex_list]
    regex_replace = [regex.replace(" ", "\\S") for regex in regex_list]
    for regex, replace in zip(regex_list, regex_replace):
        str = str.replace(regex, replace)
    args = str.split(split)
    args = [arg.replace("\\S", " ") for arg in args]
    return args


def run_txt2img(config):
    host = config["host"]
    text_config = config["txt2img"]
    output_dir = text_config["output"]
    models = text_config["models"]
    exception_list = text_config["prefix"]["exception_list"]
    prompts = text_config["prompts"]
    prompt_base = text_config["prompt_base"]
    abort_matrix = text_config["abort_matrix"]
    coef_matrix = text_config["coef_matrix"]
    prefix = text_config["prefix"]
    folder_suffix = text_config["folder_suffix"]
    overrides = text_config["overrides"]
    info = text_config["info"]
    if type(overrides) is str:
        overrides = escape_split(overrides, " ")
        Logger.debug(f"overrides string {overrides}")
    elif type(overrides) is list:
        Logger.debug(f"overrides list {overrides}")
    else:
        Logger.debug("overrides is None")
        overrides = None

    while True:
        model = models[random.randint(0, len(models) - 1)]
        model_name = model["model_name"]
        vae = model["vae"]
        mode = model["mode"]
        Logger.info(f"Set model {model_name} vae {vae} mode {mode}")

        if mode in abort_matrix:
            matrix = abort_matrix[mode]
        else:
            matrix = None
        if matrix is None:
            Logger.info(f"SKIP {model_name} {vae} {mode}")
        else:
            break

    for prompt in prompts:
        prompt_name = prompt["prompt_name"]
        Logger.debug(f"prompt_name {prompt_name}")
        if prompt_name in exception_list:
            prompt_name = (
                prompt_base + prefix["exception"] + prompt_name + prefix["suffix"]
            )
        else:
            prompt_name = (
                prompt_base + prefix["default"] + prompt_name + prefix["suffix"]
            )
        folder = prompt["folder"]
        number = float(prompt["number"])
        genre = prompt["genre"]
        Logger.debug(
            f"prompt_name {prompt_name} folder {folder} number {number} genre {genre}"
        )

        file_pattern = prompt["file_pattern"]
        if file_pattern == "":
            file_pattern = "[num]-[seed]"

        if matrix == "*" or genre in matrix:
            coef = 1.0
            if mode in coef_matrix:
                if type(coef_matrix[mode]) is dict:
                    if genre in coef_matrix[mode] and (
                        type(coef_matrix[mode][genre]) is float or
                        type(coef_matrix[mode][genre]) is int
                    ):
                        coef = coef_matrix[mode][genre]
                elif type(coef_matrix[mode]) is float or type(coef_matrix[mode]) is int:
                    coef = coef_matrix[mode]

            number = int(number * coef)
            output = os.path.join(output_dir, folder + folder_suffix)
            Logger.info(f"{model_name}, {prompt_name}, {output}, {genre}")
            # If direct call is True, call modules/txt2img.py
            if (
                config.get("direct_call") is True or
                text_config.get("direct_call") is True
            ):
                Logger.debug("direct_call")
                # create prompt
                Logger.verbose(f"create prompt {prompt_name}")
                try:
                    import modules.prompt

                    opt = {
                        "mode": "json",
                        "override": overrides,
                        "info": info,
                        "input": prompt_name,
                        "max_number": number,
                        "api_filename_variable": True,
                    }
                    result = modules.prompt.create_text(opt)
                    # Logger.info(f"output_text {result['output_text']}")
                except Exception as e:
                    Logger.error("create prompt failed")
                    Logger.error(e)
                # Logger.debug(f"create prompt finished {result}")
                options = result["options"]
                payloads = result["output_text"]
                opt = {
                    "filename_pattern": file_pattern,
                    "sd_model": model_name or options["sd_model"],
                    "sd_vae": vae or options["sd_vae"],
                    "filename-variable": True,
                }
                if config.get("userpass"):
                    opt["userpass"] = config.get("userpass")
                if text_config.get("save_extend_meta"):
                    opt["save_extend_meta"] = text_config.get("save_extend_meta")
                if text_config.get("image_quality"):
                    opt["image_quality"] = text_config.get("image_quality")
                if text_config.get("image_quality"):
                    opt["image_quality"] = text_config.get("image_quality")
                # set model
                Logger.verbose(f"set model {model_name} {vae}")
                if model_name is not None:
                    import modules.api

                    try:
                        modules.api.set_sd_model(
                            base_url=host, sd_model=model_name, sd_vae=vae
                        )
                    except Exception as e:
                        Logger.error(e.with_traceback())
                # txt2img
                Logger.debug(f"txt2img {opt}")
                import modules.txt2img

                Logger.verbose(f"txt2img {opt}")
                try:
                    modules.txt2img.txt2img(
                        payloads,
                        base_url=host,
                        output_dir=output,
                        opt=opt,
                    )
                except Exception as e:
                    Logger.error(e)
                    return False
            else:
                args = [
                    "--api-mode",
                    "--api-base",
                    host,
                    "--api-set-sd-model",
                    model_name,
                    "--api-set-sd-vae",
                    vae,
                    "--api-filename-variable",
                    "--api-filename-pattern",
                    file_pattern,
                    "--api-output-dir",
                    output,
                    "--max-number",
                    str(number),
                    prompt_name,
                ]
                if overrides is not None and overrides != "":
                    args.extend(overrides)
                if info is not None and info != "":
                    args.append("--info")
                    args.append(info)
                Logger.verbose(args)

                try:
                    create_prompts.run_from_args(args)
                except Exception as e:
                    try:
                        Logger.debug(e)
                    except Exception as err:
                        print(e)
                        print(err)


def ping(config):
    host = config["host"].split(":")[1].replace("//", "")
    Logger.info(f"ping {host}")
    if os.name == "nt":
        result = subprocess.run(
            ["ping", host, "-n", "1", "-w", "1000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    else:
        result = subprocess.run(
            ["ping", host, "-c", "1", "-w", "1000"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    Logger.debug(f"ping {host} {result.returncode}")
    return result.returncode


def wait_ping(config):
    res = 1
    while res != 0:
        res = ping(config)
        if res != 0:
            Logger.info("ping failed")
            time.sleep(5)


def compare(*args):
    length = len(args)
    if length == 0:
        return True
    if length == 1:
        command = args[0]
    else:
        command, *args = args
    match command:
        case "date":
            pass
        case "time":
            pass
        case "day":
            pass
        case "hour":
            pass
        case "minute":
            pass
        case "second":
            pass
        case "weekday":
            pass
        case "month":
            pass
        case "year":
            pass
        case _:
            pass
    return True


def prepare_custom(config, args):
    if len(args) == 0:
        Logger.info("custom command not found")
        #         logging.info('custom command not found')
        return False
    plugin = args[0]
    if "custom" in config["custom"] and plugin in config["custom"][plugin]:
        plugin_config = config["custom"][plugin]
    else:
        plugin_config = None
    return plugin, plugin_config


def loop(config_file):
    Logger.info("loop mode")
    config = load_config(config_file)
    Logger.info(config["loop"])
    if not config["loop"]["mode"]:
        Logger.info("loop mode is not setting")
        return
    Logger.debug(config)
    random.seed()
    loop_counter = 0
    Logger.info("start")
    loop = config["loop"]
    Logger.info(f'MAX LOOP {loop["loop_count"]}')
    while True:
        if loop["loop_count"] > 0 and loop_counter >= loop["loop_count"]:
            Logger.info("LOOP completed")
            exit()
        loop_counter += 1
        Logger.info(f'LOOP #{loop_counter} / {loop["loop_count"]}')

        next = True

        for command in loop["commands"]:
            Logger.info(command)
            if not next:
                next = True
                continue
            commands = arg_split(command)
            command = commands[0].lower()
            args = commands[1:]
            try:
                match command:
                    case "check":
                        check_time(config_file)
                    case "compare":
                        if "compares" in config:
                            compares = config["compares"]
                        else:
                            compares = []
                        if args[0] in compares:
                            args = compares[int(args[0])]
                        else:
                            args = ""
                        next = compare(args)
                    case "ping":
                        wait_ping(config)
                    case "txt2img":
                        run_txt2img(config)
                    case "img2img":
                        run_img2img(config)
                    case "custom":
                        (plugin, plugin_config) = prepare_custom(config, args)
                        if plugin:
                            Logger.info(f"custom {plugin}")
                            run_plugin(plugin, plugin_config, args)
                        else:
                            continue
                    case "custom-loop":
                        try:
                            sleep_time = int(args[0])
                            args = args[1:]
                        except Exception:
                            sleep_time = 5

                        try:
                            max_count = int(args[0])
                            args = args[1:]
                        except Exception:
                            max_count = 0

                        Logger.info(args)
                        (plugin, plugin_config) = prepare_custom(config, args)
                        if plugin:
                            Logger.info(
                                f"custom loop {plugin} : {args} count {max_count} sleep {sleep_time}"
                            )
                            if len(args) > 1:
                                args = args[1:]
                            else:
                                args = []
                            count = 0

                            while max_count == 0 or max_count > count:
                                result = run_plugin(plugin, plugin_config, args)
                                print(result)
                                if result:
                                    break
                                count += 1
                                Logger.info(f"retry {count} {plugin}")
                                time.sleep(sleep_time)
                        else:
                            continue
                    case "custom-compare":
                        (plugin, plugin_config) = prepare_custom(config, args)
                        if plugin:
                            Logger.info(f"custom compare {plugin} : {args}")
                            next = run_plugin(plugin, plugin_config, args)
                        else:
                            continue
                    case "clone":
                        clone = config["clone"]
                        model_copy(clone)
                    case "sleep":
                        time.sleep(int(args[0]))
                    case "exit":
                        exit()
                    case "break":
                        break
                    case _:
                        Logger.info(f"unknown command {command}")
            except AttributeError as e:
                Logger.error(f"command error {command} {e}")
                exit(1)
            except Exception as e:
                Logger.info("run-loop error", e)
                continue
            config = load_config(config_file)
            if not config["loop"]["mode"]:
                break
            loop = config["loop"]


def main(config_file=CONFIG):
    config = load_config(config_file)
    if config["loop"]["mode"]:
        loop(config_file)

    while True:
        try:
            Logger.info("start")
            check_time(config_file)
            Logger.info("running...")
            res = 1
            while res != 0:
                res = ping(config)
                if res != 0:
                    Logger.info("ping failed")
                    time.sleep(5)
            config = load_config(config_file)
        except Exception as e:
            Logger.info("load config error", e)
            Logger.info("Please check config.yaml")
            Logger.info("Wait 60 seconds...")
            time.sleep(60)
            continue

        if config["clone"]["clone"]:
            clone = config["clone"]
            print("clone")
            model_copy(clone)
        Logger.info("txt2img")
        try:
            run_txt2img(config)
        except AttributeError as e:  # if this error is happned reboot
            Logger.error(f"Attribute Error in txt2img {e}")
            exit(1)
        except Exception as e:
            Logger.error("txt2img running error", e)
        Logger.info("img2img")
        try:
            run_img2img(config)
        except AttributeError as e:  # if this error is happned reboot
            Logger.error(f"Attribute Error in img2img {e}")
            exit(1)
        except Exception as e:
            Logger.error("img2img running error", e)
        time.sleep(1)


if __name__ == "__main__":
    import sys

    args = sys.argv
    if len(args) == 1:
        main()
    else:
        main(args[1])
