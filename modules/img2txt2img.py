import modules.api as api
from modules.logger import getDefaultLogger
from modules.parse import create_img2txt
from modules.txt2img import txt2img

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
    params = []
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

            if "override_settings" not in param:
                param["override_settings"] = {}

            overrideSettings = param.get("override_settings")

            # If infomation VAE is not filename, get from model name to vae filename dict
            if "sd_vae" not in overrideSettings:
                modelHash = overrideSettings.get("sd_model_checkpoint")
                if modelHash in modeldict:
                    try:
                        modelName = modeldict[modelHash]["model_name"]
                    except Exception:
                        modelName = modelHash
                    info = models.get(modelName, None)
                    if type(info) is list:
                        vae = info[0]
                    else:
                        vae = info
                    if vae is not None:
                        Logger.warning(
                            f"Model {modelName}'s vae not found, use default vae"
                        )
                        param["override_settings"]["sd_vae"] = vae
                else:
                    Logger.warning(f"Model hash {modelHash} not found, use default vae")
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

            if "seed" in param:
                if int(param["seed"]) >= 0:
                    param["seed"] = int(param["seed"]) + seed_diff
                else:
                    Logger.warning("Seed is illegal")
                    param["seed"] = -1
            else:
                Logger.warning("No seed in param")
                param["seed"] = -1

            params.append(param)
        except Exception as e:
            Logger.error(f"Failed to create img2txt params {e}")
            continue
    Logger.info("txt2img start")
    if not dry_run:
        txt2img(params, base_url=base_url, output_dir=output_dir, opt=opt)
    else:
        Logger.info(f"Dry run {params}")
