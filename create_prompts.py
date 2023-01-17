#!/bin/python3
#!pip install pyyaml
#!pip install Pillow
#!pip install httpx

# version 0.6 (C) 2022 MITH@mmk  MIT License 

import argparse
import asyncio
import base64
import copy
import io
import itertools as it
import json
import os
import random
import re
import sys
import time

import httpx
import yaml
from PIL import Image, PngImagePlugin

share = {
    'timeout': 5,
    'max_timeout': 1000
}


def init():
    loop = asyncio.new_event_loop()
    share['loop'] = loop

def shutdown():
    pass

async def async_post(url,data,userpass = None):
    headers = {
        'Content-Type': 'application/json',
    }
    if userpass:
        headers['Authorization'] = 'Basic ' + base64.b64encode(userpass.encode())

    async with httpx.AsyncClient() as client:
        try:
            return await client.post(url,data=data,headers=headers,timeout=(share.get('timeout'),share.get('max_timeout')))
        except httpx.ReadTimeout:
            print('Read timeout',file=sys.stderr)
            return None
        except httpx.TimeoutException:
            print('Connect Timeout',file=sys.stderr)
            return None
        except BaseException as error:
            print('Exception: ',error,file=sys.stderr)
            return None

async def progress_writer(url,data,progress_url,userpass=None):
    headers = {
        'Content-Type': 'application/json',
    }
    if userpass:
        headers['Authorization'] = 'Basic ' + base64.b64encode(userpass.encode())
    result = None
    async with httpx.AsyncClient() as client:
        async def write_progress(result,start_time):
            right = result['progress'] * 100
            state = result['state']
            step = state['sampling_step']
            steps = state['sampling_steps']
            job = state['job']
            elapsed_time = time.time() - start_time
            sharp = '#' * int(right / 2) 
            space = ' ' * (50 - len(sharp))
            if right >= 0.0:
                string = '\033[KCreate Image [{}{}] {:.1f}%  {} step ({:d}/{:d}) {:.2f} sec'.format(
                    sharp,space,right,job,step,steps,elapsed_time
                )
            else:
                right = - right
                sharp = '#' * int(right / 2) 
                space = ' ' * (50 - len(sharp))
                string = '\033[KWeb UI interrupts using resource [{}{}] {:.1f}%  {} step ({:d}/{:d}) {:.2f} sec'.format(
                    sharp,space,right,job,step,steps,elapsed_time
                )

            print(string,end='\r')
            return elapsed_time

        async def progress_get(progress_url,userpass=None):
            headers = {}
            if userpass:
                headers['Authorization'] = 'Basic ' + base64.b64encode(userpass.encode())
            async with httpx.AsyncClient() as client:
                retry = 0
                start_time = time.time()
                response = await client.get(progress_url,headers = headers)
                result = response.json()
                right = 1.0

                elapsed_time =await write_progress(result,start_time)
                await asyncio.sleep(0.5) # initializing wait
                while right != 0.0 and elapsed_time <= share.get('max_timeout'):
                    await asyncio.sleep(0.2)
                    try: 
                        response = await client.get(progress_url)
                        retry = 0
                        result = response.json()
                        right = result['progress']
                        elapsed_time = await write_progress(result,start_time)
                    except:
                        retry += 1
                        if retry >= 10:
                            print('Progress is unknown',file=sys.stderr)
                            return

        tasks = [
            client.post(url,data=data,headers=headers,timeout=(share.get('timeout'),share.get('max_timeout'))),
            progress_get(progress_url,userpass)
        ]
        result = await asyncio.gather(*tasks, return_exceptions=False)
    return result[0]

# force interrupt process
def progress_interrupt(url,userpass):
    try:
        headers = {}
        if userpass: 
            headers = {'Authorization': 'Basic ' + base64.b64encode(userpass.encode())}
        return httpx.post(url,headers=headers)
    except httpx.ReadTimeout:
        print('Read timeout',file=sys.stderr)
        return None
    except httpx.TimeoutException:
        print('Connect Timeout',file=sys.stderr)
        return None
    except BaseException as error:
        print(str(error),file=sys.stderr)
        return None

