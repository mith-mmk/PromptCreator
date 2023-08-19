import yaml
import copy
import random
import re
import itertools as it
import json
import os
import platform

# randam prompt creator


def set_reserved(keys):
    # 10 integer numbers
    keys['$RANDOM'] = []
    for _ in range(0, 10):
        keys['$RANDOM'].append(str(random.randint(0, 2**31 - 1)))
    keys['$SYSTEM'] = ['1.0;' + platform.system()]
    keys['$ARCHITECTURE'] = ['1.0;' + platform.architecture()[0]]
    keys['$VERSION'] = ['1.0;' + platform.version()]
    keys['$MACHINE'] = ['1.0;' + platform.machine()]
    keys['$PROCESSOR'] = ['1.0;' + platform.processor()]
    keys['$PYTHON_VERSION'] = ['1.0;' + platform.python_version()]
    keys['$HOSTNAME'] = ['1.0;' + platform.node()]

    return keys


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
        raise FileNotFoundError
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
            raise FileNotFoundError
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


def expand_arg(args):
    array = None
    if args is not None:
        array = {}
        for arg in args:
            for col in arg.split(','):
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
            raise FileNotFoundError

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
            raise FileNotFoundError
    appends = set_reserved(appends)

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