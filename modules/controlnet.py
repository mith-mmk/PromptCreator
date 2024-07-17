# Use ControlNet Extention
import os

import httpx


class ControlNet:
    def __init__(self, hostname) -> None:
        self.client = httpx.Client()
        self.hostname = hostname
        self.models = None

    def getModels(self):
        import re

        re_match = re.compile(r"^(.+?)\s*\[(.+)\]$")
        response = self.client.get(f"{self.hostname}/controlnet/model_list")
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
        if self.models is None:
            self.models = self.getModels()
        if modelname in self.models:
            return modelname
        basename = os.path.basename(modelname)
        model_base = ".".join(basename.split(".")[:-1])
        model_base = model_base.lower()
        if self.models is not None:
            if model_base in self.models:
                return self.models[model_base].get("modelname")
        return None
