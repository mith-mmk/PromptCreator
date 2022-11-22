# img2img api test inpritation,function specifications are change after commit
from create_prompts import img2img, set_sd_model
import os

import argparse

parser = argparse.ArgumentParser()

parser.add_argument('--output', type=str,
                    default=None,
                    help='direcory of output file of prompt list file')
parser.add_argument('--api-base', type=str,
                    default='http://127.0.0.1:7860',
                    help='api base url')
parser.add_argument('--seed', type=int,
                    default=None,
                    help='override seed')

parser.add_argument('--steps', type=int,
                    default=None,
                    help='override steps')
parser.add_argument('--cfg_scale', type=int,
                    default=None,
                    help='override cfg_scale')

parser.add_argument('--width', type=int,
                    default=None,
                    help='override width')
parser.add_argument('--height', type=int,
                    default=None,
                    help='override height')

parser.add_argument('--n_iter', type=int,
                    default=None,
                    help='override n_iter')
parser.add_argument('--batch_size', type=int,
                    default=None,
                    help='override batch_size')
parser.add_argument('--denoising_strength', type=float,
                    default=None,
                    help='override denoising_strength')

parser.add_argument('--interrogate', type=str,
                    default=None,
                    help='If an image does not have prompt, it uses alternative interrogate API. model "clip" or "deepdanbooru"')

parser.add_argument('--sd-model', type=str,
                    default=None,
                    help='Initalize change sd model')


parser.add_argument('--alt-image-dir', type=str,
                    default=None,
                    help='Alternative input image files diretory')

parser.add_argument('input', type=str,nargs='+',
                    help='input files or dirs')


parser.parse_args()
args = parser.parse_args()

if type(args.input) is str:
    filenames = [args.input]
else:
    filenames = args.input
base_url = args.api_base
output_dir = args.output or './outputs'

items = ['denoising_strength','seed','subseed','subseed_strength','batch_size',
    'n_iter', 'steps', 'cfg_scale','width','height','prompt','negative_prompt',
    'sampler_index']

overrides = {}

dicted_args = vars(args)
for item in items:
    if dicted_args.get(item):
        overrides[item] = dicted_args[item]


input_files = []
for filename in filenames:
    if os.path.isdir(filename):
        path = filename
        files = os.listdir(path)
        for file in files:
            file = os.path.join(path, file)
            if os.path.isfile(file):
                input_files.append(file)
    elif os.path.isfile(filename):
        input_files.append(filename)
if len(input_files) == 0:
    print('no exit files')
    exit(1)

if dicted_args.get('sd_model') is not None: set_sd_model(dicted_args.get('sd_model'), base_url= base_url)

opt = {}
if dicted_args.get('alt_image_dir') is not None:
    opt['alt_image_dir'] = dicted_args.get('alt_image_dir')

if dicted_args.get('interrogate') is not None:
    opt['interrogate'] = dicted_args.get('interrogate')

try:
    result = img2img(input_files,base_url=base_url,overrides=overrides,output_dir=output_dir,opt = opt)
except:
    exit(-1)

# - multiple images impl
# - overrides maker from yaml
# - image mask impl