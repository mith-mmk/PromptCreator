import base64
import os
import re

from PIL import Image

import modules.api as api
import modules.share as share
from modules.logger import getDefaultLogger

Logger = getDefaultLogger()


# parsing json from metadata in an image
def create_parameters(parameters_text):
    para = parameters_text.split("\n")
    if len(para) == 1:
        para.append("")
    parameters = {}
    parameters["prompt"] = para[0]
    neg = "Negative prompt: "
    neg_start = 1
    param_start = len(para) - 1
    while para[neg_start][: len(neg)] != neg:
        neg_start += 1
        if neg_start >= len(para):
            break
    if 1 < neg_start:
        for i in range(1, neg_start):
            parameters["prompt"] += " " + para[i]
    if len(para) > neg_start:
        parameters["negative_prompt"] = para[neg_start].replace(neg, "")
        if neg_start + 1 > param_start:
            for i in range(neg_start + 1, param_start):
                parameters["negative_prompt"] += " " + para[i]

    params = para[param_start]

    regex = r'".+?"'
    matches = re.findall(regex, params)
    for match in matches:
        params = params.replace(match, match.replace(",", ":"))
    options = params.split(",")
    for option in options:
        keyvalue = option.split(": ")
        if len(keyvalue) >= 2:
            key = keyvalue[0].strip().replace(" ", "_").lower()
            if key == "size":
                wh = keyvalue[1].split("x")
                parameters["width"] = wh[0]
                parameters["height"] = wh[1]
            elif key == "seed_resize_from":
                wh = keyvalue[1].split("x")
                parameters["seed_resize_from_w"] = wh[0]
                parameters["seed_resize_from_h"] = wh[1]
            elif key == "sampler":
                parameters["sampler_index"] = keyvalue[1]
            elif key == "batch_pos":
                pass
            elif key == "schedule_type":
                parameters["scheduler"] = keyvalue[1]
            elif key == "clip_skip":
                parameters["CLIP_stop_at_last_layers"] = int(keyvalue[1])
            elif key == "ensd":
                parameters["eta_noise_seed_delta"] = int(keyvalue[1])
            elif key == "model_hash":
                parameters["model_hash"] = str(keyvalue[1])
            elif key == "ti_hashes":
                values = {}
                for i in range(1, len(keyvalue), 2):
                    values[keyvalue[i].replace('"', "")] = keyvalue[i + 1].replace(
                        '"', ""
                    )
                parameters["ti_hashes"] = values
            elif key == "comments":
                values = {}
                for i in range(1, len(keyvalue), 2):
                    values[keyvalue[i].replace('"', "")] = keyvalue[i + 1].replace(
                        '"', ""
                    )
            elif key == "vae_hash":
                parameters["vae_hash"] = keyvalue[1]
            else:
                parameters[key] = keyvalue[1]
        else:
            Logger.verbose("unknow", keyvalue)
    return parameters


def imgloader(imagefile, img2img=False):
    image = Image.open(imagefile)
    image.load()
    # if png?
    extend = None
    if imagefile.lower().endswith(".png"):
        if "parameters" in image.info and image.info["parameters"] is not None:
            parameter_text = image.info["parameters"]
            parameters = create_parameters(parameter_text)
            # extend = image.info['expantion']
            # extend = json.loads(extend)
        else:
            parameters = {"width": image.width, "height": image.height}
    elif (
        imagefile.lower().endswith(".jpg")
        or imagefile.lower().endswith(".jpeg")
        or imagefile.lower().endswith(".webp")
    ):
        tiff = image.getexif()
        parameters = {"width": image.width, "height": image.height}
        if tiff is not None:
            endien = "LE" if tiff.endian == "<" else "BE"
            exif = tiff.get_ifd(0x8769)
            if exif:
                if 37510 in exif:
                    user_comment = exif[37510]
                    code = user_comment[:8]
                    parameter_text = None
                    if code == b"ASCII\x00\x00\x00":
                        parameter_text = user_comment[8:].decode("ascii")
                    elif code == b"UNICODE\x00":
                        if endien == "LE":
                            parameter_text = user_comment[8:].decode("utf-16le")
                        else:
                            parameter_text = user_comment[8:].decode("utf-16be")
                    if parameter_text is not None:
                        parameters = create_parameters(parameter_text)
            # if 0x9C9C in tiff:
            #     extend = tiff[0x9C9C].decode('utf-16le')
            #     extend = json.loads(extend)
    if "hires_upscale" in parameters:
        scale = float(parameters["hires_upscale"])
        if scale > 1.0:
            parameters["enable_hr"] = True
    if img2img:
        parameters["width"] = image.width
        parameters["height"] = image.height
    else:
        parameters["width"] = parameters.get("width", image.width)
        parameters["height"] = parameters.get("height", image.height)
    return parameters, extend