def request_post_wrapper(url,data,progress_url=None,base_url=None,userpass=None):
    try:
        if progress_url is not None:
            result = asyncio.run(progress_writer(url,data,progress_url,userpass))
        else:
            result = asyncio.run(async_post(url,data,userpass))
    except KeyboardInterrupt:
        if base_url:
            progress_interrupt(base_url + '/sdapi/v1/interrupt')
        print('enter Ctrl-c, Process stopping',file=sys.stderr)
        exit(2)
    except httpx.ConnectError:
        print('All connection attempts failed,Is the server down?',file=sys.stderr)
        exit(2)
    except httpx.ConnectTimeout:
        print('Connection Time out,Is the server down or server address mistake?',file=sys.stderr)
        exit(2)
    return result

def normalize_base_url(base_url):
    if base_url[-1] == '/':
        base_url = base_url[:-1]
    return base_url

def create_parameters(parameters_text):
    para = parameters_text.split('\n')
    if len(para) == 1:
        para.append('')
    parameters = {}
    parameters['prompt'] = para[0]
    neg = 'Negative prompt: '
    if para[1][:len(neg)] == neg:
        parameters['negative_prompt'] = para[1].replace(neg,'')
        options = para[2].split(',')
    else:
        options = para[1].split(',')

    for option in options:
        keyvalue = option.split(': ')
        if len(keyvalue) == 2:
            key = keyvalue[0].strip().replace(' ','_').lower()
            if key == 'size':
                wh = keyvalue[1].split('x')
                parameters['width'] = wh[0]
                parameters['height'] = wh[1]
            elif key == 'seed_resize_from':
                wh = keyvalue[1].split('x')
                parameters['seed_resize_from_w'] = wh[0]
                parameters['seed_resize_from_h'] = wh[1]
            elif key == 'sampler':
                parameters['sampler_index'] = keyvalue[1]
            elif key == 'batch_pos':
                pass
            elif key == 'clip_skip':
                parameters['CLIP_stop_at_last_layers'] = keyvalue[1]
            else:
                parameters[key] = keyvalue[1]
        else:
            print('unknow', option)
    return parameters

def set_sd_model(sd_model, base_url='http://127.0.0.1:7860'):
    print('Try change sd model to %s' % (sd_model))
    headers = {
        'Content-Type': 'application/json',
    }
    base_url = normalize_base_url(base_url)
    model_url = (base_url + '/sdapi/v1/sd-models')

    url = (base_url + '/sdapi/v1/options')
    try:
        res = httpx.get(model_url,headers=headers,timeout=(share.get('timeout')))
        load_model = None
        for model in res.json():
            if model['model_name'] == sd_model or model['hash'] == sd_model or model['title'] == sd_model:
                load_model = model['title']
                break
        if load_model is None:
            print('%s model is not found' % (sd_model))
            exit()
        sd_model = load_model   
        print("%s model loading..." % (sd_model))
        payload = {"sd_model_checkpoint": sd_model}
        data = json.dumps(payload)
        res = httpx.post(url,data=data,headers=headers,timeout=(share.get('timeout'),share.get('max_timeout')))
        # Version Return null only
        if res.status_code == 200:
            print('change success sd_model')
        else:
            print('change failed')

    except:
        print('Change SD Model Error')
        exit()

