# img2img api test inpritation,function specifications are change after commit
from create_prompts import img2img
import sys

filename = sys.argv[1]
if len(sys.argv) >= 3:
    base_url = sys.argv[2]
else:
    base_url ='http://127.0.0.1:7860'
overrides = [{'denoising_strength' : 0.75, 'seed': -1}]
result = img2img([filename],base_url=base_url,overrides=overrides,output_dir='./outputs')
# - multiple images impl
# - overrides maker from yaml
# - image mask impl