# parsing json from image's metadata
def create_img2json(imagefile, alt_image_dir=None, mask_image_dir=None):
    schema = [
        "hires_upscale",
        "prompt",
        "styles",
        # "sampler_name",  # add 2023/10/22  synonim "sampler_index"
        # "sampler_index"  # This option is exception handling
        "scheduler",  # add 2024/07/28 from v1.8 handling
        "seed",
        "subseed",
        "subseed_strength",
        "batch_size",
        "n_iter",
        "steps",
        "cfg_scale",
        "width",
        "height",
        "restore_faces",
        "tiling",
        "negative_prompt",
        # "do_not_save_samples", # this option is not supported
        # "do_not_save_grid", # this option is not supported
        "eta",
        "s_churn",
        "s_tmax",
        "s_tmin",
        "s_noise",
        "sampler",
        "comments",  # add 2023/10/22
        # hires fix
        # "enable_hr",
        "denoising_strength",
        # "firstphase_width",  # obusolete
        # "firstphase_height",  # obusolete
        "seed_resize_from_h",
        "seed_resize_from_w",
        # img2img inpainting only
        "resize_mode",
        "image_cfg_scale",
        "mask",
        "mask_blur_x",
        "mask_blur_y",
        "mask_blur",
        "inpainting_fill",
        "inpaint_full_res",
        "inpaint_full_res_padding",
        "inpainting_mask_invert",
        "initial_noise_multiplier",
        "latent_mask",
        # these option are not used
        # "script_name",
        # "script_args",
        # "send_images",
        # "save_images",
        # "alwayson_scripts"
    ]

    parameters, extend = imgloader(imagefile, img2img=True)

    load_image = imagefile
    if alt_image_dir is not None:
        basename = os.path.basename(imagefile)
        alt_imagefile = os.path.join(alt_image_dir, basename)
        if os.path.isfile(alt_imagefile):
            Logger.info(f"\033[Kbase image use alternative {alt_imagefile}")
            if share.get("line_count") is not None:
                share.set("line_count", share.get("line_count") + 1)
            load_image = alt_imagefile
    with open(load_image, "rb") as f:
        init_image = base64.b64encode(f.read()).decode("ascii")

    json_raw = {}
    json_raw["init_images"] = ["data:image/png;base64," + init_image]
    json_raw["extend"] = extend

    if mask_image_dir is not None:
        basename = os.path.basename(imagefile)
        mask_imagefile = os.path.join(mask_image_dir, basename)
        if os.path.isfile(mask_imagefile):
            with open(mask_imagefile, "rb") as f:
                Logger.info(f"\033[KUse image mask {mask_imagefile}")
                if api.share.get("line_count"):
                    api.share.set("line_count", api.share.get("line_count") + 1)
                mask_image = base64.b64encode(f.read()).decode("ascii")
                json_raw["mask"] = "data:image/png;base64," + mask_image
                json_raw["mask_blur"] = 4
                json_raw["inpainting_fill"] = 0
                json_raw["inpaint_full_res"] = True
                json_raw["inpaint_full_res_padding"] = 0
                json_raw["inpainting_mask_invert"] = 0

    override_settings = {}
    sampler_index = None
    sampler_name = None
    # override settings only return sd_model_checkpoint and CLIP_stop_at_last_layers
    # Automatic1111 1.6.0 use "Add model name to generation information" option in settings
    for key, value in parameters.items():
        if key in schema:
            json_raw[key] = value
        elif key == "sampler_index":
            sampler_index = value
        elif key == "sampler_name":
            sampler_name = value
        elif key == "schedule_type":
            json_raw["scheduler"] = value
        elif key == "hires_sampler":
            json_raw["hr_sampler_name"] = value
        elif key == "hires_checkpoint":
            json_raw["hr_checkpoint_name"] = value
        elif key == "model":
            override_settings["sd_model_checkpoint"] = value
        elif key == "model_hash":
            override_settings["sd_model_checkpoint"] = value
        elif key == "CLIP_stop_at_last_layers":
            override_settings[key] = value
        elif key == "VAE" or key == "vae":
            override_settings["sd_vae"] = value
        elif key == "RNG" or key == "RNG":
            override_settings["randn_source"] = value
    if ("sampler" not in json_raw) and (
        sampler_index is not None or sampler_name is not None
    ):
        json_raw["sampler_index"] = sampler_name or sampler_index

    json_raw["override_settings"] = override_settings
    Logger.debug(json_raw)
    return json_raw


