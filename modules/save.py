
import asyncio
import io
import sys
import re
import os
import base64
import json
from hashlib import sha256
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, PngImagePlugin
import modules.api as api
from modules.parse import create_parameters

# The Image saver, but enough support aysnc


def save_images(r, opt={'dir': './outputs'}):
    return asyncio.run(save_img_wrapper(r, opt))


async def save_img_wrapper(r, opt):
    loop = api.share.get('loop')
    if loop is None:
        loop = asyncio.new_event_loop()
        api.share['loop'] = loop

    if loop:
        loop.run_in_executor(None, save_img(r, opt=opt))
        return len(r['images']) + 2
    else:
        save_img(r, opt=opt)
        return len(r['images']) + 2


def save_img(r, opt={'dir': './outputs'}):
    dir = opt['dir']
    if 'filename_pattern' in opt:
        nameseed = opt['filename_pattern']
    else:
        nameseed = '[num]-[seed]'

    need_names = re.findall(r'\[.+?\]', nameseed)
    need_names = [n[1:-1] for n in need_names]
    before_counter = re.sub(r'\[num\].*', '', nameseed)
    before_counter = re.sub(r'\[.*?\]', '', before_counter)
    count = len(before_counter)
    use_num = False
    for name in need_names:
        if name == 'num':
            use_num = True
            break

    for name in need_names:
        if name == 'num':
            break
        if name == 'shortdate':
            count += 6
        elif name == 'date':
            count += 10
        elif name == 'DATE':
            count += 8
        elif name == 'datetime':
            count += 14
        elif name == 'shortyear':
            count += 2
        elif name == 'year':
            count += 4
        elif name == 'month':
            count += 2
        elif name == 'day':
            count += 2
        elif name == 'time':
            count += 6
        elif name == 'hour':
            count += 2
        elif name == 'min':
            count += 2
        elif name == 'sec':
            count += 2
        elif use_num:
            print(f'[{name}] is setting before [num]', file=sys.stderr)
            raise ValueError

    num_length = 5
    if 'num_length' in opt:
        num = opt['num_length']
    if 'startnum' in opt:
        num = opt['startnum']
    else:
        num = -1
        files = os.listdir(dir)
        num_start = 0 + count
        num_end = num_length + count

        for file in files:
            if os.path.isfile(os.path.join(dir, file)):
                name = file[num_start:num_end]
                try:
                    num = max(num, int(name))
                except ValueError:
                    pass
        num += 1

    if type(r['info']) is str:
        info = json.loads(r['info'])
    else:
        info = r['info']

    count = len(r['images'])
    print(f'\033[Kreturn {count} images')

    filename_pattern = {}

    for key, value in info.items():
        filename_pattern[key] = value
    if 'variables' in opt:
        var = re.compile(r'\$\{(.+?)\}')
        for key, value in opt['variables'].items():
            value = str(value)
            match = var.search(value)
            while match is not None:
                for new_key in match.groups():
                    if new_key in opt['variables']:
                        value = value.replace('${%s}' % (new_key), opt['variables'][new_key])
                    else:
                        value = value.replace('${%s}' % (new_key), '')
                    match = var.search(value)
            filename_pattern['var:' + key] = value

    if 'info' in opt:
        for key, value in opt['info'].items():
            if type(key) == str:
                filename_pattern['info:' + key] = value

    if 'command' in opt:
        for key, value in opt['command'].items():
            if type(key) == str:
                filename_pattern['command:' + key] = value

    for n, i in enumerate(r['images']):
        try:
            meta = info['infotexts'][n]
