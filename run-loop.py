#!/usr/bin/env python3
import csv
import datetime
import glob
import os
import random
import shutil
import subprocess
import time

import httpx
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


def get_image_files(folder):
    supoorted_files = ["*.png", "*.jpg", "*.jpeg", "*.webp"]
    files = []
    for file in supoorted_files:
        files.extend(glob.glob(os.path.join(folder, file)))
    return files


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
    with open(filename, encoding="utf-8") as f:
        reader = csv.reader(f)
        # model_name,vae,mode,
        for i, row in enumerate(reader):
            if len(row) < 3:
                if len(row) == 0:
                    Logger.debug(f"load_models_csv {filename} line {i} empty")
                    continue
                Logger.warning(
                    f"load_models_csv line {i} {row} error column count {len(row)}"
                )
                continue
            try:
                model = {
                    "model_name": row[0],
                    "vae": row[1],
                    "mode": row[2],
                }
                if len(row) > 3:
                    model["overrrides"] = row[3]
            except Exception as e:
                Logger.error(f"load_models_csv {filename} {i} {row} error {e}")
                continue
            models.append(model)
    Logger.debug(f"load_models_csv {filename} {models}")
    return models


def load_prompts_csv(filename):
    if not (os.path.exists(filename)):
        return []
    prompts = []
    with open(filename, encoding="utf-8") as f:
        reader = csv.reader(f)
        # prompt_name,folder,number,genre,
        for i, row in enumerate(reader):
            if len(row) < 4:
                if len(row) == 0:
                    Logger.debug(f"load_prompts_csv {filename} line {i} empty")
                    continue
                Logger.warning(
                    f"load_prompts_csv {filename} line {i} {row} error column count {len(row)}"
                )
                continue
            prompt = {
                "prompt_name": row[0],
                "folder": row[1],
                "number": row[2],
                "genre": row[3],
                "file_pattern": row[4],
            }
            if len(row) > 5:
                prompt["profile"] = row[5]
            else:
                prompt["profile"] = ""
            prompts.append(prompt)
    Logger.debug(f"load_prompts_csv {filename} {prompts}")
    return prompts


