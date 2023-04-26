#!/usr/bin/env python3
# !pip install pyyaml
# !pip install Pillow
# !pip install httpx

# version 0.8 (C) 2022-3 MITH@mmk  MIT License

import argparse
import copy
import itertools as it
import json
import os
import random
import re

import yaml
import modules.api as api
from modules.img2img import img2img
from modules.txt2img import txt2img


def get_appends(appends):
    appends_result = {}
    for n, items in enumerate(appends):
        if type(appends) is dict:
            key = items
            items = appends[items]
        else:
            key = str(n + 1)
        if type(items) is str:
            # filemode
            append = read_file(items)
        else:
            # inline mode
            append = []
            for item in items:
                append.append(item_split(item))
        appends_result[key] = append
    return appends_result


def yaml_parse(filename, mode='text', override=None, info=None):
    try:
        with open(filename, encoding='utf-8') as f:
            yml = yaml.safe_load(f)
    except FileNotFoundError:
        print(f'File {filename} is not found')
        exit(1)
    if 'command' not in yml:
        yml['command'] = {}
    if 'info' not in yml:
        yml['info'] = {}
    if 'options' in yml and 'json' in yml['options'] and yml['options']['json']:
        mode = 'json'

    command = yml['command']

    if override is not None:
        for key, item in override.items():
            command[key] = item

    information = yml['info']
    if info is not None:
        for key, item in info.items():
            information[key] = item

    if 'before_multiple' in yml:
        yml['before_multiple'] = get_appends(yml['before_multiple'])
    if 'appends' in yml:
        appends = get_appends(yml['appends'])
    if 'appends_multiple' in yml:
        yml['appends_multiple'] = get_appends(yml['appends_multiple'])

    prompts = ''

    if mode == 'text':
        for key, item in command.items():
            if type(item) is str:
                prompts = prompts + '--' + key + ' "' + item + '" '
            else:
                prompts = prompts + '--' + key + ' ' + str(item) + ' '
    elif mode == 'json':
        prompts = command
    return (prompts, appends, yml, mode)


def read_file(filename):
    strs = []
    filenames = filename.split()
    for filename in filenames:
        try:
            with open(filename, 'r', encoding='utf_8') as f:
                for i, item in enumerate(f.readlines()):
                    if re.match(r'^\s*#.*', item) or re.match(r'^\s*$', item):
                        continue
                    item = re.sub(r'\s*#.*$', '', item)
                    try:
                        strs.append(item_split(item))
                    except Exception:
                        print(f'Error happen line {filename} {i} {item}')
        except FileNotFoundError:
            print(f'{filename} is not found')
            exit(-1)
    return strs


def item_split(item):
    if type(item) is not str:
        return [str(item)]
    item = item.replace('\n', ' ').strip().replace(r'\;', r'${semicolon}')
    split = item.split(';')

    if type(split) is list:
        for i in range(0, len(split)):
            split[i] = split[i].replace(r'${semicolon}', ';')
    return split


def prompt_replace(string, replace_texts, var):
    if type(string) is string:
        print("Repacing String is type error ", type(string))
        exit(-1)

    if type(replace_texts) is not list:
        replace_texts = [replace_texts]

    rep = replace_texts[0]
    if type(string) is str:
        string = string.replace('${%s}' % (var), rep)
    elif type(string) is dict:
        for key in string:
            if type(string[key]) is str:
                string[key] = string[key].replace('${%s}' % (var), rep)

    for j in range(0, len(replace_texts)):
        rep = replace_texts[j]
        k = j + 1
        if type(string) is str:
            string = string.replace('${%s,%d}' % (var, k), rep)
        elif type(string) is dict:
            for key in string:
                if type(string[key]) is str:
                    string[key] = string[key].replace(
                        '${%s,%d}' % (var, k), rep)

    if type(string) is str:
        string = re.sub(r'\$\{%s,\d+\}' % (var), '', string)
        string = string.replace('${%s}' % (var), '')
    else:
        for key in string:
            if type(string[key]) is str:
                string[key] = re.sub(r'\$\{%s,\d+\}' % (var), '', string[key])
                string[key] = string[key].replace('${%s}' % (var), '')

    return string


