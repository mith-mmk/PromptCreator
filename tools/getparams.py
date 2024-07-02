import argparse
import csv
import glob
import json
import os

import httpx

import modules.api as api
from modules.parse import create_img2txt


def get_sd_models(
    base_url="http://127.0.0.1:7860",
):
    models = {}
    headers = {
        "Content-Type": "application/json",
    }
    base_url = api.normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-models"
    try:
        res = httpx.get(model_url, headers=headers, timeout=10)
        models = res.json()
    except Exception:
        print("Failed to get models")
    return models


def main():
    host = "http://localhost:7860"

    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument(
        "filename",
        help="filename",
        type=str,
        nargs="?",
    )
    parser.add_argument("-o", "--output", help="output filename")
    parser.add_argument("-m", "--modelfile", help="model name", default="models.csv")
    parser.add_argument("-H", "--host", help="host", default=host)
    parser.add_argument("-b", "--batch_size", help="batch size", default=3, type=int)
    parser.add_argument("-i", "--n_iter", help="n_iter", default=2, type=int)
    parser.add_argument(
        "-R", "--enable_hr", help="enable hr", action="store_true", default=False
    )
    parser.add_argument(
        "-D", "--strength", help="denoising strength", default=0.5, type=float
    )
    parser.add_argument("-d", "--seed-diff", help="seed diff", default=0, type=int)
    parser.add_argument("-u", "--upscaler", help="upscaler override", default=None)
    parser.add_argument(
        "-s", "--scale", help="hr_scale overridse", default=None, type=float
    )
    parser.add_argument(
        "-S", "--steps", help="hr_steps override", default=None, type=int
    )
    parser.add_argument(
        "-V",
        "--default-vae",
        help="default vae",
        default="clearvae_main.safetensors",
        type=str,
        dest="vae",
    )

    args = parser.parse_args()
    # override = args.override
    # print(override)

    modelsFile = args.modelfile
    modelHash = get_sd_models(args.host)
    modeldict = {}
    for model in modelHash:
        modeldict[model["hash"]] = model

    models = {}
    if os.path.exists(modelsFile):
        with open(modelsFile, "r") as f:
            csv_reader = csv.reader(f)
            for row in csv_reader:
                models[row[0]] = row[1:]

    files = args.filename

    if type(files) is not list:
        files = [files]

    imgfiles = []
    for filename in files:
        if not os.path.exists(filename):
            print(f"File not found: {filename}")
        if os.path.isdir(filename):
            imgfiles.extend(glob.glob(os.path.join(filename, "*.jpg")))
            imgfiles.extend(glob.glob(os.path.join(filename, "*.png")))
        else:
            imgfiles.append(filename)

    params = []

    for imgfile in imgfiles:
        print(f"Processing {imgfile}")
        param = create_img2txt(imgfile)

        # overrride settings
        param["enable_hr"] = args.enable_hr
        if param["enable_hr"]:
            param["hr_scale"] = args.scale or 2
            param["hr_second_pass_steps"] = args.steps or 0
            param["hr_upscaler"] = args.upscaler or "R-ESRGAN 4x+ Anime6B"
            if args.strength is not None:
                param["denoising_strength"] = args.strength
        else:
            # img2img -> txt2img
            if "firstphase_width" in param:
                param["width"] = param["firstphase_width"]
                del param["firstphase_width"]
            if "firstphase_height" in param:
                param["height"] = param["firstphase_height"]
                del param["firstphase_height"]

        param["batch_size"] = args.batch_size
        param["n_iter"] = args.n_iter
        param["seed"] = int(param["seed"]) + args.seed_diff
        params.append(param)
        modelHash = param["override_settings"]["sd_model_checkpoint"]
        if param["override_settings"].get("sd_vae") is None:
            try:
                modelName = modeldict[modelHash]["model_name"]
            except Exception:
                modelName = modelHash
            opt = models.get(modelName)
            if opt is None:
                print(f"Model {modelName} not found")
                vae = args.default_vae
            else:
                vae = models.get(modelName, [])[0]
        param["override_settings"]["sd_vae"] = vae

    if args.output:
        with open(args.output, "w") as f:
            json.dump(params, f, indent=2, ensure_ascii=False)
    else:
        print(json.dumps(params, indent=2, ensure_ascii=False))
    print("Done")


main()
