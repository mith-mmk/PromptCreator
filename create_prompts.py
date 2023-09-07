#!/usr/bin/env python3
# !pip install pyyaml
# !pip install Pillow
# !pip install httpx

# version 0.8 (C) 2022-3 MITH@mmk  MIT License

import argparse
import json
import os
import modules.api as api
from modules.img2img import img2img
from modules.txt2img import txt2img
from modules.interrogate import interrogate
from modules.prompt import expand_arg, create_text


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
        print("no exit files")
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
        print(e)
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
        print(result)
        if result.status_code == 200:
            print(filename)
            print(result.json()["caption"])
        else:
            print(result.text)
            print("Is Web UI replace newest version?")


def main(args):
    if args.api_mode:
        if args.api_type == "img2img":
            img2img_from_args(args)
            return
        if args.api_type == "interrogate":
            interrogate_from_args(args)
            return

    if args.input is not None:
        result = create_text(args)
        options = result["options"]
        output_text = result["output_text"]
        yml = result["yml"]
    elif args.api_input_json:
        options = {}
        yml = {}
        with open(args.api_input_json, "r", encoding="utf-8") as f:
            output_text = json.loads(f.read())
    else:
        print("option error")
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
        sd_vae = args.api_set_sd_vae or options.get("sd_vae")
        opt["sd_model"] = sd_model
        opt["sd_vae"] = sd_vae
        opt["base_url"] = args.api_base
        if sd_model is not None:
            api.set_sd_model(base_url=args.api_base, sd_model=sd_model, sd_vae=sd_vae)
        api.init()
        result = txt2img(
            output_text, base_url=args.api_base, output_dir=args.api_output_dir, opt=opt
        )
        if not result:
            return False
        api.shutdown()
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
        help="replace variables use filename",
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
        "--mask_blur", type=int, default=None, help="Mask blur for img2img"
    )

    args = parser.parse_args(command_args)
    if args.input is None and not (args.api_mode and args.api_input_json is not None):
        parser.print_help()
        print("need [input] or --api-mode --api_input_json [filename]")
        return False
    return main(args)


if __name__ == "__main__":
    try:
        result = run_from_args()
        if not result:
            exit(1)
    except Exception:
        exit(1)