def load_not_default(filename):
    if os.path.exists(filename):
        with open(filename, "r", encoding="utf-8") as f:
            not_default = f.read().splitlines()
        return not_default
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
                [prompt_name, folder, number, genre, file_pattern] = prompt.split(",")
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
    if "profiles" in txt_config:
        for profile in txt_config["profiles"]:
            if "prompts" in profile:
                if type(profile["prompts"]) is str:
                    txt2img["prompts"] = load_prompts_csv(profile["prompts"])
                else:
                    prompts = []
                    for prompt in profile["prompts"]:
                        [prompt_name, folder, number, genre, file_pattern] = (
                            prompt.split(",")
                        )
                        prompt = {
                            "prompt_name": prompt_name,
                            "folder": folder,
                            "number": number,
                            "genre": genre,
                            "file_pattern": file_pattern,
                        }
                        prompts.append(prompt)
                    profile["prompts"] = prompts
            if "model" in profile:
                if type(profile["models"]) is str:
                    profile["models"] = load_models_csv(profile["models"])
                else:
                    list = profile["models"]
                    models = []
                    for model in list:
                        [model_name, vae, mode] = model.split(",")
                        model = {
                            "model_name": model_name,
                            "vae": vae,
                            "mode": mode,
                        }
                        models.append(model)
                profile["models"] = models


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
    schedule = {
        "start_hour": START_HOUR,
        "stop_hour": STOP_HOUR,
    }
    config = {
        "host": HOST,
        "prompt_base": PROMPT_BASE,
        "schedule": schedule,
        "txt2img": txt2img,
        "img2img": img2img,
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
    # set Logger
    log = config["log"]
    DefaultLogger.setConfig(log["path"], log["print_levels"], log["level"], log["days"])
    Logger.setConfig(log["path"], log["print_levels"], log["level"], log["days"])
    share.set("config", config)
    return config


def parseBetweenTime(config_time):
    # 7:30-21:00
    config_times = config_time.split("-")
    if len(config_times) == 2:
        start_time = config_times[0].strip()
        stop_time = config_times[1].strip()
    else:
        start_time = "00:00"
        stop_time = "24:00"
    return start_time, stop_time


def load_schedule(config_file):
    schedule = load_config(config_file)["schedule"]
    if "time" in schedule:
        start_time, stop_time = parseBetweenTime(schedule["time"])
        start_hour = int(start_time.split(":")[0])
        start_minute = int(start_time.split(":")[1])
        stop_hour = int(stop_time.split(":")[0])
        stop_minute = int(stop_time.split(":")[1])
    else:
        start_hour = schedule.get("start", schedule["start_hour"])
        start_minute = schedule.get("start_minute", 0)
        stop_hour = schedule.get("stop", schedule["stop_hour"])
        stop_minute = schedule.get("stop_minute", 0)
    return start_hour, start_minute, stop_hour, stop_minute


# sleep time
def check_time(config_file):
    start_hour, start_minute, stop_hour, stop_minute = load_schedule(config_file)
    now = datetime.datetime.now()
    minutes = now.minute + now.hour * 60
    start_minutes = start_minute + start_hour * 60
    stop_minutes = stop_minute + stop_hour * 60
    if stop_minutes < start_minutes:
        if minutes < stop_minutes:
            minutes += 60 * 24
        stop_minutes += 60 * 24

    if not (minutes >= start_minutes and minutes < stop_minutes):
        now_minute = str(now.minute).zfill(2)
        start_minute = str(start_minute).zfill(2)
        stop_minute = str(stop_minute).zfill(2)
        Logger.info(
            f"sleeping...{now.hour}:{now_minute} running between {start_hour}:{start_minute} and {stop_hour}:{stop_minute}"
        )
    else:
        return
    while not (minutes >= start_minutes and minutes < stop_minutes):
        time.sleep(60)
        now = datetime.datetime.now()
        minutes = now.minute + now.hour * 60
        start_hour, start_minute, stop_hour, stop_minute = load_schedule(config_file)
        start_minutes = start_minute + start_hour * 60
        stop_minutes = stop_minute + stop_hour * 60
        if stop_minutes < start_minutes:
            if minutes < stop_minutes:
                minutes += 60 * 24
            stop_minutes += 60 * 24


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
        Logger.verbose(f"custom {plugin_name} {args}")
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
    recursive = clone.get("recursive", False)
    for folder in folders:
        src = os.path.join(src_dir, folder)
        dest = os.path.join(dest_dir, folder)
        if not os.path.exists(dest):
            os.makedirs(dest)
        Logger.info(f"copying {src} to {dest}")
        if os.name == "nt":
            if recursive:
                subprocess.Popen(
                    ["robocopy", src, dest, "/NP", "/J", "/R:1", "/W:1", "/FFT", "/S"],
                    stdout=subprocess.DEVNULL,
                )
                Logger.verbose(
                    "robocopy", src, dest, "/NP", "/J", "/R:1", "/W:1", "/FFT", "/S"
                )
            else:
                subprocess.Popen(
                    ["robocopy", src, dest, "/NP", "/J", "/R:1", "/W:1", "/FFT"],
                    stdout=subprocess.DEVNULL,
                )
                Logger.verbose(
                    "robocopy", src, dest, "/NP", "/J", "/R:1", "/W:1", "/FFT"
                )
        else:
            dest = dest.replace("\\", "/")
            # dest の最後を / にする
            if dest[-1] != "/":
                dest = dest + "/"
            if recursive:
                subprocess.Popen(
                    ["rsync", "-avr", src, dest], stdout=subprocess.DEVNULL
                )
                Logger.verbose("rsync", "-avr", src, dest)
            else:
                subprocess.Popen(["rsync", "-av", src, dest], stdout=subprocess.DEVNULL)
                Logger.verbose("rsync", "-av", src, dest)


def get_profile_name(args=None):
    profile_name = None
    if type(args) is str:
        profile_name = args
    elif type(args) is list:
        if len(args) > 0:
            profile_name = args[0]
    elif type(args) is dict:
        profile_name = args.get("profile")
    return profile_name


def run_img2img(config, args=None):
    Logger.verbose(f"run img2img args {args}")
    host = config["host"]
    img_config = config["img2img"]
    profile_name = get_profile_name(args)
    if img_config.get("profiles") and profile_name is not None:
        Logger.info(f"run img2img {profile_name}")
        img_config = img_config["profiles"].get(profile_name) or img_config
    Logger.verbose(f"img2img config {img_config}")
    options = img_config.get("options", {})
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
        files = get_image_files(folder)
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
                "enable_hr",
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
                "comments",
                "negative_prompt",
                "sampler_index",
                "mask_blur",
                "inpainting_fill",
                "inpaint_full_res",
                "inpaint_full_res_padding",
                "inpainting_mask_invert",
                "override_settings_restore_afterwards",
                "refiner_checkpoint",
                "refiner_switch_at",
            ]

            if "overrides" in img_config:
                if type(img_config["overrides"]) is dict:
                    _overrides = img_config["overrides"]
                    for item in _overrides:
                        if item in items:
                            if item:
                                overrides[item] = _overrides[item]
                        elif item == "override_settings":
                            for override in _overrides[item]:
                                overrides[override] = _overrides[item][override]
                else:
                    Logger.debug("overrides is None")
            opt = options
            opt["filename_pattern"] = file_pattern
            opt["mask_dir"] = input_mask
            opt["alt_image_dir"] = input_append

            if config.get("userpass"):
                opt["userpass"] = config.get("userpass")
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
                        try:
                            shutil.move(file, ended_dir)
                        except Exception as e:
                            Logger.error(f"move {file} to {ended_dir} failed")
                            Logger.debug(e)
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
                    files = get_image_files(work_dir)
                    for file in files:
                        shutil.move(file, ended_dir)
                except Exception as e:
                    Logger.debug(e)
            else:
                Logger.error(f"img2img.py failed {folder}")
                try:
                    files = get_image_files(work_dir)
                    for file in files:
                        shutil.move(file, folder)
                except Exception as e:
                    Logger.error(e)


