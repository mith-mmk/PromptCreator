# img2img api test inpritation,function specifications are change after commit
from create_prompts import img2img
import os

import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--output', type=str,
                    default=None,
                    help='direcory of output file of prompt list file')
parser.add_argument('--api-base', type=str,
                    default='http://127.0.0.1:7860',
                    help='api base url')
parser.add_argument('input', nargs='+',
                    help='input files or dirs')
parser.parse_args()
args = parser.parse_args()

if type(args.input) is str:
    filenames = [args.input]
else:
    filenames = args.input
base_url = args.api_base
output_dir = args.output or './outputs'

overrides = [{'denoising_strength' : 0.75, 'seed': -1}]

input_files = []
for filename in filenames:
    if os.path.isdir(filename):
        path = filename
        files = os.listdir(path)
        for file in files:
            file = os.path.join(path, file)
            if os.path.isfile(file):
                input_files.append(file)
    else:
        input_files.append(filename)


result = img2img(input_files,base_url=base_url,overrides=overrides,output_dir=output_dir)
# - multiple images impl
# - overrides maker from yaml
# - image mask impl