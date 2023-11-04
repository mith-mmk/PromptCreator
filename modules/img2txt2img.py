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

            for key in overrides:
                param[key] = overrides[key]

            if "seed" in param:
                if int(param["seed"]) >= 0:
                    param["seed"] = int(param["seed"]) + seed_diff
                else:
                    Logger.warning("Seed is illegal")
                    param["seed"] = -1
            else:
                Logger.warning("No seed in param")
                param["seed"] = -1
            overrideSettings = param.get("override_settings")

            # If infomation VAE is not filename, get from model name to vae filename dict
            if overrideSettings is None:
                if "sd_vae" in overrideSettings:
                    modelHash = overrideSettings.get("sd_model_checkpoint")
                    if modelHash in modeldict:
                        modelName = modeldict[modelHash]["model_name"]
                        vae = models.get(modelName, [None])[0]
                        if vae is not None:
                            param["override_settings"]["sd_vae"] = vae
            params.append(param)
        except Exception as e:
            Logger.error(f"Failed to create img2txt params {e}")
            continue
    Logger.info("txt2img start")
    if not dry_run:
        txt2img(params, base_url=base_url, output_dir=output_dir, opt=opt)
    else:
        Logger.info(f"Dry run {params}")