def run_img2txt2img(config, args):
    Logger.verbose(f"run img2txt2img args {args}")
    profile_name = get_profile_name(args)
    Logger.info(f"run img2txt2img {profile_name}")
    iti_config = config.get("img2txt2img")
    if iti_config is None:
        Logger.error("img2txt2img config not found")
        return False
    base_url = config["host"]
    dry_run = iti_config.get("dry_run")
    profiles = iti_config.get("profiles", iti_config)
    profile = profiles.get(profile_name, iti_config.get("DEFAULT"))
    if profile is None or type(profile) is not dict:
        Logger.error(f"profile {profile_name} not found in config")
        return False
    base_url = config["host"]
    modelsFile = iti_config.get("modelfile")
    models = {}
    if os.path.exists(modelsFile):
        with open(modelsFile, "r", encoding="utf-8") as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                models[row[0]] = row[1:]

    files = profile["input"]
    if type(files) is not list:
        files = [files]

    imgfiles = []
    for filename in files:
        if not os.path.exists(filename):
            Logger.error(f"File not found: {filename}")
        if os.path.isdir(filename):
            imgfiles.extend(get_image_files(filename))
        else:
            imgfiles.append(filename)
    # overrride settings
    overrides = profile.get("overrides", {})
    all_images_count = len(imgfiles)

    backup = profile.get("backup", None)
    output_dir = profile.get("output", None)
    options = profile.get("options", {})
    options["dry_run"] = dry_run
    if "default_vae" in profile:
        options["sd_vae"] = profile["default_vae"]

    Logger.info(f"img2txt2img run {len(imgfiles)} images")
    divide = profile.get("divide", 0)
    if divide > 0:
        Logger.verbose(f"trunsuction {divide}")
        file_sets = [imgfiles[i : i + divide] for i in range(0, len(imgfiles), divide)]
    else:
        file_sets = [imgfiles]

    result = True
    count = 0
    for imgfiles in file_sets:
        try:
            import modules.img2txt2img

            modules.img2txt2img.img2txt2img(
                imgfiles,
                base_url=base_url,
                overrides=overrides,
                seed_diff=profile.get("seed_diff", 0),
                models=models,
                output_dir=output_dir,
                opt=options,
            )

        except Exception as e:
            Logger.error(e)
            result = False
            continue
        count += len(imgfiles)
        remain = all_images_count - count
        Logger.info(f"img2txt2img finished {count} images remain {remain}")
        try:
            if backup is not None:
                if not dry_run:
                    if not os.path.exists(backup):
                        os.makedirs(backup)
                else:
                    Logger.info(f"dry run create directory {backup}")
                for imgfile in imgfiles:
                    backupfile = os.path.join(backup, os.path.basename(imgfile))
                    if os.path.exists(backupfile):
                        file_ext = os.path.splitext(imgfile)[1]
                        file_base = os.path.splitext(imgfile)[0]
                        i = 1
                        while os.path.exists(backupfile):
                            backupbase = file_base + "_" + str(i) + file_ext
                            i += 1
                            backupfile = os.path.join(
                                backup, os.path.basename(backupbase)
                            )
                    if not dry_run:
                        try:
                            os.rename(imgfile, backupfile)
                            Logger.verbose(f"Moved {imgfile} to {backupfile}")
                        except Exception as e:
                            Logger.error(f"Move {imgfile} to {backupfile} failed")
                            Logger.error(e)
                    else:
                        Logger.info(f"dry run move {imgfile} to {backupfile}")
            else:
                for imgfile in imgfiles:
                    if not dry_run:
                        try:
                            os.remove(imgfile)
                            Logger.verbose(f"Removed {imgfile}")
                        except Exception as e:
                            Logger.error(f"Remove {imgfile} failed")
                            Logger.error(e)
                    else:
                        Logger.info(f"dry run remove {imgfile}")
        except Exception as e:
            Logger.error(e)
            result = False
    return result


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


