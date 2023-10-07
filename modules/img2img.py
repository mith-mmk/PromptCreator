import json
import os

import modules.api as api
from modules.interrogate import interrogate
from modules.parse import create_img2json
from modules.save import save_img

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


def img2txt2img(
    imagefiles,
    overrides=None,
    base_url="http://127.0.0.1:8760",
    output_dir="./outputs",
    opt={},
):
    base_url = api.normalize_base_url(base_url)
    url = base_url + "/sdapi/v1/txt2img"
    progress = base_url + "/sdapi/v1/progress?skip_current_image=true"
    print("Enter API, connect", url)
    dir = output_dir
    opt["dir"] = output_dir
    print("output dir", dir)
    os.makedirs(dir, exist_ok=True)
    #    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(imagefiles)

    print(f"API loop count is {count} times")
    print("")
    flash = ""
    if opt.get("userpass"):
        userpass = opt.get("userpass")
    else:
        userpass = None
    for n, imagefile in enumerate(imagefiles):
        api.share["line_count"] = 0
        print(flash, end="")
        print(f"\033[KBatch {n + 1} of {count}")
        item = create_img2json(imagefile)
        del item["mask_blur"]
        del item["inpainting_fill"]
        del item["inpaint_full_res"]
        del item["inpaint_full_res_padding"]
        if overrides is not None:
            for key, value in overrides.items():
                item[key] = value
        payload = json.dumps(item)
        response = api.request_post_wrapper(
            url,
            data=payload,
            progress_url=progress,
            base_url=base_url,
            userpass=userpass,
        )
        if response is None:
            print("http connection - happening error")
            raise Exception("http connection - happening error")
        if response.status_code != 200:
            print("\033[KError!", response.status_code, response.text)
            print("\033[2A", end="")
            continue

        r = response.json()
        prt_cnt = save_img(r, opt=opt)
        if "line_count" in api.share:
            prt_cnt += api.share["line_count"]
            api.share["line_count"] = 0
        flash = f"\033[{prt_cnt}A"
    print("")


def img2img(
    imagefiles,
    overrides=None,
    base_url="http://127.0.0.1:8760",
    output_dir="./outputs",
    opt={},
):
    base_url = api.normalize_base_url(base_url)
    url = base_url + "/sdapi/v1/img2img"
    progress = base_url + "/sdapi/v1/progress?skip_current_image=true"
    print("Enter API, connect", url)
    dir = output_dir
    opt["dir"] = output_dir
    print("output dir", dir)
    os.makedirs(dir, exist_ok=True)
    #    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(imagefiles)

    print(f"API loop count is {count} times")
    print("")
    flash = ""
    alt_image_dir = opt.get("alt_image_dir")
    mask_image_dir = opt.get("mask_dir")

    if opt.get("userpass"):
        userpass = opt.get("userpass")
    else:
        userpass = None

    for n, imagefile in enumerate(imagefiles):
        api.share["line_count"] = 0
        print(flash, end="")
        print(f"\033[KBatch {n + 1} of {count}")
        item = create_img2json(imagefile, alt_image_dir, mask_image_dir, base_url)
        if opt.get("interrogate") is not None and (
            item.get("prompt") is None or opt.get("force_interrogate")
        ):
            print("\033[KInterrogate from an image....")
            api.share["line_count"] += 1
            try:
                result = interrogate(imagefile, base_url, model=opt.get("interrogate"))
                if result.status_code == 200:
                    item["prompt"] = result.json()["caption"]
            except BaseException as e:
                print("itterogate failed", e)
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
            else:
                override = overrides
            override_settings = {}
            if "model" in override:
                model = api.get_sd_model(
                    sd_model=override["model"], base_url=base_url, sd_vae=None
                )
                del override["model"]
                override_settings["sd_model_checkpoint"] = model.title
            if "vae" in override:
                vae = api.get_vae(base_url=base_url, vae=override["vae"])
                del override["vae"]
                override_settings["sd_vae"] = vae.title
            if "clip_skip" in override:
                override_settings["CLIP_stop_at_last_layers"] = override["clip_skip"]
                del override["clip_skip"]
            if "ensd" in override:
                override_settings["eta_noise_seed_delta"] = override["ensd"]
                del override["ensd"]
            if override_settings != {}:
                override["override_settings"] = override_settings
            for key, value in override.items():
                if value is not None:
                    item[key] = value

        # Why is an error happening? json=payload or json=item
        payload = json.dumps(item)
        response = api.request_post_wrapper(
            url,
            data=payload,
            progress_url=progress,
            base_url=base_url,
            userpass=userpass,
        )

        if response is None:
            print("http connection - happening error")
            raise Exception("http connection - happening error")
        if response.status_code != 200:
            print("\033[KError!", response.status_code, response.text)
            print("\033[2A", end="")
            continue

        r = response.json()
        prt_cnt = save_img(r, opt=opt)
        if "line_count" in api.share:
            prt_cnt += api.share["line_count"]
            api.share["line_count"] = 0
        flash = f"\033[{prt_cnt}A"
    print("")


# 2022-11-07 cannot run yet 2022-11-12 running?]
