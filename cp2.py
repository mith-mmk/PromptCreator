#!/usr/bin/env python3
# !pip install pyyaml
# !pip install Pillow
# !pip install httpx

# version 2.0 (C) 4 MITH@mmk  MIT License
# 2.0dev1 2024-06-06

import argparse
import copy
import json
import os

import modules.api as api
from modules.img2img import img2img
from modules.interrogate import interrogate
from modules.logger import getDefaultLogger
from modules.prompt import expand_arg
from modules.prompt_v2 import create_text_v2
from modules.txt2img import txt2img

Logger = getDefaultLogger()


def img2img_from_args(args):
    opt = {}
    opt["sd_model"] = args.api_set_sd_model
    opt["sd_vae"] = args.api_set_sd_vae
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
    overrides_arg = expand_arg(args.override)
    overrides = {}
    if overrides_arg is not None:
        for item in items:
            if overrides_arg.get(item):
                overrides[item] = overrides_arg[item]
    if type(args.input) is str:
        filenames = [args.input]
    base_url = args.api_base
    output_dir = args.api_output_dir or "./outputs"
    dicted_args = vars(args)
    input_files = []
    for filename in filenames:
        if os.path.isdir(filename):
            path = filename
            files = os.listdir(path)
            for file in files:
                file = os.path.join(path, file)
                if os.path.isfile(file):
                    input_files.append(file)
        elif os.path.isfile(filename):
            input_files.append(filename)
    if len(input_files) == 0:
        Logger.error("no exit files")
        return False

    if dicted_args.get("sd_model") is not None:
        api.set_sd_model(
            dicted_args.get("sd_model"),
            base_url=base_url,
            sd_vae=dicted_args.get("sd_vae"),
        )

    opt = {}

    opt_keys = [
        "alt_image_dir",
        "interrogate",
        "filename_pattern",
        "api_filename_variables",
        "verbose",
        "mask_dir",
        "userpass",
        "num_once",
        "num_length",
    ]
    for key in opt_keys:
        if dicted_args.get(key) is not None:
            opt[key] = dicted_args.get(key)

    try:
        img2img(
            input_files,
            base_url=base_url,
            overrides=overrides,
            output_dir=output_dir,
            opt=opt,
        )
    except Exception as e:
        Logger.error("img2img error")
        Logger.info(e)
        return False
    return True


def interrogate_from_args(args):
    base_url = args.api_base
    if type(args.input) is str:
        filenames = [args.input]
    else:
        filenames = args.input
    # model = 'deepdanbooru' need set webui --deepdanbooru option
    for filename in filenames:
        result = interrogate(
            filename, base_url=base_url, model=args.model
        )  # 'clip' or 'deepdanbooru'
        Logger.info(result)
        if result.status_code == 200:
            Logger.info(filename)
            Logger.info(result.json()["caption"])
        else:
            Logger.info(result.text)
            Logger.info("Is Web UI replace newest version?")


