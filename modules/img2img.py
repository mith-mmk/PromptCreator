import json
import os

import modules.api as api
import modules.logger as logger
import modules.share as share
from modules.interrogate import interrogate
from modules.parse import create_img2json
from modules.save import DataSaver
from modules.util import get_part

Logger = logger.getDefaultLogger()
# Call img2img API from webui, it has many bugs


# img2txt2img is img to text and txt2img for resizing
# also override uses img2txt2img
"""
  "enable_hr": true,
  "hr_scale": 2.25,
  "hr_upscaler": "Your UPSCALER",
  "hr_second_pass_steps": 10,
  "hr_checkpoint_name": "string",
  "hr_sampler_name": "string",
  "hr_prompt": "",
  "hr_negative_prompt": "",
"""


def img2img(
    imagefiles,
    overrides=None,
    base_url="http://127.0.0.1:7860",
    output_dir="./outputs",
    opt={},
):
    base_url = api.normalize_base_url(base_url)
    url = base_url + "/sdapi/v1/img2img"
    progress = base_url + "/sdapi/v1/progress?skip_current_image=true"
    Logger.info("Enter API, connect", url)
    dir = output_dir
    saver = DataSaver()
    opt["dir"] = output_dir
    Logger.info("output dir", dir)
    os.makedirs(dir, exist_ok=True)
    #    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(imagefiles)

    Logger.info(f"API loop count is {count} times")
    Logger.info("")
    flash = ""
    alt_image_dir = opt.get("alt_image_dir")
    mask_image_dir = opt.get("mask_dir")
    if opt.get("userpass"):
        userpass = opt.get("userpass")
    else:
        userpass = None

    res = []
    for n, imagefile in enumerate(imagefiles):
        try:
            Logger.debug(f"imagefile is {imagefile}")

            share.set("line_count", 0)
            print(flash, end="")
            print(f"\033[KBatch {n + 1} of {count}")
            item = create_img2json(imagefile, alt_image_dir, mask_image_dir)
            if opt.get("interrogate") is not None and (
                item.get("prompt") is None or opt.get("force_interrogate")
            ):
                print("\033[KInterrogate from an image....")
                share.set("line_count", share.get("line_count") + 1)
                try:
                    result = interrogate(
                        imagefile, base_url, model=opt.get("interrogate")
                    )
                    if result.status_code == 200:
                        item["prompt"] = result.json()["caption"]
                except BaseException as e:
                    Logger.error("itterogate failed", e)
            if "extend" in opt:
                # extend = opt['extend']
                del opt["extend"]
                # if 'variable' in extend:
                #   opt['variable'] = extend['variable']
                # if 'info' in extend:
                #   opt['info'] = extend['info']
                # if 'file_pettern' in extend and opt.get('use_extend_file_pettern'):
                #   opt['file_pettern'] = extend['file_pettern']

            if overrides is not None:
                if type(overrides) is list:
                    override = overrides[n]
                elif type(overrides) is dict:
                    override = overrides
                else:
                    override = {}
                override_settings = {}
                if "model" in override:
                    model = api.get_sd_model(
                        sd_model=override["model"], base_url=base_url
                    )
                    del override["model"]
                    if model is None:
                        continue
                    override_settings["sd_model_checkpoint"] = model["title"]
                if "vae" in override:
                    vae = api.get_vae(base_url=base_url, vae=override["vae"])
                    del override["vae"]
                    if vae is None:
                        continue
                    override_settings["sd_vae"] = vae.title
                if "clip_skip" in override:
                    override_settings["CLIP_stop_at_last_layers"] = override[
                        "clip_skip"
                    ]
                    del override["clip_skip"]
                if "ensd" in override:
                    override_settings["eta_noise_seed_delta"] = override["ensd"]
                    del override["ensd"]
                if override_settings != {}:
                    override["override_settings"] = override_settings
                for key, value in override.items():
                    if value is not None:
                        item[key] = value
            if item.get("enable_hr"):
                if "denoising_strength" not in item:
                    item["denoising_strength"] = 0.5

            # Why is an error happening? json=payload or json=item
            payload = json.dumps(item)
            del item["init_images"]
            Logger.debug(json.dumps(item, indent=2))

            response = api.request_post_wrapper(
                url,
                data=payload,
                progress_url=progress,
                base_url=base_url,
                userpass=userpass,
            )

            if response is None:
                Logger.error("http connection - happening error")
                raise Exception("http connection - happening error")
            if response.status_code != 200:
                print("\033[KError!", response.status_code, response.text)
                print("\033[2A", end="")
                res.append({"imagefile": imagefile, "success": False})
                continue

            r = response.json()
            opt["filepart"] = get_part(imagefile)
            prt_cnt = saver.save_images(r, opt=opt)
            if share.get("line_count"):
                prt_cnt += share.get("line_count")
                share.set("line_count", 0)
            res.append({"imagefile": imagefile, "success": True})
            flash = f"\033[{prt_cnt}A"
        except KeyboardInterrupt:
            Logger.error("KeyboardInterrupt")
            res.append({"imagefile": imagefile, "success": False})
            break
        except BaseException as e:
            Logger.error(f"img2img failed {imagefile}, {e}")
            res.append({"imagefile": imagefile, "success": False, "error": e})
            continue
    print("")
    return res


# 2022-11-07 cannot run yet 2022-11-12 running?]