def run_txt2img(config, args=None):
    # Logger.verbose(f"run txt2img args {args}")
    try:
        profile_name = get_profile_name(args)
    except Exception as e:
        Logger.error(f"get_profile_name failed {e}")
        profile_name = None
    Logger.info(f"profile name is {profile_name}")
    host = config["host"]
    text_config = config["txt2img"]
    if text_config.get("profiles") and profile_name is not None:
        Logger.info(f"run txt2img {profile_name}")
        text_config = text_config["profiles"].get(profile_name) or text_config

    Logger.debug(f"text_config {text_config}")
    models = text_config.get("models", [])
    if type(models) is str:
        models = load_models_csv(models)
    Logger.debug(f"models {models}")
    prompts = text_config.get("prompts", [])
    if type(prompts) is str:
        prompts = load_prompts_csv(prompts)
    Logger.debug(f"prompts {prompts}")
    output_dir = text_config.get("output", None)
    exception_list = text_config["prefix"].get("exception_list", [])
    prompt_base = text_config.get("prompt_base", "")
    abort_matrix = text_config.get("abort_matrix", {})
    coef_matrix = text_config.get("coef_matrix", {})
    prefix = text_config.get("prefix", {})
    folder_suffix = text_config.get("folder_suffix", "-images")

    version = text_config.get("version", 1)

    # 以下 direct config。matrix系より優先されるオプション
    # prompt_name = text_config.get("prompt_name") # prompt用yamlを固定する場合
    # file_pattern = text_config.get("file_pattern")    # file_patternを固定する場合
    # max_number = text_config.get("max_number")    # numberを固定する場合
    # model_name = text_config.get("model_name")    # modelを固定する場合
    # vae_name = text_config.get("vae_name")        # vaeを固定する場合
    # direct_output_dir = text_config.get("output_dir")　# output_dirを固定する場合

    overrides = text_config.get("overrides", "")
    info = text_config.get("info", "")
    options = text_config.get("options", {})
    if type(overrides) is str:
        overrides = escape_split(overrides, " ")
        Logger.debug(f"overrides string {overrides}")
    elif type(overrides) is list:
        Logger.debug(f"overrides list {overrides}")
    else:
        Logger.debug("overrides is None")
        overrides = None

    overrides_backup = overrides
    Logger.debug(f"enter loop {models}")
    while True:
        overrides = overrides_backup
        model = models[random.randint(0, len(models) - 1)]
        model_name = model["model_name"]
        vae = model["vae"]
        mode = model["mode"]
        Logger.info(f"Set model {model_name} vae {vae} mode {mode}")
        if info != "":
            info = f"$MODEL={model_name},$VAE={vae},$MODE={mode}," + info
        else:
            info = f"$MODEL={model_name},$VAE={vae},$MODE={mode}"

        if model.get("overrides"):
            # model overrides is only text
            overrides = escape_split(model["overrides"], " ")
            Logger.info(f"model overrides {overrides}")

        if mode in abort_matrix:
            matrix = abort_matrix[mode]
        else:
            matrix = None
        if matrix is None:
            Logger.verbose(f"SKIP {model_name} {vae} {mode}")
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
        profile = prompt.get("profile", None)
        Logger.debug(
            f"prompt_name {prompt_name} folder {folder} number {number} genre {genre}"
        )

        file_pattern = prompt["file_pattern"]
        if file_pattern == "":
            file_pattern = "[num]-[seed]"

        if matrix == "*" or genre in matrix:
            coef = 1.0
            if version == 1:
                if mode in coef_matrix:
                    if type(coef_matrix[mode]) is dict:
                        if genre in coef_matrix[mode] and (
                            type(coef_matrix[mode][genre]) is float
                            or type(coef_matrix[mode][genre]) is int
                        ):
                            coef = coef_matrix[mode][genre]
                    elif (
                        type(coef_matrix[mode]) is float
                        or type(coef_matrix[mode]) is int
                    ):
                        coef = coef_matrix[mode]

            number = int(number * coef + 0.5)
            output = os.path.join(output_dir, folder + folder_suffix)
            Logger.debug(
                f"choice {model_name}, {prompt_name}, {output}, {genre}, {profile}"
            )
            if number < 1:
                Logger.debug(f"skip number {number} < 1")
                continue
            Logger.info(f"{model_name}, {prompt_name}, {output}, {genre}, {profile}")

            # If direct call is True, call modules/txt2img.py
            if (
                config.get("direct_call") is True
                or text_config.get("direct_call") is True
            ):
                Logger.debug("direct_call")
                # create prompt
                Logger.verbose(f"create prompt {prompt_name}")
                try:
                    if version == 1:
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
                    else:
                        import modules.prompt_v2

                        opt = {
                            "mode": "json",
                            "v1json": True,
                            "override": overrides,
                            "info": info,
                            "input": prompt_name,
                            "max_number": number,
                            "api_filename_variable": True,
                        }
                        if profile is not None:
                            opt["profile"] = profile
                        result = modules.prompt_v2.create_text_v2(opt)

                    # Logger.info(f"output_text {result['output_text']}")
                except Exception as e:
                    Logger.error("create prompt failed")
                    Logger.error(e)
                    continue
                # Logger.debug(f"create prompt finished {result}")
                if result is None:
                    Logger.error("create prompt failed")
                    continue
                payloads = result["output_text"]
                opt = options.copy()
                opt["filename_pattern"] = file_pattern
                opt["sd_model"] = model_name or result["options"].get("sd_model")
                opt["sd_vae"] = vae or result["options"].get("sd_vae")
                opt["filename-variable"] = True
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
                        start_time = time.time()
                        modules.api.set_sd_model(
                            base_url=host, sd_model=model_name, sd_vae=vae
                        )
                        end_time = time.time()
                        Logger.info(f"set model time {end_time - start_time} sec")
                    except Exception as e:
                        Logger.error("set model failed")
                        Logger.error(e)
                # txt2img
                Logger.debug(f"txt2img {opt}")
                import modules.txt2img

                try:
                    modules.txt2img.txt2img(
                        payloads,
                        base_url=host,
                        output_dir=output,
                        opt=opt,
                    )
                except Exception as e:
                    Logger.error("txt2img failed")
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
                if version >= 2:
                    args.append("--v1json")
                    if profile is not None:
                        args.append("--profile")
                        args.append(profile)
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
            Logger.error("ping failed")
            time.sleep(5)


