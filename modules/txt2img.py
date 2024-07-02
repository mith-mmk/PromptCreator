import json
import os

import modules.api as api
import modules.share as share
from modules.logger import getDefaultLogger
from modules.save import save_images

Logger = getDefaultLogger()

# Call txt2img API from webui


def txt2img(
    output_text,
    base_url="http://127.0.0.1:7860",
    output_dir="./outputs",
    opt={},
):
    base_url = api.normalize_base_url(base_url)
    url = base_url + "/sdapi/v1/txt2img"
    progress = base_url + "/sdapi/v1/progress?skip_current_image=true"
    Logger.info("Enter API mode, connect", url)
    dir = output_dir
    opt["dir"] = output_dir
    Logger.info("output dir", dir)
    Logger.debug("output text", output_text)
    os.makedirs(dir, exist_ok=True)
    #    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(output_text)
    Logger.info(f"API loop count is {count} times")
    Logger.info("")

    if opt.get("userpass"):
        userpass = opt.get("userpass")
    else:
        userpass = None

    for n, item in enumerate(output_text):
        Logger.info(f"API loop {n + 1} of {count}")
        share.set("line_count", 0)
        print(f"\033[KBatch {n + 1} of {count}")
        # Why is an error happening? json=payload or json=item
        # v1 mode
        if "variables" in item:
            opt["variables"] = item.pop("variables")
        # v2 mode
        if "verbose" in item:
            verbose = item.pop("verbose")
            opt["variables"] = verbose.get("variables")
            opt["values"] = verbose.get("values")
        part = item.get("filepart", "")
        if part:
            del item["filepart"]
        payload = json.dumps(item)
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
            Logger.info("Error!", response.status_code, response.text)
            continue

        r = response.json()
        opt["filepart"] = part
        prt_cnt = save_images(r, opt=opt)
        if share.get("line_count"):
            prt_cnt += share.get("line_count")
            share.set("line_count", 0)
    print("")
