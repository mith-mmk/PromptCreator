#!/bin/python3
#!pip install pyyaml
#!pip install Pillow
#!pip install httpx

# version 0.5 (C) 2022 MITH@mmk
import os
import yaml
import argparse
import itertools as it
import re
import random
import json
import copy

import io
import base64
from PIL import Image, PngImagePlugin

import httpx
import asyncio
import time

async def async_post(url,data):
    headers = {
        'Content-Type': 'application/json',
    }
    async with httpx.AsyncClient() as client:
        try:
            return await client.post(url,data=data,headers=headers,timeout=(5,10000))
        except httpx.ReadTimeout:
            print('Read timeout')
            return None
        except httpx.TimeoutException:
            print('Connect Timeout')
            return None
        except BaseException as error:
            print('Exception',error)
            return None

async def progress_writer(url,data,progress_url):
    headers = {
        'Content-Type': 'application/json',
    }
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
                string = '\033[KWait Web UI is resource using [{}{}] {:.1f}%  {} step ({:d}/{:d}) {:.2f} sec'.format(
                    sharp,space,right,job,step,steps,elapsed_time
                )

            print(string,end='\r')

        async def progress_get(progress_url):
            async with httpx.AsyncClient() as client:
                retry = 0
                start_time = time.time()
                response = await client.get(progress_url)
                result = response.json()
                right = 1.0
                await write_progress(result,start_time)
                await asyncio.sleep(1.0) # initializing wait
                while right != 0.0:
                    await asyncio.sleep(0.1)
                    try: 
                        response = await client.get(progress_url)
                        retry = 0
                        result = response.json()
                        right = result['progress']
                        await write_progress(result,start_time)
                    except:
                        retry += 1
                        if retry >= 10:
                            print('Progress is unknown')
                            return

        tasks = [
            client.post(url,data=data,headers=headers,timeout=(5,10000)),
            progress_get(progress_url)
        ]
        result = await asyncio.gather(*tasks, return_exceptions=False)
    return result[0]

# force interrupt process
async def progress_interrupt(url):
    async with httpx.AsyncClient() as client:
        try:
            return await client.post(url)
        except httpx.ReadTimeout:
            print('Read timeout')
            return None
        except httpx.TimeoutException:
            print('Connect Timeout')
            return None
        except BaseException as error:
            print('Exception',error)
            return None

def request_post_wrapper(url,data,progress_url=None,base_url=None):
    try:
        if progress_url is not None:
            result = asyncio.run(progress_writer(url,data,progress_url))
        else:
            result = asyncio.run(async_post(url,data))
    except KeyboardInterrupt:
        if base_url:
            asyncio.run(progress_interrupt(base_url + '/sdapi/v1/interrupt'))
        print('enter Ctrl-c, Process stopping')
        exit(2)
    except httpx.ConnectError:
        print('All connection attempts failed,Is the server down?')
        exit(2)
    except httpx.ConnectTimeout:
        print('Connection Time out,Is the server down or server address mistake?')
        exit(2)
    return result

def normalize_base_url(base_url):
    if base_url[-1] == '/':
        base_url = base_url[:-1]
    return base_url

def create_parameters(parameters_text):
    para = parameters_text.split('\n')
    parameters = {}
    parameters['prompt'] = para[0]
    parameters['negative_prompt'] = para[1].replace('Negative prompt: ','')
    options = para[2].split(',')
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

def create_img2json(imagefile):
    schema = [
        'enable_hr',
        'denoising_strength',
        'firstphase_width',
        'firstphase_height',
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
        'sampler_index'
    ]

    image = Image.open(imagefile)
    image.load()
    if image.info['parameters'] is not None:
        parameter_text = image.info['parameters']
        parameters = create_parameters(parameter_text)
    else:
        parameters = {}
    buffer = io.BytesIO()
    image.save(buffer, 'png')
    init_image = base64.b64encode(buffer.getvalue()).decode("ascii")
    json_raw = {}
    json_raw['init_images'] = ['dummy;dummy,' + init_image] # 11/07/2022 version img2img api dummy string need,yet 
    override_setting = {}
    for key in parameters.keys():
        if key in schema:
            json_raw[key] = parameters[key]
        else:
            override_setting[key] = parameters[key]

    json_raw['override_setting'] = override_setting
    return json_raw

def img2img(imagefiles,overrides=None,base_url='http://127.0.0.1:8760',output_dir='./outputs'):
    base_url = normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/img2img')
    progress = base_url + '/sdapi/v1/progress?skip_current_image=false'
    print ('Enter API, connect', url)
    dir = output_dir
    print('output dir',dir)
    os.makedirs(dir,exist_ok=True)