def create_img2json(imagefile,alt_image_dir = None,mask_image_dir = None):
    schema = [
        'enable_hr',
        'denoising_strength',
        'firstphase_width', # obusolete
        'firstphase_height', # obusolete
        'prompt',
        'styles',
        'seed',
        'subseed',
        'subseed_strength',
        'seed_resize_from_h',
        'seed_resize_from_w',
        'batch_size',
        'n_iter',
        'steps',
        'cfg_scale',
        'width',
        'height',
        'restore_faces',
        'tiling',
        'negative_prompt',
        'eta',
        's_churn',
        's_tmax',
        's_tmin',
        's_noise',
        'sampler',
        # img2img inpainting onky
        'mask_blur',
        'inpainting_fill',
        'inpaint_full_res',
        'inpaint_full_res_padding',
        'inpainting_mask_invert'
    ]

    image = Image.open(imagefile)
    image.load()
    if 'parameters' in image.info and image.info['parameters'] is not None:
        parameter_text = image.info['parameters']
        parameters = create_parameters(parameter_text)
    else:
        parameters = {'width': image.width,'height': image.height}

    # workaround for hires.fix spec change 
    parameters['width'] = image.width
    parameters['height'] = image.height

    load_image = imagefile
    if alt_image_dir is not None:
        basename = os.path.basename(imagefile)
        alt_imagefile = os.path.join(alt_image_dir, basename)
        if os.path.isfile(alt_imagefile):
            print ('\033[Kbase image use alternative %s' % (alt_imagefile))
            if 'line_count' in share: share['line_count'] += 1
            load_image = alt_imagefile
    with open(load_image,'rb') as f:
        init_image = base64.b64encode(f.read()).decode("ascii")
    json_raw = {}
    json_raw['init_images'] = ['data:image/png;base64,' + init_image]

    if mask_image_dir is not None:
        basename = os.path.basename(imagefile)
        mask_imagefile = os.path.join(mask_image_dir, basename)
        if os.path.isfile(mask_imagefile):
            with open(mask_imagefile,'rb') as f:
                print ('\033[KUse image mask %s' % (mask_imagefile))
                if 'line_count' in share: share['line_count'] += 1
                mask_image = base64.b64encode(f.read()).decode("ascii")
                json_raw['mask'] = 'data:image/png;base64,' + mask_image
                json_raw['mask_blur'] = 4
                json_raw['inpainting_fill'] = 0
                json_raw['inpaint_full_res'] = True
                json_raw['inpaint_full_res_padding'] = 0
                json_raw['inpainting_mask_invert'] = 0

    override_setting = {}
    sampler_index = None
    for key,value in parameters.items():
        if key in schema:
            json_raw[key] = value
        elif key == 'sampler_index':
            sampler_index = value
            pass
        else:
            override_setting[key] = value

    if ( 'sampler' not in json_raw) and sampler_index is not None:
        json_raw['sampler_index'] = sampler_index

    json_raw['override_setting'] = override_setting
    return json_raw

def save_images(r,opt={'dir': './outputs'}):
    return asyncio.run(save_img_wrapper(r,opt))

async def save_img_wrapper(r,opt):
    loop = share.get('loop')
    if loop == None:
        loop = asyncio.new_event_loop()
        share['loop'] = loop

    if loop:
        loop.run_in_executor(None,save_img(r,opt=opt))
        return len(r['images']) + 2
    else:
        save_img(r,opt=opt)
        return len(r['images']) + 2

def save_img(r,opt={'dir': './outputs'}):
    dir = opt['dir']
    if 'filename_pattern' in opt:
        nameseed = opt['filename_pattern']
    else:
        nameseed = '[num]-[seed]'

    need_names = re.findall('\[.+?\]',nameseed)
    need_names = [n[1:-1] for n in need_names]
    before_counter = re.sub('\[num\].*','',nameseed)
    before_counter = re.sub('\[.*?\]','',before_counter)
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
            count += 8
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
            print('[%s] is setting before [num]' % (name),file=sys.stderr)
            exit(-1)

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
            if os.path.isfile(os.path.join(dir,file)):
                name = file[num_start:num_end]
                try:
                    num = max(num,int(name))
                except:
                    pass
        num += 1
        # opt['startnum'] = num

    if type(r['info']) is str:
        info = json.loads(r['info'])
    else:
        info = r['info']


    print('\033[Kreturn %d images' % (len(r['images'])))

    filename_pattern = {}

    for key,value in info.items():
        filename_pattern[key] = value

    if 'variables' in opt:
        for key,value in opt['variables'].items():
            filename_pattern['var:' + key] = value

    for n, i in enumerate(r['images']):
        try:
            meta = info['infotexts'][n]
