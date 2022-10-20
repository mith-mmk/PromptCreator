import os
import yaml
import argparse
import itertools as it

def yaml_parse(filename):
    with open(filename) as f:
        yml = yaml.safe_load(f)
    command = yml['command']
    appends = yml['appends']

    prompts = ''

    for key, item in command.items():
        if type(item) is str:
            prompts = prompts + '--' + key + ' "' + item + '" '
        else:
            prompts = prompts + '--' + key + ' ' + str(item) + ' '
    return (prompts, appends, yml)

def readFile(filename):
    strs = []
    with open(filename,'r',encoding='utf_8') as f:
        for str in f.readlines():
            str = str.replace('\n','')
            strs.append(str)
    return strs

def prompt_multiple(prompts,appends,console_mode):
    x = list(range(0,len(appends[0])))
    if len(appends) >= 2:
        for i in range(1,len(appends)):
            a = list(range(0, len(appends[i])))
            x = list(it.product(x,a))

    output_text = ''
    for i in x:
        new_prompt = prompts
        if type(i) is int:
            j = [i]
        else:
            j = list(i)
        for k in (range(2,len(appends))):
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
            rep = '$' + str(n+1)
            new_prompt = new_prompt.replace(rep,str(appends[n][j[n]]))
        if console_mode:
            print(new_prompt)
        else:
            output_text = output_text + new_prompt + '\n'
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

args = parser.parse_args()

current = args.append_dir
prompt_file = args.input

ext = os.path.splitext(prompt_file)[-1:][0]
if ext == '.yaml' or ext == '.yml':
    #yaml mode
    prompts, appends, _ = yaml_parse(prompt_file)
else:
    #text mode
    appends = []
    prompts = ''
    dirs = os.listdir(current)
    sorted(dirs)
    for filename in dirs:
        path = os.path.join(current,filename)
        if os.path.isfile(path):
            appends.append(readFile(path))
    with open(prompt_file,'r',encoding='utf_8') as f:
        for l in f.readlines():
            prompts = prompts + ' ' + l.replace('\n','')

if args.output is None:
    console_mode = True
else:
    console_mode = False


output_text = prompt_multiple(prompts,appends,console_mode)

if args.output is not None:
    with open(args.output,'w',encoding='utf-8',newline='\n') as fw:
        fw.write(output_text)