def create_img2params(imagefile):
    parameters, _ = imgloader(imagefile, img2img=True)
    return create_parms(parameters)


# parsing json from image's metadata
def create_parms(parameters):
    schema = [
        "enable_hr",
        "denoising_strength",
        "hr_upscaler",
        "hr_upscale",
        "hr_steps",
        "hr_resize_x",
        "hr_resize_y",
        "prompt",
        "styles",
        "seed",
        "subseed",
        "subseed_strength",
        "batch_size",
        "n_iter",
        "steps",
        "cfg_scale",
        "firstphase_width",
        "firstphase_height",
        "restore_faces",
        "tiling",
        "negative_prompt",
        "eta",
        "s_churn",
        "s_tmax",
        "s_tmin",
        "s_noise",
        "sampler",
    ]

    # convert txt2img parameters to img2img parameters

    if "hires_upscale" in parameters:
        parameters["hr_upscale"] = parameters["hires_upscale"]
        del parameters["hires_upscale"]
    if "hires_steps" in parameters:
        parameters["hr_steps"] = parameters["hires_steps"]
        del parameters["hires_steps"]
    if "hires_upscaler" in parameters:
        parameters["hr_upscaler"] = parameters["hires_upscaler"]
        del parameters["hires_upscaler"]
    if "hires_resize" in parameters:
        h = parameters["height"]
        w = parameters["width"]
        parameters["hr_resize_x"] = h
        parameters["hr_resize_y"] = w
        del parameters["hires_resize"]
        if h > w:
            scale = float(h) / float(w)
            w = 512
            h = int((h * scale + 63) / 64) * 64
            parameters["firstphase_width"] = w
            parameters["firstphase_height"] = h
        else:
            scale = float(w) / float(h)
            h = 512
            w = int(int(h * scale + 63) / 64) * 64
            parameters["firstphase_width"] = w
            parameters["firstphase_height"] = h
    if "hr_upscale" in parameters:
        parameters["firstphase_width"] = int(
            float(parameters["width"]) / float(parameters["hr_upscale"])
        )
        parameters["firstphase_height"] = int(
            float(parameters["height"]) / float(parameters["hr_upscale"])
        )
        del parameters["width"]
        del parameters["height"]
    json_raw = {}
    override_settings = {}
    Logger.debug(schema)
    Logger.debug(parameters)

    sampler_index = None
    sampler_name = None
    # override settings only return sd_model_checkpoint and CLIP_stop_at_last_layers
    # Automatic1111 1.6.0 verion setting is not support VAE HASH tag
    for key, value in parameters.items():
        if key in schema:
            json_raw[key] = value
        elif key == "sampler_index":
            sampler_index = value
        elif key == "sampler_name":
            sampler_name = value
        elif key == "model":
            override_settings["sd_model_checkpoint"] = value
        elif key == "model_hash":
            override_settings["sd_model_checkpoint"] = value
        # Automatic1111 1.6.0 use "Add model name to generation information" option in settings
        elif key == "VAE" or key == "vae":
            override_settings["sd_vae"] = value
        elif key == "CLIP_stop_at_last_layers":
            override_settings[key] = value
    if ("sampler" not in json_raw) and (
        sampler_index is not None or sampler_name is not None
    ):
        json_raw["sampler_index"] = sampler_name or sampler_index

    json_raw["override_settings"] = override_settings
    return json_raw