#               image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[1])))
            image = Image.open(io.BytesIO(base64.b64decode(i)))
            pnginfo = PngImagePlugin.PngInfo()
            pnginfo.add_text('parameters', meta)

            filename = nameseed + '.png'

            for seeds in need_names:
                replacer = ''
                if seeds == 'num':
                    replacer = str(num).zfill(5)
                elif seeds == 'seed' and 'all_seeds' in filename_pattern:                  
                    replacer = filename_pattern['all_seeds'][n]
                elif seeds == 'subseed' and 'all_subseeds' in filename_pattern:
                    replacer = filename_pattern['all_subseeds'] [n]
                elif seeds == 'styles' and seeds in filename_pattern:
                    replacer = filename_pattern[seeds].join(' ')
                elif seeds == 'date' and 'job_timestamp' in filename_pattern:
                    replacer = filename_pattern['job_timestamp'][:8]
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
                elif type(filename_pattern[seeds]) is list and seeds in filename_pattern:
                    replacer = filename_pattern[seeds][n]
                else:
                    replacer = filename_pattern[seeds]
                replacer = re.sub('[\<\>\:\"\/\\\\|?\*\n\s]+','_',str(replacer))[:127]
                filename = filename.replace('[' + seeds + ']',replacer)
            
#            seed = filename_pattern['all_seeds'] [n]
#            filename = str(num).zfill(5) +'-' +  str(seed) + '.png'
            filename = re.sub('\[.+?\:.+?\]','', filename)
            print('\033[Ksave... ',filename)
            filename = os.path.join(dir,filename)
            dirname = os.path.dirname(filename)
            if dirname != dir: os.makedirs(dirname,exist_ok=True)
            num += 1
            image.save(filename , pnginfo=pnginfo)
        except KeyboardInterrupt:
            print ('\033[KProcess stopped Ctrl+C break',file=sys.stderr)
            exit(2)
        except BaseException as e:
            print ('\033[Ksave error',e,filename,file=sys.stderr)
            exit(2)
#    opt['startnum'] = num
    return len(r['images']) + 2


def img2img(imagefiles,overrides=None,base_url='http://127.0.0.1:8760',output_dir='./outputs',opt = {}):
    base_url = normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/img2img')
    progress = base_url + '/sdapi/v1/progress?skip_current_image=true'
    print ('Enter API, connect', url)
    dir = output_dir
    opt['dir'] = output_dir
    print('output dir',dir)
    os.makedirs(dir,exist_ok=True)
#    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(imagefiles)

    print('API loop count is %d times' % (count))
    print('')
    flash = ''
    alt_image_dir = opt.get('alt_image_dir')
    mask_image_dir = opt.get('mask_dir')

    if opt.get('userpass'): userpass = opt.get('userpass')
    else: userpass = None


    for (n,imagefile) in enumerate(imagefiles):
        share['line_count'] = 0
        print(flash,end = '')
        print('\033[KBatch %d of %d' % (n+1,count))
        item = create_img2json(imagefile,alt_image_dir,mask_image_dir)
        if opt.get('interrogate') is not None and (item.get('prompt') is None or opt.get('force_interrogate')):
            print('\033[KInterrogate from an image....')
            share['line_count'] += 1
            try:
                result = interrogate(imagefile, base_url, model = opt.get('interrogate'))
                if result.status_code == 200:
                    item['prompt'] = result.json()['caption']
            except BaseException as e:
                print ('itterogate failed',e)
        if overrides is not None:
            if type(overrides) is list:
                override = overrides[n]
            else:
                override = overrides
            for key,value in override.items():
                item[key] = value


        # Why is an error happening? json=payload or json=item
        payload = json.dumps(item)
        response = request_post_wrapper(url, data=payload, progress_url=progress,base_url=base_url,userpass=userpass)

        if response is None:
            print('http connection - happening error')
            exit(-1)
        if response.status_code != 200:
            print ('\033[KError!',response.status_code, response.text)
            print('\033[%dA' % (2),end='')
            continue

        r = response.json()
        prt_cnt = save_img(r,opt = opt)
        if 'line_count' in share:
            prt_cnt += share['line_count']
            share['line_count'] = 0
        flash = '\033[%dA' % (prt_cnt)
    print('')

# 2022-11-07 cannot run yet 2022-11-12 running?
def interrogate(imagefile,base_url,model = 'clip',userpass=None):
    base_url = normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/interrogate')
    with open(imagefile,'rb') as f:
        image = base64.b64encode(f.read()).decode("ascii")
    payload = json.dumps({'image': 'data:image/png;base64,' + image,'model': model})
    response = request_post_wrapper(url, data=payload, progress_url=None,base_url=base_url,userpass=userpass)
    return response


