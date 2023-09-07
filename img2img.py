# img2img api test inpritation,function specifications are change after commit
from modules.img2img import img2img
from modules.api import set_sd_model
import os

import argparse


def run_from_args_img2img(command_args=None):
    parser = argparse.ArgumentParser(argument_default=None)

    parser.add_argument(
        "--output",
        type=str,
        default=None,
        help="direcory of output file of prompt list file",
    )
    parser.add_argument(
        "--api-base", type=str, default="http://127.0.0.1:7860", help="api base url"
    )
    parser.add_argument("--seed", type=int, default=None, help="override seed")

    parser.add_argument("--steps", type=int, default=None, help="override steps")
    parser.add_argument(
        "--cfg_scale", type=int, default=None, help="override cfg_scale"
    )

    parser.add_argument("--width", type=int, default=None, help="override width")
    parser.add_argument("--height", type=int, default=None, help="override height")

    parser.add_argument("--n_iter", type=int, default=None, help="override n_iter")
    parser.add_argument(
        "--batch_size", type=int, default=None, help="override batch_size"
    )
    parser.add_argument(
        "--denoising_strength",
        type=float,
        default=None,
        help="override denoising_strength",
    )

    parser.add_argument(
        "--interrogate",
        type=str,
        default=None,
        help='If an image does not have prompt, it uses alternative interrogate API. model "clip" or "deepdanbooru"',
    )

    parser.add_argument("--sampler_index", type=str, default=None, help="sampler")

    parser.add_argument(
        "--sd-model", type=str, default=None, help="Initalize change sd model"
    )

    parser.add_argument(
        "--sd-vae",
        type=str,
        default="automatic",
        help="Initalize change sd model vae ex) Anything-V3.0.vae.pt",
    )

    parser.add_argument(
        "--alt-image-dir",
        type=str,
        default=None,
        help="Alternative input image files diretory",
    )

    parser.add_argument(
        "--mask-dir", type=str, default=None, help="Mask images directory"
    )

    parser.add_argument("--mask_blur", type=int, default=None, help="Mask blur")

    parser.add_argument(
        "--inpainting_fill", type=int, default=None, help="inpainting fill"
    )

    parser.add_argument(
        "--inpaint_full_res", type=bool, default=None, help="inpaint full res padding"
    )

    parser.add_argument(
        "--inpaint_full_res_padding",
        type=int,
        default=None,
        help="inpaint full res padding",
    )

    parser.add_argument(
        "--inpainting_mask_invert",
        type=int,
        default=None,
        help="inpainting_mask_invert",
    )

    parser.add_argument(
        "--filename-pattern",
        type=str,
        default=None,
        help="Filename Patter default [num]-[seed]",
    )

    parser.add_argument(
        "--api-filename-variables",
        type=bool,
        nargs="?",
        const=True,
        default=False,
        help="replace variables use filename",
    )

    parser.add_argument("input", type=str, nargs="+", help="input files or dirs")

    args = parser.parse_args(command_args)

    if type(args.input) is str:
        filenames = [args.input]
    else:
        filenames = args.input
    base_url = args.api_base
    output_dir = args.output or "./outputs"

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

    overrides = {}

    dicted_args = vars(args)
    for item in items:
        if dicted_args.get(item):
            overrides[item] = dicted_args[item]

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
        set_sd_model(
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
    except Exception:
        return False
    return True


if __name__ == "__main__":
    try:
        result = run_from_args_img2img()
        if not result:
            exit(1)
    except Exception:
        exit(1)


# - multiple images impl
# - overrides maker from yaml
# - image mask impl
