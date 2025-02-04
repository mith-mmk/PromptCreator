# Use ControlNet Extention
import asyncio
import base64
import os

import httpx

from modules.logger import getDefaultLogger

Logger = getDefaultLogger()

cn = None


def parse(base_url, controlnet, opt):
    global cn
    if cn is None:
        cn = ControlNet(base_url)
    return cn.parse(controlnet, opt)


class ControlNet:
    def __init__(self, hostname) -> None:
        self.client = httpx.AsyncClient()
        self.hostname = hostname
        self.models = None

    async def getModels(self):
        import re

        re_match = re.compile(r"^(.+?)\s*\[(.+)\]$")
        response = await self.client.get(f"{self.hostname}/controlnet/model_list")
        if response.status_code != 200:
            return None
        json_data = response.json()
        for modelname in json_data.get("model_list", []):
            match = re_match.match(modelname)
            if match:
                try:
                    model, hash = match.groups()
                except Exception as e:
                    print(e)
                    continue
                if self.models is None:
                    self.models = {}
                model = model.strip().lower()
                self.models[model] = {"modelname": modelname, "hash": hash}
        return self.models

    def searchModel(self, modelname):
        if modelname == "None":
            return "None"
        if self.models is None:
            self.models = asyncio.run(self.getModels())
        if modelname in self.models:
            return modelname
        basename = os.path.basename(modelname)
        model_base = ".".join(basename.split(".")[:-1])
        model_base = model_base.lower()
        if self.models is not None:
            if model_base in self.models:
                return self.models[model_base].get("modelname")
        return None

    def parse(self, controlnet, opt):
        try:
            Logger.verbose("Extend Script ControlNet")
            args = controlnet.get("args")
            for arg in args:
                if not arg.get("enabled"):
                    Logger.verbose("ControlNet arg is disabled, Skip prompt")
                    continue
                image = arg.get("image")
                if image:
                    dir = opt.get("cn_images_dir", "./inputs")
                    image = os.path.join(dir, image)
                    if not os.path.exists(image):
                        Logger.error(f"Image file not found: {image}")
                        continue
                    with open(image, "rb") as f:
                        encoded = base64.b64encode(f.read()).decode("utf-8")
                        missing_padding = len(encoded) % 4
                        if missing_padding:
                            encoded += "=" * (4 - missing_padding)
                        arg["image"] = f"data:image/png;base64,{encoded}"
                Logger.info("ControlNet image loaded:")
                model = arg.get("model")
                if model:
                    model = self.searchModel(model)
                    if model is None:
                        Logger.warning(
                            f'ControlNet model not found: {model}, use  "None"'
                        )
                        arg["model"] = "None"
                    else:
                        arg["model"] = model
                else:
                    Logger.error("ControlNet model not found")
                    continue
                Logger.info("ControlNet model:", model)

        except Exception as e:
            Logger.error("ControlNet error, Skip prompt:", e)
            return None
        return controlnet