def main(args):
    if args.api_mode:
        if args.api_type == "img2img":
            img2img_from_args(args)
            return True
        if args.api_type == "interrogate":
            interrogate_from_args(args)
            return True
    if args.api_comfy and args.api_mode:
        Logger.error("api-comfy and api-mode is not same time")
        return False
    save_image = []
    if args.api_comfy:
        api_mode = "comfy"
        save_mode = args.api_comfy_save.lower()
        if save_mode == "save":
            save_image = ["websocket"]
        elif save_mode == "both":
            save_image = ["ui", "save"]
        elif save_mode == "ui":
            save_image = ["ui"]
        else:
            Logger.error("api-comfy-save option error use [save, both, ui]")
            return False

    if args.input is not None:
        Logger.debug(f"input: {args.input}")
        try:
            # arg ->dict
            opt = vars(args)
            Logger.debug(opt)
            try:
                result = create_text_v2(opt)
            except Exception as e:
                Logger.error(f"create_text error create_text_v2 in {e}")
                raise Exception("create_text error")
            if result is None:
                return False
            options = result.get("options", {})
            output_text = result.get("output_text", [])
            yml = result.get("yml", {})
            output_filename = yml.get("options", {}).get("output")
            if isinstance(output_filename, str):  # Replace '==' with 'is'
                Logger.debug(f"output_filename: {output_filename}")
                try:
                    with open(output_filename, "w", encoding="utf-8") as f:
                        if isinstance(output_text, str):
                            text = output_text
                        else:
                            if not options.get("verbose"):
                                text = copy.deepcopy(output_text)
                                for t in text:
                                    if t.get("verbose"):
                                        del t["verbose"]
                            else:
                                # verbose mode
                                if not args.v1json:
                                    text = output_text
                                else:
                                    # conver v2 to v1
                                    Logger.debug("v1json")
                                    text = copy.deepcopy(output_text)
                                    for t in text:
                                        verbose = t.get("verbose", {})
                                        variables = verbose.get("variables", {})
                                        for variable in variables:
                                            if len(variables[variable]) > 0:
                                                if "variables" not in t:
                                                    t["variables"] = {}
                                                item = variables[variable][0]
                                                t["variables"][variable] = item
                                        info = verbose.get("info", {})
                                        for item in info:
                                            if len(info[item]) > 0:
                                                if "info" not in t:
                                                    t["info"] = {}
                                                t["info"][item] = info[item][0]
                                        if "verbose" in t:
                                            del t["verbose"]
                                        if "array" in t:
                                            del t["array"]
                            if args.prompt:
                                new_text = []
                                for item in text:
                                    new_text.append(item.get("prompt", ""))
                                text = new_text
                            if args.v1json:
                                text = json.dumps(text, indent=2)  # escape unicode
                            else:
                                if args.json_escape:
                                    text = json.dumps(text, indent=2)
                                else:
                                    text = json.dumps(
                                        text, ensure_ascii=False, indent=2
                                    )
                        f.write(text)
                except Exception as e:
                    Logger.error(f"output error {e}")
                    raise Exception("output error")
                    return False
                Logger.info(f"outputed file creat {output_filename}")
        except Exception as e:
            Logger.error(f"create_text error create_text_v2 in {e}")
            return False

    elif args.api_input_json:
        options = {}
        yml = {}
        with open(args.api_input_json, "r", encoding="utf-8") as f:
            output_text = json.loads(f.read())
            # if v1josn conver from v2 to v1
            if args.v1json:
                Logger.debug("v1json")
                for t in output_text:
                    if "verbose" in t:
                        verbose = t["verbose"]
                        variables = verbose.get("variables", {})
                        info = verbose.get("info", {})
                        t["variables"] = copy.deepcopy(variables)
                        t["info"] = copy.deepcopy(info)
                        del t["verbose"]
    else:
        Logger.error("option error, no input file")
        raise Exception("option error")

    opt = {}

    opt["save_extend_meta"] = args.save_extend_meta
    opt["image_type"] = args.image_type
    opt["image_quality"] = args.image_quality

    if options.get("filename_pattern"):
        args.api_filename_pattern = (
            args.api_filname_pattern or options["filename_pattern"]
        )
    if args.api_filename_pattern is not None:
        opt["filename_pattern"] = args.api_filename_pattern

    if args.num_length is not None:
        opt["num_length"] = args.num_length

    if args.api_userpass is not None:
        opt["userpass"] = args.api_userpass

    if args.num_once is not None:
        opt["num_once"] = args.num_once

    if "command" in yml:
        opt["command"] = yml["command"]

    if "info" in yml:
        opt["info"] = yml["info"]

    if args.api_mode:
        sd_model = args.api_set_sd_model or options.get("sd_model")
        sd_vae = args.api_set_sd_vae or options.get("sd_vae", "Automatic")
        opt["sd_model"] = sd_model
        opt["sd_vae"] = sd_vae
        opt["base_url"] = args.api_base
        if sd_model is not None:
            api.set_sd_model(base_url=args.api_base, sd_model=sd_model, sd_vae=sd_vae)
        # api.init()
        Logger.verbose("api mode")
        Logger.verbose(f"base_url: {args.api_base} output_dir: {args.api_output_dir}")
        Logger.verbose(f"output_text: {output_text} opt: {opt}")
        result = txt2img(
            output_text, base_url=args.api_base, output_dir=args.api_output_dir, opt=opt
        )
        Logger.debug(result)
        if not result:
            return False
        # api.shutdown()
    elif args.api_comfy:
        import modules.comfyui as comfyui

        sd_model = args.api_set_sd_model or options.get("sd_model")
        sd_vae = args.api_set_sd_vae or options.get("sd_vae", "None")
        if sd_vae == "Automatic":
            sd_vae = None
        opt["sd_model"] = sd_model
        opt["sd_vae"] = sd_vae
        opt["save_image"] = save_image
        result = comfyui.ComufyClient.txt2img(
            output_text,
            hostname=args.api_base,
            output_dir=args.api_output_dir,
            options=opt,
        )

        Logger.debug(result)
        if not result:
            return False
    return True