def check_launch(config, verbose=True):
    host = config["host"]
    if verbose:
        Logger.info(f"wait api {host}")
    url = f"{host}/sdapi/v1/memory"

    try:
        with httpx.Client(timeout=httpx.Timeout(1, read=5)) as client:
            response = client.get(url)
            if response.status_code == 200:
                if verbose:
                    Logger.info("api is ready")
                return True
            else:
                Logger.error(f"api is return error {response.status_code}")
                return False
    except Exception as e:
        if verbose:
            Logger.error(f"api is not ready {e}")
        return False


def wait_launch(config, args):
    if len(args) == 0:
        max_wait_time = args[0]
    else:
        max_wait_time = config.get("max_wait_time", 300)
    res = False
    is_fist = True
    start_time = time.time()
    Logger.info("wait api")
    while not res:
        res = check_launch(config, verbose=False)
        if not res:
            if is_fist:
                Logger.info("api is not ready waiting...")
                is_fist = False
            duration = time.time() - start_time
            if duration > max_wait_time:
                res = check_launch(config, verbose=True)
                if not res:
                    Logger.error("api is not ready timeout")
                    return False
                return True
            Logger.verbose("api is not ready wait 5 sec")
            time.sleep(5)
    Logger.info("api is ready")
    return True


def date_to_isoformat(date):
    dates = date.split("-")
    if len(dates) >= 1:
        # zero padding
        year = str(int(dates[0])).zfill(4)
    if len(dates) >= 2:
        month = str(int(dates[1])).zfill(2)
    else:
        month = "01"
    if len(dates) >= 3:
        day = str(int(dates[2])).zfill(2)
    else:
        day = "01"
    return f"{year}-{month}-{day}"


