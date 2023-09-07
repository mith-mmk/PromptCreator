import sys
import os
import json
from modules.parse import create_img2json

model_json = "./outputs/hash.json"
models = json.load(open(model_json, "r"))


arg = sys.argv[1]
ext = os.path.splitext(arg)[1]
if ext != ".png":
    print("Error: File extension must be .png")
    exit(1)

params = create_img2json(arg)
print(params)
model_hash = params["override_settings"]["sd_model_checkpoint"]
print(models[model_hash], model_hash)