def run_from_args(command_args=None):
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        default=None,
        help="input promptfile or image file for img2img",
    )
    parser.add_argument(
        "--append-dir",
        type=str,
        default="./appends",
        help="direcory of input append prompt files",
    )
    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="direcory of output file of prompt list file",
    )

    parser.add_argument(
        "--json", type=bool, nargs="?", const=True, default=False, help="output JSON"
    )

    parser.add_argument(
        "--api-mode",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="output api force set --json",
    )

    parser.add_argument(
        "--api-base",
        type=str,
        default="http://127.0.0.1:7860",
        help="direct call api e.g http://127.0.0.1:7860",
    )

    parser.add_argument(
        "--api-userpass", type=str, default=None, help="API username:password"
    )

    parser.add_argument(
        "--api-output-dir",
        type=str,
        default="outputs",
        help="api output images directory",
    )

    parser.add_argument(
        "--api-input-json",
        type=str,
        default=None,
        help="api direct inputs from a json file",
    )

    parser.add_argument(
        "--api-filename-pattern",
        type=str,
        default=None,
        help="api outputs filename pattern default: [num]-[seed]",
    )

    parser.add_argument(
        "--max-number",
        type=int,
        default=-1,
        help="override option.number for yaml mode",
    )

    parser.add_argument(
        "--num-length",
        type=int,
        default=None,
        help="override seaquintial number length for filename : default 5",
    )

    parser.add_argument(
        "--api-filename-variable",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="replace variables use filename, obsolete option",
    )

    parser.add_argument(
        "--json-verbose",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="verbose file output mode replace from --api-filename-variable option",
    )

    parser.add_argument(
        "--num-once",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="Search once file number",
    )
    parser.add_argument(
        "--api-set-sd-model",
        type=str,
        default=None,
        help='Change sd model "[Filename]" e.g. wd-v1-3 for "wd-v1-3.ckpt"',
    )

    parser.add_argument(
        "--api-set-sd-vae",
        type=str,
        default="Automatic",
        help='Change sd vae "[Filename]" e.g. "Anything-V3.0.vae.pt", None is not using VAE',
    )

    #    --command_override="width=768, height=1024,"....
    parser.add_argument(
        "--override",
        type=str,
        nargs="*",
        default=None,
        help='command oveeride ex) "width=768, height=1024"',
    )
    parser.add_argument(
        "--info", type=str, nargs="*", default=None, help="add infomation"
    )
    parser.add_argument(
        "--save-extend-meta",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="save extend meta data",
    )
    parser.add_argument(
        "--image-type", type=str, default="png", help="image type jpg or png"
    )
    parser.add_argument(
        "--image-quality", type=int, default=80, help="image quality 1-100"
    )

    # img2img

    parser.add_argument(
        "--api-type",
        type=str,
        default="txt2img",
        help='call API type "txt2img", "img2img", "interrogate" default txt2img',
    )

    parser.add_argument(
        "--interrogate",
        type=str,
        default=None,
        help='If an image does not have prompt, it uses alternative interrogate API or api-type="interrogate". model "clip" or "deepdanbooru"',
    )

    parser.add_argument(
        "--alt-image-dir",
        type=str,
        default=None,
        help="Alternative input image files diretory for img2img",
    )

    parser.add_argument(
        "--mask-dirs", type=str, default=None, help="Mask images directory for img2img"
    )

    parser.add_argument(
        "--mask-blur", type=int, default=None, help="Mask blur for img2img"
    )

    # profiles

    parser.add_argument(
        "--profile",
        type=str,
        default=None,
        help="profile for create prompt, profile is override yml",
    )

    # comfyui

    parser.add_argument(
        "--api-comfy-save",
        type=str,
        default="save",
        help="on save place for comfyui api ui, save, both",
    )

    parser.add_argument(
        "--debug", type=bool, nargs="?", const=True, default=False, help="debug mode"
    )

    parser.add_argument(
        "--verbose", type=bool, nargs="?", const=True, default=False, help="verbose"
    )

    parser.add_argument(
        "--v1json",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="output v1 json",
    )
    parser.add_argument(
        "--prompt",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="output prompt only",
    )

    parser.add_argument(
        "--json-escape",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="multibyte escaped json",
    )

    # comfyui
    parser.add_argument(
        "--api-comfy",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="use comfyui api alternative to webui",
    )

    args = parser.parse_args(command_args)
    if args.debug:
        Logger.print_levels = [
            "info",
            "warning",
            "error",
            "critical",
            "verbose",
            "debug",
        ]
    if args.verbose:
        Logger.print_levels = ["info", "warning", "error", "critical", "verbose"]
    if args.input is None and not (args.api_mode and args.api_input_json is not None):
        parser.print_help()
        Logger.info("need [input] or --api-mode --api_input_json [filename]")
        return False
    return main(args)


if __name__ == "__main__":
    try:
        result = run_from_args()
        if not result:
            print("Not result Error")
            exit(1)
    except Exception as e:
        print(f"Error, help is --help option {e}")
        exit(1)