def prompt_multiple(prompts, appends, console_mode, mode='text', variables_mode=False):
    if mode == 'text':
        output_text = ''
    elif mode == 'json':
        output_text = []

    array = list(appends.values())
    keys = list(appends.keys())
    x = list(range(0, len(array[0])))
    if len(array) >= 2:
        for i in range(1, len(array)):
            a = list(range(0, len(array[i])))
            x = list(it.product(x, a))

    for i in x:
        new_prompt = copy.deepcopy(prompts)
        if type(i) is int:
            j = [i]
        else:
            j = list(i)
        for _ in (range(2, len(array))):
            if len(j) == 2:
                a, b = j[0]
                if type(a) is int:
                    j = [a, b, j[1]]
                else:
                    j = [a[0], a[1], b, j[1]]
            elif type(j[0]) != int:
                a, b = j[0]
                j2 = j[1:]
                if type(a) is int:
                    j = [a, b]
                else:
                    j = [a[0], a[1], b]
                j.extend(j2)
        variables = {}
        for n, _ in enumerate(j):
            re_str = appends[keys[n]][j[n]]
            var = keys[n]
            if len(re_str) == 1:
                variables[var] = re_str[0]
            else:
                variables[var] = re_str[1]
            if len(re_str) == 1:
                new_prompt = prompt_replace(new_prompt, re_str, var)
            else:
                try:
                    float(re_str[0])
                    new_prompt = prompt_replace(new_prompt, re_str[1:], var)
                except ValueError:
                    new_prompt = prompt_replace(new_prompt, re_str, var)
        if console_mode:
            print(new_prompt)
        if mode == 'text':
            output_text = output_text + new_prompt + '\n'
        elif mode == 'json':
            if variables_mode:
                if 'variables' in new_prompt:
                    new_prompt['variables'].update(variables)
                else:
                    new_prompt['variables'] = variables
            output_text.append(new_prompt)
    return output_text


def weight_calc(append, num, default_weight=0.1, weight_mode=True):
    weight_append = []
    max_value = 0.0
    for i, item in enumerate(append):
        if len(item) == 1:
            weight = max_value + default_weight
            text = item[0]
        else:
            try:
                if weight_mode:
                    weight = max_value + float(item[0])
                else:
                    weight = max_value + default_weight
            except ValueError:
                print(f'float convert error append {num + 1} line {i} {item} use default')
                weight = max_value + default_weight
            finally:
                text = item[1:]

        weight_txt = {'weight': weight, 'text': text}

        max_value = weight_txt['weight']
        weight_append.append(weight_txt)
    return (weight_append, max_value)


def prompt_random(prompts, appends, console_mode, max_number, weight_mode=False, default_weight=0.1, mode='text', variables_mode=True):
    if mode == 'text':
        output_text = ''
    elif mode == 'json':
        output_text = []

    keys = list(appends.keys())
    appends = list(appends.values())
    weight_appends = []
    for num, append in enumerate(appends):
        weighted = weight_calc(
            append, num, default_weight, weight_mode=weight_mode)
#           print(weighted)
        weight_appends.append(weighted)
    for _ in range(0, max_number):
        new_prompt = copy.deepcopy(prompts)
        variables = {}
        for i, weighted in enumerate(weight_appends):
            append, max_weight = weighted
            n = max_weight
            while n >= max_weight:
                n = random.uniform(0.0, max_weight)
            pos = int(len(append) / 2)
            cnt = int((len(append) + 1) / 2)
            while True:
                w = append[pos]['weight']