#               image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[1])))
            image = Image.open(io.BytesIO(base64.b64decode(i)))
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text('parameters', meta)
            parameters = create_parameters(info['infotexts'][n])
            filename = nameseed + '.png'

            for seeds in need_names:
                replacer = ''
                if seeds == 'num':
                    replacer = str(num).zfill(5)
                elif seeds == 'seed' and 'all_seeds' in filename_pattern:
                    replacer = filename_pattern['all_seeds'][n]
                elif seeds == 'subseed' and 'all_subseeds' in filename_pattern:
                    replacer = filename_pattern['all_subseeds'][n]
                elif seeds == 'styles' and seeds in filename_pattern:
                    replacer = filename_pattern[seeds].join(' ')
                elif seeds == 'DATE' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][:8]     # OLD Date
                elif seeds == 'date':
                    date = datetime.now()
                    replacer = date.strftime('%Y-%m-%d')                 # Web UI Date
                elif seeds == 'datetime' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp']
                elif re.match(r'datetime<.+?><.+?>', seeds):
                    try:
                        match = re.search(r'datetime<(.+)><(.+)>', seeds)
                        date = datetime.now(tz=ZoneInfo(key=match.group(2)))
                        replacer = date.strftime(match.group(1))
                    except ValueError:
                        replacer = '[' + seeds + ']'
                elif re.match(r'datetime<.+>', seeds):
                    try:
                        date = datetime.now()
                        match = re.search(r'datetime<(.+)>', seeds)
                        replacer = date.strftime(match.group(1))
                    except ValueError:
                        replacer = '[' + seeds + ']'
                        replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\s]', '_', str(replacer))[:127]
                elif seeds == 'shortdate' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][2:8]
                elif seeds == 'year' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][:4]
                elif seeds == 'shortyear' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][2:4]
                elif seeds == 'month' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][4:6]
                elif seeds == 'day' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][6:8]
                elif seeds == 'time' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][8:]
                elif seeds == 'hour' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][8:10]
                elif seeds == 'min' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][10:12]
                elif seeds == 'sec' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][12:14]
                elif seeds == 'model_name':
                    base_url = opt['base_url']
                    model = api.get_sd_model(base_url, parameters['model_hash'])
                    replacer = model['model_name'] if model is not None else ''
                elif seeds == 'prompt':
                    replacer = parameters['prompt']
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\s]', '_', str(replacer))[:127]
                elif seeds == 'prompt_spaces':
                    replacer = parameters['prompt']
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\s]+', ' ', str(replacer))[:127]
                elif seeds == 'prompt_words':
                    replacer = parameters['prompt']
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+', ' ', str(replacer))[:127]
                elif seeds == 'prompt_hash':
                    replacer = sha256(parameters['prompt'].encode('utf-8')).hexdigest()[:8]
                elif seeds == 'prompt_no_styles':
                    replacer = filename_pattern['prompt']
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+', '_', str(replacer))[:127]
                elif seeds in parameters:
                    replacer = parameters[seeds]
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+', '_', str(replacer))[:127]
                elif seeds in filename_pattern and type(filename_pattern[seeds]) is list:
                    replacer = filename_pattern[seeds][n]
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+', '_', str(replacer))[:127]
                elif seeds in filename_pattern:
                    replacer = filename_pattern[seeds]
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\s]', '_', str(replacer))[:127]
                else:
                    replacer = '[' + seeds + ']'
                    replacer = re.sub(r'[\<\>\:\"\/\\\\|?\*\n\s]', '_', str(replacer))[:127]
                filename = filename.replace('[' + seeds + ']', str(replacer))

#            seed = filename_pattern['all_seeds'] [n]
#            filename = str(num).zfill(5) +'-' +  str(seed) + '.png'
            filename = re.sub(r'\[.+?\:.+?\]', '', filename)
            print('\033[Ksave... ', filename)
            filename = os.path.join(dir, filename)
            dirname = os.path.dirname(filename)
            if dirname != dir:
                os.makedirs(dirname, exist_ok=True)
            num += 1
            if 'num_once' in opt:
                opt['startnum'] = num
            image.save(filename, pnginfo=pnginfo)
        except KeyboardInterrupt:
            print('\033[KProcess stopped Ctrl+C break', file=sys.stderr)
            raise KeyboardInterrupt
        except BaseException as e:
            print('\033[Ksave error', e, filename, file=sys.stderr)
            raise e
#    opt['startnum'] = num
    return len(r['images']) + 2
