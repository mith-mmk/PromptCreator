import json
import sys

from modules.parse import create_img2params

args = sys.argv
filename = sys.argv[1]
params = create_img2params(filename)


print(json.dumps(params, indent=2, ensure_ascii=False))
