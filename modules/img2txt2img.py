import os

import modules.api as api
from modules.logger import getDefaultLogger
from modules.parse import create_img2txt
from modules.txt2img import txt2img
from modules.util import get_part

Logger = getDefaultLogger()


def img2txt2img(
    imagefiles,
    base_url="http://127.0.0.1:7860",
    overrides={},
    seed_diff=0,
    models={},  # {modelname: vae_filename, ...}
    output_dir="./outputs",
    opt={},
):
    dry_run = opt.get("dry_run", False)
    # modelHash
    modelHash = api.get_sd_models(base_url)

    if modelHash is None:
        Logger.error("Failed to get models")
        # return False
        modelHash = []
    modeldict = {}
    for model in modelHash:
        modeldict[model["hash"]] = model
        modeldict[model["model_name"]] = model
    modelsKeys = modeldict.keys()

    params = []
    res = []
    for imgfile in imagefiles:
        Logger.info(f"Processing {imgfile}")

        try:
            param = create_img2txt(imgfile)

            # If enable_hr is True, set width and height to firstphase_width and firstphase_height
            if param.get("enable_hr", False):
                if "firstphase_width" in param:
                    param["width"] = param["firstphase_width"]
                    del param["firstphase_width"]
                if "firstphase_height" in param:
                    param["height"] = param["firstphase_height"]
                    del param["firstphase_height"]
                if "denoising_strength" not in param:
                    param["denoising_strength"] = 0.5

            overrideSettings = param.get("override_settings")

            Logger.debug(f"Override settings: {overrideSettings}")

            if overrideSettings is None:
                overrideSettings = {}
                param["override_settings"] = overrideSettings

            def search_model(modelHash):
                for key in modelsKeys:
                    if isinstance(key, str):
                        if modelHash.endswith(key):
                            return modeldict[key]["model_name"]
                return ""

            # If infomation VAE is not filename, get from model name to vae filename dict
            if "sd_vae" not in overrideSettings:
                modelHash = overrideSettings.get("sd_model_checkpoint")
                if search_model(modelHash) != "":
                    try:
                        modelName = search_model(modelHash)
                    except Exception:
                        modelName = modelHash
                    info = models.get(modelName, None)
                    if type(info) is list:
                        vae = info[0]
                    else:
                        vae = info
                    if vae is not None:
                        Logger.warning(
                            f"Model hash for VAE is not found, use default vae"
                        )
                        param["override_settings"]["sd_vae"] = vae
                else:
                    Logger.warning(
                        f"Model hash {modelHash} for VAE not found, use default vae"
                    )
                    if "sd_vae" in opt:
                        param["override_settings"]["sd_vae"] = opt["sd_vae"]
            else:
                if "sd_checkpoint" in opt:
                    param["override_settings"]["sd_model_checkpoint"] = opt["model"]
                if "sd_vae" in opt:
                    param["override_settings"]["sd_vae"] = opt["sd_vae"]

            for key in overrides:
                if key != "override_settings":
                    param[key] = overrides[key]
                else:
                    for key2 in overrides[key]:
                        param[key][key2] = overrides[key][key2]
            if opt.get("rotate", False):
                temp = param["width"]
                param["width"] = param["height"]
                param["height"] = temp

            if "seed" in param:
                if int(param["seed"]) >= 0:
                    param["seed"] = int(param["seed"]) + seed_diff
                else:
                    Logger.warning("Seed is illegal")
                    param["seed"] = -1
            else:
                Logger.warning("No seed in param")
                param["seed"] = -1

            param["filepart"] = get_part(imgfile)
            params.append(param)
        except KeyboardInterrupt:
            Logger.info("Interrupted")
            break
        except Exception as e:
            Logger.error(f"Failed to create img2txt params {e}")
            res.append({"imgfile": imgfile, "success": False, "error": e})
            continue
    if param.get("override_settings", {}):
        # if "forge_additional_modules" in param["override_settings"]: get module names
        if "forge_additional_modules" in param["override_settings"]:
            modules = api.get_modules(
                base_url=base_url,
                modules=param["override_settings"]["forge_additional_modules"],
            )

            if modules is not None:
                models = []

                for module in modules:
                    models.append(module["model_name"])
                param["override_settings"]["forge_additional_modules"] = models

    Logger.info(f"{param.get('override_settings', {})}")
    if not dry_run:
        try:
            txt2img(params, base_url=base_url, output_dir=output_dir, opt=opt)
            res.append({"imgfile": imgfile, "success": True})
        except Exception as e:
            Logger.error(f"Failed to call txt2img {e}")
            res.append({"imgfile": imgfile, "success": False, "error": e})
    else:
        Logger.info(f"Dry run {params}")
    return res