def time_to_isoformat(time):
    times = time.split(":")
    if len(times) >= 1:
        # zero padding
        hour = str(int(times[0])).zfill(2)
    if len(times) >= 2:
        minute = str(int(times[1])).zfill(2)
    else:
        minute = "00"
    if len(times) >= 3:
        second = str(int(times[2])).zfill(2)
    else:
        second = "00"
    return f"{hour}:{minute}:{second}"


def compare(args):
    Logger.verbose(f"compare {args}")
    length = len(args)
    if length == 0:
        return True
    command = args[0]
    args = args[1:]
    match command:
        case "afterdate":  # compare date %Y-%m-%d is after now return True
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            compare_date = date_to_isoformat(args[0])
            if compare_date <= now:
                return True
            else:
                return False
        case "befordate":  # compare date %Y-%m-%d is befor now return True
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            compare_date = date_to_isoformat(args[0])
            if compare_date > now:
                return True
            else:
                return False
        case "betweendate":  # compare date from %Y-%m-%d to  is between now return True
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            if len(args) < 2:
                Logger.error(f"betweendate args must has Two error but has {len(args)}")
                return False
            compare_date_from = date_to_isoformat(args[0])
            compare_date_to = date_to_isoformat(args[1])
            if compare_date_from <= now and compare_date_to > now:
                return True
            else:
                return False
        case "aftertime":  # compare time %H:%M:%S is after now return True
            Logger.debug(f"aftertime {args}")
            now = datetime.datetime.now().strftime("%H:%M:%S")
            compare_time = time_to_isoformat(args[0])
            Logger.debug(f"compare_time {compare_time} now {now}")
            if compare_time <= now:
                return True
            else:
                return False
        case "beforetime":  # compare time %H:%M:%S is befor now return True
            Logger.debug(f"aftertime {args}")
            now = datetime.datetime.now().strftime("%H:%M:%S")
            compare_time = time_to_isoformat(args[0])
            Logger.debug(f"compare_time {compare_time} now {now}")
            if compare_time > now:
                return True
            else:
                return False
        case "betweentime":  # compare time from %H:%M:%S to  is between now return True
            now = datetime.datetime.now().strftime("%H:%M:%S")
            if len(args) < 2:
                Logger.error(f"betweentime args must has Two error but has {len(args)}")
                return False

            compare_time_from = time_to_isoformat(args[0])
            compare_time_to = time_to_isoformat(args[1])
            if compare_time_from <= now and now < compare_time_to:
                return True
            else:
                return False
        case "date":  # compare date %Y-%m-%d is equal now return True
            now = datetime.datetime.now().strftime("%Y-%m-%d")
            compare_date = date_to_isoformat(args[0])
            if compare_date == now:
                return True
            else:
                return False
        case "day":  # compare day %d is equal now return True
            now = datetime.datetime.now().strftime("%d")
            compare_day = str(int(args[0])).zfill(2)
            if compare_day == now:
                return True
            else:
                return False
        case "hour":  # compare hour %H is equal now return True
            now = datetime.datetime.now().strftime("%H")
            compare_hour = str(int(args[0])).zfill(2)
            if compare_hour == now:
                return True
            else:
                return False
        case "minute":  # compare minute %M is equal now return True
            now = datetime.datetime.now().strftime("%M")
            compare_minute = str(int(args[0])).zfill(2)
            if compare_minute == now:
                return True
            else:
                return False
        case "weekday":  # compare weekday %w is equal now return True
            weekdays_mtx = [
                ["sun", "mon", "tue", "wed", "thu", "fri", "sat", "sun"],
                [
                    "sunday",
                    "monday",
                    "tuesday",
                    "wednesday",
                    "thursday",
                    "friday",
                    "saturday",
                    "sunday",
                ],
                ["日", "月", "火", "水", "木", "金", "土", "日"],
            ]
            idx = datetime.datetime.now().strftime("%w")
            compare_weekday = args[0].lower()
            for weekdays in weekdays_mtx:
                if compare_weekday in weekdays:
                    compare_weekday = weekdays.index(compare_weekday)
                    break
            if compare_weekday == idx:
                return True
            else:
                return False
        case "month":  # compare month %m is equal now return True
            now = datetime.datetime.now().strftime("%m")
            compare_month = str(int(args[0])).zfill(2)
            if compare_month == now:
                return True
            else:
                return False
        case "year":  # compare year %Y is equal now return True
            now = datetime.datetime.now().strftime("%Y")
            compare_year = str(int(args[0])).zfill(4)
            if compare_year == now:
                return True
            else:
                return False
        case "existfile":  # arg[0] file is exist return True
            file = args[0]
            if os.path.exists(file):
                if os.path.isfile(file):
                    return True
                else:
                    Logger.verbose(f"{file} is not file")
            Logger.verbose(f"{file} is not exist")
            return False
        case "notexist":  # arg[0] file is not exist return True
            file = args[0]
            if not os.path.exists(file):
                return True
            return False
        case "existdir":  # arg[0] dir is exist return True
            dir = args[0]
            if os.path.exists(dir):
                if os.path.isdir(dir):
                    return True
            return False
        case _:
            pass
    return True