# parsing json from image's metadata
def create_img2txt(imagefile):
    parameters, _ = imgloader(imagefile)
    return create_infotext(parameters)


def create_infotext(parameters):
    schema = [
        "enable_hr",
        "denoising_strength",
        "sampler_name",
        "sampler_index",
        "scheduler",
        "hr_upscaler",
        "hr_upscale",
        "hr_steps",
        "hr_resize_x",
        "hr_resize_y",
        "prompt",
        "styles",
        "seed",
        "subseed",
        "subseed_strength",
        "batch_size",
        "n_iter",
        "steps",
        "cfg_scale",
        "width",
        "height",
        "firstphase_width",
        "firstphase_height",
        "restore_faces",
        "tiling",
        "negative_prompt",
        "eta",
        "s_churn",
        "s_tmax",
        "s_tmin",
        "s_noise",
        "sampler",
        "sd_vae",
    ]

    # convert txt2img parameters to img2img parameters

    if "hires_upscale" in parameters:
        parameters["hr_upscale"] = parameters["hires_upscale"]
        del parameters["hires_upscale"]
    if "hires_steps" in parameters:
        parameters["hr_steps"] = parameters["hires_steps"]
        del parameters["hires_steps"]
    if "hires_upscaler" in parameters:
        parameters["hr_upscaler"] = parameters["hires_upscaler"]
        del parameters["hires_upscaler"]
    if "hires_resize" in parameters:
        h = parameters["height"]
        w = parameters["width"]
        parameters["hr_resize_x"] = h
        parameters["hr_resize_y"] = w
        del parameters["hires_resize"]
        if h > w:
            scale = float(h) / float(w)
            w = 512
            h = int((h * scale + 63) / 64) * 64
            parameters["firstphase_width"] = w
            parameters["firstphase_height"] = h
        else:
            scale = float(w) / float(h)
            h = 512
            w = int(int(h * scale + 63) / 64) * 64
            parameters["firstphase_width"] = w
            parameters["firstphase_height"] = h

    json_raw = {}
    override_settings = {}
    Logger.debug(schema)
    Logger.debug(parameters)

    sampler_index = None
    sampler_name = None
    # override settings only return sd_model_checkpoint and CLIP_stop_at_last_layers
    # Automatic1111 1.6.0 do not support VAE hash tag use VAE tag but setting check
    for key, value in parameters.items():
        if key in schema:
            json_raw[key] = value
        elif key == "sampler_index":
            sampler_index = value
        elif key == "sampler_name":
            sampler_name = value
        elif key == "model":
            if "sd_model_checkpoint" not in override_settings:
                override_settings["sd_model_checkpoint"] = value
        elif key == "model_hash":
            override_settings["sd_model_checkpoint"] = value
        elif key == "VAE" or key == "vae":
            override_settings["sd_vae"] = value
        elif key == "CLIP_stop_at_last_layers":
            override_settings[key] = value
    if ("sampler" not in json_raw) and (
        sampler_index is not None or sampler_name is not None
    ):
        json_raw["sampler_index"] = sampler_name or sampler_index

    json_raw["override_settings"] = override_settings
    return json_raw
