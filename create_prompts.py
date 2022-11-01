#!/bin/python3
#!pip3 install pyyaml

# version 0.3 (C) 2022 MITH@mmk
import os
import yaml
import argparse
import itertools as it
import re
import random
import json

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
#    print(appends)

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
        with open(filename,'r',encoding='utf_8') as f:
            for i,item in enumerate(f.readlines()):
                if re.match('^\s*#.+',item) or re.match('^\s*$',item):
                    continue
                item = re.sub('\s*#.+$','',item)
                try:
                    strs.append(item_split(item))
                except:
                    print('Errro happen line %s %d %s' % (filename, i, item))
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
    # mode version <= 0.2
    rep = replace_texts[0]
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
        string = re.sub(r'\${%s,.*?}' % (var) ,'',string)
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
        new_prompt = prompts
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
        else:
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
            new_prompt = prompts
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
            new_prompt = prompts
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
            else:
                if mode == 'text':
                    output_text = output_text + new_prompt + '\n'
                elif mode == 'json':
                    output_text.append(new_prompt)
    return output_text

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

parser.add_argument('--api-mode', type=bool,
                    default=False,
                    help='output api mode(JSON)')

# parser.add_argument('--api-url', type=str,
#                    default=None,
#                    help='direct call api ex http://127.0.0.1:7860/sdapi/v1/txt2img ')

## default from .env ?
# parser.add_argument('--api-input-dir', type=bool,
#                    default='./',
#                    help='api input image directory for img2img')

## default from .env ?
# parser.add_argument('--api-output-dir', type=bool,
#                    default='./',
#                    help='api output image directory')


args = parser.parse_args()

if args.api_mode:
    mode = 'json'
else:
    mode = 'text'

current = args.append_dir
prompt_file = args.input

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

if args.output is None:
    console_mode = True
else:
    console_mode = False


if yml is not None and 'options' in yml and 'method' in yml['options'] and yml['options']['method'] == 'random':
    options = yml['options']
    max_number = 100
    if options is not None and 'number' in options:
        max_number = options['number']

    flag = False
    if options is not None and 'weight' in options:
        flag = options['weight']
    if options is not None and 'default_weight' in options:
        default_weight = options['default_weight']
    else:
        default_weight = 0.1
    output_text = prompt_random(prompts,appends,console_mode,max_number,weight_mode = flag,default_weight = default_weight,mode = mode)   
else:
    output_text = prompt_multiple(prompts,appends,console_mode,mode = mode)

if args.output is not None:
    with open(args.output,'w',encoding='utf-8',newline='\n') as fw:
        if type(output_text) is str:
            fw.write(output_text)

        else:
            json.dump(output_text,fp=fw,indent=2)