#                   print (cnt,pos,n,w)
                if n < w:
                    if pos == 0:
                        break
                    if n >= append[pos - 1]['weight']:
                        #                           print ('break')
                        break
                    pos = pos - cnt
                    cnt = int((cnt + 1) / 2)
                    if pos < 0:
                        pos = 0
                    if cnt == 0:
                        break
                elif n == w:
                    break
                else:
                    if pos == len(append) - 1:
                        break
                    if n < w:
                        if n >= append[pos - 1]['weight']:
                            break
                    pos = pos + cnt
                    cnt = int((cnt + 1) / 2)
                    if pos >= len(append):
                        pos = len(append) - 1
                    if cnt == 0:
                        break
#               print (n,pos)
            var = keys[i]
            re_str = append[pos]['text']
#               print(var, re_str)
            new_prompt = prompt_replace(new_prompt, re_str, var)
            if type(re_str) is list:
                variables[var] = re_str[0]
            else:
                variables[var] = re_str
        if console_mode:
            print(new_prompt)
        if mode == 'text':
            output_text = output_text + new_prompt + '\n'
        elif mode == 'json':
            if variables_mode:
                if 'variables' in new_prompt:
                    new_prompt['variables'].update(variables)
                else:
                    new_prompt['variables'] = variables
            output_text.append(new_prompt)
    return output_text


def expand_arg(arg):
    array = None
    if arg is not None:
        array = {}
        for col in arg:
            items = col.split('=')
            key = items[0].strip()
            item = '='.join(items[1:]).strip()
            array[key] = item
    return array


def create_text(args):
    override = expand_arg(args.override)
    info = expand_arg(args.info)
    if args.json or args.api_mode:
        mode = 'json'
    else:
        mode = 'text'
    current = args.append_dir
    prompt_file = args.input
    output = args.output
    ext = os.path.splitext(prompt_file)[-1:][0]
    yml = None
    if ext == '.yaml' or ext == '.yml':
        # yaml mode
        prompts, appends, yml, mode = yaml_parse(prompt_file, mode=mode, override=override, info=info)
    else:
        # text mode
        appends = []
        prompts = ''
        try:
            dirs = os.listdir(current)
        except FileNotFoundError:
            print(f'Directory {current} is not found')
            exit(1)

        sorted(dirs)
        for filename in dirs:
            path = os.path.join(current, filename)
            if os.path.isfile(path):
                appends.append(read_file(path))
        try:
            with open(prompt_file, 'r', encoding='utf_8') as f:
                for line in f.readlines():
                    prompts = prompts + ' ' + line.replace('\n', '')
        except FileNotFoundError:
            print(f'{prompt_file} is not found')
            exit(1)

    if yml is not None and 'options' in yml and yml['options'] is not None:
        options = yml['options']
    else:
        options = {}

    console_mode = False
    if output is None and args.api_mode is False:
        if options.get('output'):
            output = options['output']
        else:
            console_mode = True

    if args.api_input_json is None and options.get('method') == 'random':
        max_number = 100
        default_weight = 0.1
        weight_mode = False
        if options is not None:
            if 'number' in options:
                max_number = options['number']

            if args.max_number != -1:
                max_number = args.max_number

            if 'weight' in options:
                weight_mode = options['weight']
            if 'default_weight' in options:
                default_weight = options['default_weight']

        if 'before_multiple' in yml:
            output_text = prompt_multiple(
                prompts, yml['before_multiple'], console_mode=False, mode=mode, variables_mode=args.api_filename_variable)
            if type(output_text) is list:
                multiple_text = []
                for prompts in output_text:
                    result = prompt_random(prompts, appends, console_mode, max_number, weight_mode=weight_mode,
                                           default_weight=default_weight, mode=mode, variables_mode=args.api_filename_variable)
                    for item in result:
                        multiple_text.append(item)
            else:
                multiple_text = ''
                for prompts in output_text.split('\n'):
                    multiple_text += prompt_random(prompts, appends, console_mode, max_number, weight_mode=weight_mode,
                                                   default_weight=default_weight, mode=mode, variables_mode=args.api_filename_variable)
            output_text = multiple_text
        else:
            if 'appends_multiple' in yml:
                output_text = prompt_random(prompts, appends, False, max_number, weight_mode=weight_mode,
                                            default_weight=default_weight, mode=mode, variables_mode=args.api_filename_variable)
            else:
                output_text = prompt_random(prompts, appends, console_mode, max_number, weight_mode=weight_mode,
                                            default_weight=default_weight, mode=mode, variables_mode=args.api_filename_variable)
        if 'appends_multiple' in yml:
            if type(output_text) is list:
                multiple_text = []
                for prompts in output_text:
                    result = prompt_multiple(
                        prompts, yml['appends_multiple'], console_mode, mode=mode, variables_mode=args.api_filename_variable)
                    for item in result:
                        multiple_text.append(item)
            else:
                multiple_text = ''
                for prompts in output_text.split('\n'):
                    multiple_text += prompt_multiple(
                        prompts, yml['appends_multiple'], console_mode, mode=mode, variables_mode=args.api_filename_variable)
            output_text = multiple_text
    else:
        output_text = prompt_multiple(
            prompts, appends, console_mode, mode=mode)

    if output is not None:
        with open(output, 'w', encoding='utf-8', newline='\n') as fw:
            if type(output_text) is str:
                fw.write(output_text)
            else:
                json.dump(output_text, fp=fw, indent=2)
    result = {
        'options': options,
        'yml': yml,
        'output_text': output_text
    }
    return result