#    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(imagefiles)
    num = -1
    files = os.listdir(dir)
    for file in files:
        if os.path.isfile(os.path.join(dir,file)):
            name = file[0:5]
            try:
                num = max(num,int(name))
            except:
                pass
    num += 1
    print('API loop count is %d times' % (count))
    print('')
    flash = ''
    for (n,imagefile) in enumerate(imagefiles):
        item = create_img2json(imagefile)
        if overrides is not None:
            if type(overrides) is list:
                override = overrides[n]
            else:
                override = overrides
            for key,value in override.items():
                item[key] = value

        print(flash,end = '')
        print('\033[KBatch %d of %d' % (n+1,count))
        # Why is an error happening? json=payload or json=item
        payload = json.dumps(item)
        response = request_post_wrapper(url, data=payload, progress_url=progress,base_url=base_url)

        if response is None:
            print('http connection - happening error')
            exit(-1)
        if response.status_code != 200:
            print ('\033[KError!',response.status_code, response.text)
            print('\033[%dA' % (2),end='')
            continue

        r = response.json()
        load_r = json.loads(r['info'])
#        meta = load_r["infotexts"][0]
        print('\033[Kreturn %d images' % (len(r['images'])))
        for i in r['images']:
            try:
                meta = load_r["infotexts"][i]

#                image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[1])))
                image = Image.open(io.BytesIO(base64.b64decode(i)))
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", meta)
                seed = re.findall('Seed: (\d+),', meta)
                filename = str(num).zfill(5) +'-' +  str(seed[0]) + '.png'
                print('\033[Ksave... ',filename)
                filename = os.path.join(dir,filename)
                num += 1
                image.save(filename , pnginfo=pnginfo)
            except KeyboardInterrupt:
                print ('\033[KProcess stopped',e)
                exit(2)
            except BaseException as e:
                print ('\033[Ksave error',e)
        prt_cnt = len(r['images']) + 2
        flash = '\033[%dA' % (prt_cnt)
    print('')

# 2022-11-07 cannot run yet
def iterrogate(imagefile,base_url):
    base_url = normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/interrogate')
    print ('Iterrogate mode, connect', url)
    json_raw = create_img2json(imagefile)
    payload = json.dumps({'image': json_raw['init_image']})
    response = request_post_wrapper(url, data=payload, progress_url=None,base_url=base_url)
    print(response)
    return response


def txt2img(output_text,base_url='http://127.0.0.1:8760',output_dir='./outputs'):
    base_url = normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/txt2img')
    progress = base_url + '/sdapi/v1/progress?skip_current_image=false'
    print ('Enter API mode, connect', url)
    dir = output_dir
    print('output dir',dir)
    os.makedirs(dir,exist_ok=True)
#    dt = datetime.datetime.now().strftime('%y%m%d')

    num = -1
    files = os.listdir(dir)
    for file in files:
        if os.path.isfile(os.path.join(dir,file)):
            name = file[0:5]
            try:
                num = max(num,int(name))
            except:
                pass
    num += 1
    count = len(output_text)
    print('API loop count is %d times' % (count))
    print('')
    flash = ''
    for (n,item) in enumerate(output_text):
        print(flash,end = '')
        print('\033[KBatch %d of %d' % (n+1,count))
        # Why is an error happening? json=payload or json=item
        payload = json.dumps(item)
        response = request_post_wrapper(url, data=payload, progress_url=progress,base_url=base_url)

        if response is None:
            print('http connection - happening error')
            exit(-1)
        if response.status_code != 200:
            print ('\033[KError!',response.status_code, response.text)
            print('\033[%dA' % (2),end='')
            continue

        r = response.json()
        load_r = json.loads(r['info'])
        meta = load_r["infotexts"][0]
        print('\033[Kreturn %d images' % (len(r['images'])))
        for i in r['images']:
            try:
#                image = Image.open(io.BytesIO(base64.b64decode(i.split(",",1)[1])))
                image = Image.open(io.BytesIO(base64.b64decode(i)))
                pnginfo = PngImagePlugin.PngInfo()
                pnginfo.add_text("parameters", meta)
                seed = re.findall('Seed: (\d+),', meta)
                filename = str(num).zfill(5) +'-' +  str(seed[0]) + '.png'
                print('\033[Ksave... ',filename)
                filename = os.path.join(dir,filename)
                num += 1
                image.save(filename , pnginfo=pnginfo)
            except KeyboardInterrupt:
                print ('\033[KProcess stopped',e)
                exit(2)
            except BaseException as e:
                print ('\033[Ksave error',e)
        prt_cnt = len(r['images']) + 2
        flash = '\033[%dA' % (prt_cnt)
    print('')


def yaml_parse(filename, mode='text'):
    with open(filename, encoding='utf-8') as f:
        yml = yaml.safe_load(f)
    command = yml['command']
    appends = {}

    for n,items in enumerate(yml['appends']):
        if type(yml['appends']) is dict:
            key = items
            items = yml['appends'][items]

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
        appends[key] = append
    if 'appends_multiple' in yml:
        appends_multiple = {}
        for n,items in enumerate(yml['appends_multiple']):
            if type(yml['appends_multiple']) is dict:
                key = items
                items = yml['appends_multiple'][items]
            else:
                key = str(n+1)            

            if type(items) is str:
                # filemode
                appends_multiple = read_file(items)
            else:
                # inline mode
                append = []
                for item in items:
                    append.append(item_split(item))
            appends_multiple[key] = append
        yml['appends_multiple'] = appends_multiple

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
                    if re.match('^\s*#.+',item) or re.match('^\s*$',item):
                        continue
                    item = re.sub('\s*#.+$','',item)
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
        string = re.sub(r'\$\{%s,\d*?\}' % (var) ,'',string)
        string = string.replace(r'\${%s}' % (var) ,'')
    return string

