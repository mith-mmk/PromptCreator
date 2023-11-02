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

        param["seed"] = int(param["seed"]) + seed_diff
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
    Logger.info("txt2img start")
    txt2img(params, base_url=base_url, output_dir=output_dir, opt=opt)