def img2img_from_args(args):
    opt = {}
    opt['sd_model'] = args.api_set_sd_model
    opt['sd_vae'] = args.api_set_sd_vae
    items = ['denoising_strength', 'seed', 'subseed', 'subseed_strength', 'batch_size',
             'n_iter', 'steps', 'cfg_scale', 'width', 'height', 'prompt', 'negative_prompt',
             'sampler_index',
             'mask_blur', 'inpainting_fill', 'inpaint_full_res', 'inpaint_full_res_padding', 'inpainting_mask_invert']
    overrides_arg = expand_arg(args.override)
    overrides = {}
    if overrides_arg is not None:
        for item in items:
            if overrides_arg.get(item):
                overrides[item] = overrides_arg[item]
    print(overrides)
    if type(args.input) is str:
        filenames = [args.input]
    base_url = args.api_base
    output_dir = args.api_output_dir or './outputs'
    dicted_args = vars(args)
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

    if dicted_args.get('sd_model') is not None:
        api.set_sd_model(dicted_args.get('sd_model'), base_url=base_url, sd_vae=dicted_args.get('sd_vae'))

    opt = {}

    opt_keys = ['alt_image_dir', 'interrogate', 'filename_pattern', 'api_filename_variables', 'mask_dir',
                'userpass', 'num_once', 'num_length']
    for key in opt_keys:
        if dicted_args.get(key) is not None:
            opt[key] = dicted_args.get(key)

    try:
        img2img(input_files, base_url=base_url, overrides=overrides, output_dir=output_dir, opt=opt)
    except Exception as e:
        print(e)
        exit(-1)


def main(args):
    if args.api_mode and args.api_type == 'img2img':
        img2img_from_args(args)
        return

    if args.input is not None:
        result = create_text(args)
        options = result['options']
        output_text = result['output_text']
        yml = result['yml']
    elif args.api_input_json:
        options = {}
        yml = {}
        with open(args.api_input_json, 'r', encoding='utf-8') as f:
            output_text = json.loads(f.read())
    else:
        print('option error')
        exit(1)

    opt = {}

    if options.get('filename_pattern'):
        args.api_filename_pattern = args.api_filname_pattern or options['filename_pattern']
    if args.api_filename_pattern is not None:
        opt['filename_pattern'] = args.api_filename_pattern

    if args.num_length is not None:
        opt['num_length'] = args.num_length

    if args.api_userpass is not None:
        opt['userpass'] = args.api_userpass

    if args.num_once is not None:
        opt['num_once'] = args.num_once

    if 'command' in yml:
        opt['command'] = yml['command']

    if 'info' in yml:
        opt['info'] = yml['info']

    if args.api_mode:
        sd_model = args.api_set_sd_model or options.get('sd_model')
        sd_vae = args.api_set_sd_vae or options.get('sd_vae')
        opt['sd_model'] = sd_model
        opt['sd_vae'] = sd_vae
        opt['base_url'] = args.api_base
        if sd_model is not None:
            api.set_sd_model(base_url=args.api_base, sd_model=sd_model, sd_vae=sd_vae)
        api.init()
        txt2img(output_text, base_url=args.api_base,
                output_dir=args.api_output_dir, opt=opt)
        api.shutdown()