def txt2img(output_text,base_url='http://127.0.0.1:8760',output_dir='./outputs',opt = {}):
    base_url = normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/txt2img')
    progress = base_url + '/sdapi/v1/progress?skip_current_image=true'
    print ('Enter API mode, connect', url)
    dir = output_dir
    opt['dir'] = output_dir
    print('output dir',dir)
    os.makedirs(dir,exist_ok=True)
#    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(output_text)
    print('API loop count is %d times' % (count))
    print('')
    flash = ''

    if opt.get('userpass'): userpass = opt.get('userpass')
    else: userpass = None

    for (n,item) in enumerate(output_text):
        share['line_count'] = 0
        print(flash,end = '')
        print('\033[KBatch %d of %d' % (n+1,count))
        # Why is an error happening? json=payload or json=item
        if 'variables' in item:
            opt['variables'] = item.pop('variables')
        payload = json.dumps(item)
        response = request_post_wrapper(url, data=payload, progress_url=progress,base_url=base_url,userpass=userpass)

        if response is None:
            print('http connection - happening error')
            exit(-1)
        if response.status_code != 200:
            print ('\033[KError!',response.status_code, response.text)
            print('\033[%dA' % (2),end='')
            continue

        r = response.json()
        prt_cnt = save_images(r,opt = opt)
        if 'line_count' in share:
            prt_cnt += share['line_count']
            share['line_count'] = 0
        flash = '\033[%dA' % (prt_cnt)
    print('')

def get_appends(appends):
    appends_result = {}
    for n,items in enumerate(appends):
        if type(appends) is dict:
            key = items
            items = appends[items]
        else:
            key = str(n+1)            
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



def yaml_parse(filename, mode='text'):
    with open(filename, encoding='utf-8') as f:
        yml = yaml.safe_load(f)
    command = yml['command']

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
    return (prompts, appends, yml)

def read_file(filename):
    strs = []
    filenames = filename.split()
    for filename in filenames:
        try:
            with open(filename,'r',encoding='utf_8') as f:
                for i,item in enumerate(f.readlines()):
                    if re.match('^\s*#.*',item) or re.match('^\s*$',item):
                        continue
                    item = re.sub('\s*#.*$','',item)
                    try:
                        strs.append(item_split(item))
                    except:
                        print('Errro happen line %s %d %s' % (filename, i, item))
        except FileNotFoundError:
            print('%s is not found' % (filename))
            exit(-1)
    return strs

def item_split(item):
    if type(item) is not str:
        return [str(item)]
    item = item.replace('\n',' ').strip().replace('\;',r'${semicolon}')
    split = item.split(';')

    if type(split) is list:
        for i in range(0,len(split)):
           split[i] = split[i].replace(r'${semicolon}',';')
    return split

def prompt_replace(string,replace_texts,var):
    if type(string) is string:
        print("Repacing String is type error ",type(string))
        exit(-1)

    if type(replace_texts) is not list:
        replace_texts = [replace_texts]

    rep = replace_texts[0]
# $1 mode version <= 0.2, 0.4 expired
#    i = ''
#    if '1' <= var <= '9':
#        i = '$' + var
#    elif  '10' <= var <= '36':
#        n = int(var)
#        i = '$' + chr(n +97-10)
#    if type(string) is str:
#        string = string.replace(i,rep)
#    elif type(string) is dict: 
#        for key in string:
#            if type(string[key]) is str:
#                pass
#                string[key] = string[key].replace(i,rep)

# mode version >= 0.3
#    i = n + 1
    if type(string) is str:
        string = string.replace('${%s}' % (var),rep)
    elif type(string) is dict: 
        for key in string:
            if type(string[key]) is str:
                string[key] = string[key].replace('${%s}' % (var),rep)

    for j in range(0,len(replace_texts)):
        rep = replace_texts[j]
        k = j + 1
        if type(string) is str:
            string = string.replace('${%s,%d}' % (var,k),rep)
        elif type(string) is dict: 
            for key in string:
                if type(string[key]) is str:
                    string[key] = string[key].replace('${%s,%d}' % (var,k),rep)
    
    if type(string) is str:
        string = re.sub('\$\{%s,\d+\}' % (var) ,'',string)
        string = string.replace('${%s}' % (var) ,'')
    else:
        for key in string:
            if type(string[key]) is str:
                string[key] = re.sub('\$\{%s,\d+\}' % (var) ,'',string[key])
                string[key] = string[key].replace('${%s}' % (var) ,'')

    return string