def prepare_custom(config, args):
    if len(args) == 0:
        Logger.warning("custom command not found")
        #         logging.info('custom command not found')
        return False, None
    plugin = args[0]
    if "custom" in config["custom"] and plugin in config["custom"][plugin]:
        plugin_config = config["custom"][plugin]
    else:
        plugin_config = None
    return plugin, plugin_config


def run_command(command, config_file, config, next=True):
    if command == "":
        return next
    commands = arg_split(command)
    command = commands[0].lower()
    now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    Logger.info(f"{now} {command}")
    if len(commands) > 1:
        args = commands[1:]
    else:
        args = []
    try:
        match command:
            case "check":
                check_time(config_file)
            case "compare":
                next = compare(commands[1:])
            case "ping":
                wait_ping(config)
            case "launch":
                wait_launch(config, args)
            case "txt2img":
                run_txt2img(config, args)
            case "img2img":
                run_img2img(config, args)
            case "img2txt2img":
                run_img2txt2img(config, args)
            case "custom":
                (plugin, plugin_config) = prepare_custom(config, args)
                if plugin:
                    Logger.info(f"custom {plugin}")
                    next = run_plugin(plugin, plugin_config, args)
                else:
                    pass
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
                    return next
            case "custom-compare":
                (plugin, plugin_config) = prepare_custom(config, args)
                if plugin:
                    Logger.info(f"custom compare {plugin} : {args}")
                    next = run_plugin(plugin, plugin_config, args)
                else:
                    return next
            case "clone":
                clone = config["clone"]
                model_copy(clone)
            case "sleep":
                time.sleep(int(args[0]))
            case "exit":
                exit()
            case "break":
                raise Exception("break")
            case _:
                Logger.warning(f"unknown command {command}")
    except AttributeError as e:
        Logger.error(f"command error {command} {e}")
        return False
    except Exception as e:
        Logger.error("run-loop error", e)
        return False
    return next


def run_loop(command, config_file, config, loop_count, nest=0):
    commands = command.split("\n")
    Logger.verbose(commands)
    next = True
    for command in commands:
        if command == "":
            continue
        result = run_command(command, config_file, config, next)
        if result is False:
            next = False
    return next


def loop(config_file):
    Logger.info("loop mode")
    config = load_config(config_file)
    Logger.verbose(config["loop"])
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
            now = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            Logger.verbose(f"{now} {command}")
            if next is False:
                Logger.info(f"skip {command}")
                next = True
                continue
            next = run_loop(command, config_file, config, loop_counter)
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
            Logger.error("load config error", e)
            Logger.error("Please check config.yaml")
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

    print("run-loop script: start")
    args = sys.argv
    if len(args) == 1:
        main()
    else:
        main(args[1])