def prompt_multiple(prompts,appends,console_mode,mode='text'):
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
        for n,_ in enumerate(j):
            re_str = appends[keys[n]][j[n]]
            var = keys[n]
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
            output_text.append(new_prompt)
    return output_text



def weight_calc(append,num,default_weight = 0.1):
    weight_append = []
    max_value = 0.0
    for i,item in enumerate(append):
        if len(item) == 1:
            weight = max_value + default_weight
            text = item[0]
        else:
            try:
                weight = max_value + float(item[0])
            except:
                print('float convert error append %d line %d %s use default' % (num + 1,i,item[0]))
                weight = max_value + default_weight
            finally:
                text = item[1:]

        weight_txt = {'weight':weight, 'text': text}

        max_value = weight_txt['weight']
        weight_append.append(weight_txt)        
    return (weight_append, max_value)


   
def prompt_random(prompts,appends,console_mode,max_number,weight_mode = False,default_weight = 0.1,mode = 'text'):
    if mode =='text':
        output_text = ''
    elif mode == 'json':
        output_text = []

    keys = list(appends.keys())
    appends = list(appends.values())
    if weight_mode == False:
        for _ in range(0,max_number):
            new_prompt = copy.deepcopy(prompts)
            for i in range(0,len(appends)):
                n = random.randint(0,len(appends[i])-1)
                re_str = appends[i][n]
                var = keys[i]
                new_prompt = prompt_replace(new_prompt, re_str, var)
            if console_mode:
                print(new_prompt)
            else:
                if mode == 'text':
                    output_text = output_text + new_prompt + '\n'
                elif mode == 'json':
                    output_text.append(new_prompt)
    else:   # weighted
        weight_appends = []
        for num,append in enumerate(appends):
            weighted = weight_calc(append, num, default_weight)
#            print(weighted)
            weight_appends.append(weighted)

        for _ in range(0,max_number):
            new_prompt = copy.deepcopy(prompts)
            for i,weighted in enumerate(weight_appends):
                append, max_weight = weighted
                n = max_weight
                while n >= max_weight:
                    n = random.uniform(0.0,max_weight)

                pos = int(len(append) / 2)
                cnt = int((len(append) + 1) / 2)
                while True:
                    w = append[pos]['weight']
#                    print (cnt,pos,n,w)
                    if n < w:
                        if pos == 0:
                            break
                        if n >= append[pos - 1]['weight']:
#                            print ('break')
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
#                print (n,pos)
                var = keys[i]
                re_str = append[pos]['text']
#                print(var, re_str)
                new_prompt = prompt_replace(new_prompt, re_str, var)
            if console_mode:
                print(new_prompt)
            if mode == 'text':
                output_text = output_text + new_prompt + '\n'
            elif mode == 'json':
                output_text.append(new_prompt)
    return output_text

def main():
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
                        help='direct call api ex http://127.0.0.1:7860')

    ## default from .env ?
    #parser.add_argument('--api-input-dir', type=str,
    #                    default='inputs',
    #                    help='api input image directory for img2img')

    parser.add_argument('--api-output-dir', type=str,
                        default='outputs',
                        help='api output image directory')

    parser.add_argument('--max-number', type=int,
                        default=-1,
                        help='override option.number for yaml mode')


    args = parser.parse_args()

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
        options = None

    console_mode = False
    if output is None and args.api_mode == False:
        if options is not None and 'output' in options and options['output'] is not None:
            output = options['output']
        else:
            console_mode = True
        

    if options is not None and 'method' in options and options['method'] == 'random':
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

        output_text = prompt_random(prompts,appends,console_mode,max_number,weight_mode = weight_mode,default_weight = default_weight,mode = mode)
        if 'appends_multiple' in yml:
            if type(output_text) is list:
                multiple_text = []
                for prompts in output_text:
                    result = prompt_multiple(prompts,yml['appends_multiple'],console_mode,mode = mode)
                    for item in result:
                        multiple_text.append(item)
            else:
                multiple_text = ''
                for prompts in output_text.split('\n'):
                    multiple_text += prompt_multiple(prompts,yml['appends_multiple'],console_mode,mode = mode)             

            output_text = multiple_text
    else:
        output_text = prompt_multiple(prompts,appends,console_mode,mode = mode)

    if output is not None:
        with open(output,'w',encoding='utf-8',newline='\n') as fw:
            if type(output_text) is str:
                fw.write(output_text)
            else:
                json.dump(output_text,fp=fw,indent=2)

    if args.api_mode:
        txt2img(output_text, base_url=args.api_base, output_dir=args.api_output_dir)

if __name__ == "__main__":
    main()