def prompt_multiple(prompts,appends,console_mode,mode='text',variables_mode = False):
    if mode =='text':
        output_text = ''
    elif mode == 'json':
        output_text = []

    array = list(appends.values())
    keys = list(appends.keys())
    x = list(range(0,len(array[0])))
    if len(array) >= 2:
        for i in range(1,len(array)):
            a = list(range(0, len(array[i])))
            x = list(it.product(x,a))

    for i in x:
        new_prompt = copy.deepcopy(prompts)
        if type(i) is int:
            j = [i]
        else:
            j = list(i)
        for _ in (range(2,len(array))):
            if len(j) == 2:
                a,b = j[0]
                if type(a) is int:
                    j = [a,b,j[1]]
                else:
                    j = [a[0],a[1],b,j[1]]                    
            elif type(j[0]) != int:
                a,b = j[0]
                j2=j[1:]
                if type(a) is int:
                    j = [a,b]
                else:
                    j = [a[0],a[1],b]                    
                j.extend(j2)
        variables = {}
        for n,_ in enumerate(j):
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
                except:
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



def weight_calc(append,num,default_weight = 0.1,weight_mode = True):
    weight_append = []
    max_value = 0.0
    for i,item in enumerate(append):
        if len(item) == 1:
            weight = max_value + default_weight
            text = item[0]
        else:
            try:
                if weight_mode:
                    weight = max_value + float(item[0])
                else:
                    weight = max_value + default_weight
            except:
                print('float convert error append %d line %d %s use default' % (num + 1,i,item[0]))
                weight = max_value + default_weight
            finally:
                text = item[1:]

        weight_txt = {'weight':weight, 'text': text}

        max_value = weight_txt['weight']
        weight_append.append(weight_txt)        
    return (weight_append, max_value)


   
def prompt_random(prompts,appends,console_mode,max_number,weight_mode = False,default_weight = 0.1,mode = 'text',variables_mode = True):
    if mode =='text':
        output_text = ''
    elif mode == 'json':
        output_text = []

    keys = list(appends.keys())
    appends = list(appends.values())
    weight_appends = []
    for num,append in enumerate(appends):
        weighted = weight_calc(append, num, default_weight,weight_mode=weight_mode)
#           print(weighted)
        weight_appends.append(weighted)
    for _ in range(0,max_number):
        new_prompt = copy.deepcopy(prompts)
        variables = {}
        for i,weighted in enumerate(weight_appends):
            append, max_weight = weighted
            n = max_weight
            while n >= max_weight:
                n = random.uniform(0.0,max_weight)
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

