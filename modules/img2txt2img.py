import json
import os

import modules.api as api
from modules.parse import create_img2params
from modules.save import save_img


def img2txt2img(
    imagefiles,
    overrides=None,
    base_url="http://127.0.0.1:7860",
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
        # Path: modules/img2txt2img.py
        item = create_img2params(imagefile)
        if item is None:
            continue
        item = create_param(item, overrides)

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
        os.remove
        r = response.json()
        prt_cnt = save_img(r, opt=opt)
        if "line_count" in api.share:
            prt_cnt += api.share["line_count"]
            api.share["line_count"] = 0
        flash = f"\033[{prt_cnt}A"
    print("")


def create_param(item, overritesettings):
    for key in overritesettings:
        if key == "override_settings":
            if type(overritesettings[key]) is not dict:
                print("override_settings must be a dict")
                continue
            if "override_settings" not in item:
                item["override_settings"] = {}
            for subkey in overritesettings[key]:
                if overritesettings[key][subkey] == "":
                    if subkey in item[key]:
                        del item[key][subkey]
                else:
                    item[key][subkey] = overritesettings[key][subkey]
        else:
            item[key] = overritesettings[key]