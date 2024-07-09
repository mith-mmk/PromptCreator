import json
import sys

import yaml


def yaml2json(yaml_file, json_file):
    with open(yaml_file, "r", encoding="utf-8") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


yaml_file = sys.argv[1]
json_file = sys.argv[2]
yaml2json(yaml_file, json_file)