def main(args):
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
        #yaml mode
        prompts, appends, yml = yaml_parse(prompt_file,mode = mode)
    else:
        #text mode
        appends = []
        prompts = ''
        dirs = os.listdir(current)
        sorted(dirs)
        for filename in dirs:
            path = os.path.join(current,filename)
            if os.path.isfile(path):
                appends.append(read_file(path))
        with open(prompt_file,'r',encoding='utf_8') as f:
            for l in f.readlines():
                prompts = prompts + ' ' + l.replace('\n','')


    if yml is not None and 'options' in yml and yml['options'] is not None:
        options = yml['options']
    else:
        options = {}

    console_mode = False
    if output is None and args.api_mode == False:
        if options.get('output'):
            output = options['output']
        else:
            console_mode = True
        

    if args.api_input_json == None and options.get('method') == 'random':
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
            output_text = prompt_multiple(prompts,yml['before_multiple'],console_mode = False,mode = mode
                ,variables_mode= args.api_filename_variables)
            if type(output_text) is list:
                multiple_text = []
                for prompts in output_text:
                    result = prompt_random(prompts,appends,console_mode,max_number,weight_mode = weight_mode,default_weight = default_weight,mode = mode
                                    ,variables_mode= args.api_filename_variables)
                    for item in result:
                        multiple_text.append(item)
            else:
                multiple_text = ''
                for prompts in output_text.split('\n'):
                    multiple_text += prompt_random(prompts,appends,console_mode,max_number,weight_mode = weight_mode,default_weight = default_weight,mode = mode
                                                        ,variables_mode= args.api_filename_variables)
            output_text = multiple_text
        else:
            if 'appends_multiple' in yml:
                output_text = prompt_random(prompts,appends,False,max_number,weight_mode = weight_mode,default_weight = default_weight,mode = mode
                                                    ,variables_mode= args.api_filename_variables)
            else:
                output_text = prompt_random(prompts,appends,console_mode,max_number,weight_mode = weight_mode,default_weight = default_weight,mode = mode
                                                    ,variables_mode= args.api_filename_variables)
        if 'appends_multiple' in yml:
            if type(output_text) is list:
                multiple_text = []
                for prompts in output_text:
                    result = prompt_multiple(prompts,yml['appends_multiple'],console_mode,mode = mode
                                                        ,variables_mode= args.api_filename_variables)
                    for item in result:
                        multiple_text.append(item)
            else:
                multiple_text = ''
                for prompts in output_text.split('\n'):
                    multiple_text += prompt_multiple(prompts,yml['appends_multiple'],console_mode,mode = mode
                                                        ,variables_mode= args.api_filename_variables)
            output_text = multiple_text
    else:
        output_text = prompt_multiple(prompts,appends,console_mode,mode = mode)

    if output is not None:
        with open(output,'w',encoding='utf-8',newline='\n') as fw:
            if type(output_text) is str:
                fw.write(output_text)
            else:
                json.dump(output_text,fp=fw,indent=2)
    
    if args.api_input_json:
        with open(args.api_input_json,'r',encoding='utf-8') as f:
            output_text = f.read()
    
    if options.get('filename_pattern'):
        args.api_filename_pattern = args.api_filname_pattern or options['filename_pattern']

    opt = {}
    if args.api_filename_pattern is not None:
        opt = {'filename_pattern': args.api_filename_pattern}

    if args.num_length is not None:
        opt = {'num_length':  args.num_length}

    if args.api_userpass is not None:
        opt = {'userpass':  args.api_userpass}


    if args.api_mode:
        sd_model = options.get('sd_model') or args.api_set_sd_model
        if sd_model is not None:
            set_sd_model(base_url=args.api_base,sd_model=sd_model)
        init()
        txt2img(output_text, base_url=args.api_base, output_dir=args.api_output_dir,opt=opt)
        shutdown()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('input', type=str,
                        default='./prompt.txt',
                        help='input promptfile')
    parser.add_argument('--append-dir', type=str,
                        default='./appends',
                        help='direcory of input append prompt files')
    parser.add_argument('--output', type=str,
                        default=None,
                        help='direcory of output file of prompt list file')

    parser.add_argument('--json', type=bool,nargs='?',
                        const=True, default=False,
                        help='output JSON')

    parser.add_argument('--api-mode', type=bool,nargs='?',
                        const=True, default=False,
                        help='output api force set --json')

    parser.add_argument('--api-base', type=str,
                        default='http://127.0.0.1:7860',
                        help='direct call api e.g http://127.0.0.1:7860')


    parser.add_argument('--api-userpass', type=str,
                        default=None,
                        help='API username:password')

    ## 
    #parser.add_argument('--api-name', type=str,
    #                    default='txt2img',
    #                    help='call api txt2img/img2img')

    #parser.add_argument('--image-path', type=str,
    #                    default='./inputs',
    #                    help='img2img path')

    #parser.add_argument('--mask-path', type=str,
    #                    default='./inputs-mask',
    #                    help='img2img mask path')


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

    parser.add_argument('--api-filename-variables', type=bool,nargs='?',
                        const=True, default=False,
                        help='replace variables use filename')

    parser.add_argument('--api-set-sd-model', type=str,
                        default=None,
                        help='Change sd model "Filename.ckpt [hash]" e.g. "wd-v1-3.ckpt [84692140]"')

    args = parser.parse_args()
    main(args)