def run_from_args(command_args=None):
    parser = argparse.ArgumentParser(argument_default=None)
    parser.add_argument('input', type=str, nargs='?',
                        default=None,
                        help='input promptfile or image file for img2img')
    parser.add_argument('--append-dir', type=str,
                        default='./appends',
                        help='direcory of input append prompt files')
    parser.add_argument('--output', type=str,
                        default=None,
                        help='direcory of output file of prompt list file')

    parser.add_argument('--json', type=bool, nargs='?',
                        const=True, default=False,
                        help='output JSON')

    parser.add_argument('--api-mode', type=bool, nargs='?',
                        const=True, default=False,
                        help='output api force set --json')

    parser.add_argument('--api-base', type=str,
                        default='http://127.0.0.1:7860',
                        help='direct call api e.g http://127.0.0.1:7860')

    parser.add_argument('--api-userpass', type=str,
                        default=None,
                        help='API username:password')

    parser.add_argument('--api-output-dir', type=str,
                        default='outputs',
                        help='api output images directory')

    parser.add_argument('--api-input-json', type=str,
                        default=None,
                        help='api direct inputs from a json file')

    parser.add_argument('--api-filename-pattern', type=str,
                        default=None,
                        help='api outputs filename pattern default: [num]-[seed]')

    parser.add_argument('--max-number', type=int,
                        default=-1,
                        help='override option.number for yaml mode')

    parser.add_argument('--num-length', type=int,
                        default=None,
                        help='override seaquintial number length for filename : default 5')

    parser.add_argument('--api-filename-variable', type=bool, nargs='?',
                        const=True, default=False,
                        help='replace variables use filename')

    parser.add_argument('--num-once', type=bool, nargs='?',
                        const=True, default=False,
                        help='Search once file number')
    parser.add_argument('--api-set-sd-model', type=str,
                        default=None,
                        help='Change sd model "[Filename]" e.g. wd-v1-3 for "wd-v1-3.ckpt"')

    parser.add_argument('--api-set-sd-vae', type=str,
                        default='Automatic',
                        help='Change sd vae "[Filename]" e.g. "Anything-V3.0.vae.pt", None is not using VAE')

#    --command_override="width=768, height=1024,"....
    parser.add_argument('--override', type=str, nargs='*',
                        default=None,
                        help='command oveeride ex) "width=768, height=1024"')
    parser.add_argument('--info', type=str, nargs='*',
                        default=None,
                        help='add infomation')

# img2img

    parser.add_argument('--api-type', type=str,
                        default='txt2img',
                        help='call API type txt2img, img2img, default txt2img')

    parser.add_argument('--interrogate', type=str,
                        default=None,
                        help='If an image does not have prompt, it uses alternative interrogate API. model "clip" or "deepdanbooru"')

    parser.add_argument('--alt-image-dir', type=str,
                        default=None,
                        help='Alternative input image files diretory for img2img')

    parser.add_argument('--mask-dirs', type=str,
                        default=None,
                        help='Mask images directory for img2img')

    parser.add_argument('--mask_blur', type=int,
                        default=None,
                        help='Mask blur for img2img')

    args = parser.parse_args(command_args)
    if args.input is None and not (args.api_mode and args.api_input_json is not None):
        parser.print_help()
        print("need [input] or --api-mode --api_input_json [filename]")
        exit(1)
    main(args)


if __name__ == "__main__":
    run_from_args()
