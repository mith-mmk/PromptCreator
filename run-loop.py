#!/usr/bin/env python3
import os
import time
import datetime
import random
import subprocess
import shutil
import glob
import csv
import yaml
import logging

import img2img
import create_prompts

from modules.stdprint import Print

# FULL AUTOMATIC CRATE IMAGES FROM STABLE DIFFUSION script
# MIT License (C) 2023 mith@mmk

# sample fuction call from create_prompts.py and img2img_from_args()

# API
HOST = 'http://localhost:7860'

IMG2IMG_BASE = './outputs/$retake/'
OUTPUT_DIR = './outputs/'
IMG2IMG_OUTPUR_DIR = './outputs/'
CONFIG_BASE = './prompts/'

# LOG
LOG_PATH = './log/'
LOG_DAYS = 7

# MODEL BASE model clone from nas, if exists
MODEL_CLONE = False
MODEL_SRC = 'test:/ai/models/'
MODEL_DEST = '/var/ai/models/'

PROMPT_BASE = './prompts/'
CONFIG = CONFIG_BASE + 'config.yaml'

PROMPT_PREFIX = 'prompts-girls-'
PROMPT_EXCEPTION_PREFIX = 'prompts-'
PROMPT_SUFFIX = '.yaml'

FOLDER_SUFFIX = '-images'

# CONFIG COMPATIBLE
MODEL_CSV = os.path.join(CONFIG_BASE, 'models.csv')
PROMPT_CSV = os.path.join(CONFIG_BASE, 'prompts.csv')
EXCEPTION_LIST = os.path.join(CONFIG_BASE, 'prompts.txt')

# IMG2IMG DIRECTORIES
INPUT_DIR = os.path.join(IMG2IMG_BASE, 'batch')
WORK_DIR = os.path.join(IMG2IMG_BASE, '.work')
INPUT_APPEND = os.path.join(IMG2IMG_BASE + 'modified')
INPUT_MASK = os.path.join(IMG2IMG_BASE, 'mask')
ENDED_DIR = os.path.join(IMG2IMG_BASE, '$end')

# DEFAULT OPTIONS
START_HOUR = 7
STOP_HOUR = 18
IMG2IMG_STEPS = 6
IMG2IMG_DENOSING_STRINGTH = 0.6
IMG2IMG_N_ITER = 1
IMG2IMG_BATCH_SIZE = 1

ABORT_MATRIX = {
    'BOTH': ['sfw', 'nsfw'],
    'SFW': ['sfw'],
    'NSFW': ['nsfw'],
    'XL': ['xl', 'xl-sfw', 'xl-nsfw'],
    'XLSFW': ['xl-sfw'],
    'XLNSFW': ['xl-nsfw'],
    'SKIP': None
}

stdprint = Print()


def load_models_csv(filename):
    # file check
    if not (os.path.exists(filename)):
        return []
    models = []
    with open(filename) as f:
        reader = csv.reader(f)
        # model_name,vae,mode,
        for row in reader:
            model = {
                'model_name': row[0],
                'vae': row[1],
                'mode': row[2],
            }
            models.append(model)
    return models


def load_prompts_csv(filename):
    if not (os.path.exists(filename)):
        return []
    prompts = []
    with open(PROMPT_CSV) as f:
        reader = csv.reader(f)
        # prompt_name,folder,number,genre,
        for row in reader:
            if len(row) < 4:
                continue
            prompt = {
                'prompt_name': row[0],
                'folder': row[1],
                'number': row[2],
                'genre': row[3],
                'file_pattern': row[4],
            }
            prompts.append(prompt)
    return prompts


def load_not_default(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            not_girls = f.read().splitlines()
        return not_girls
    else:
        return []


def log_remover(log):
    # 7日以上前のログを削除
    for f in glob.glob(os.path.join(log['path'], '*.log')):
        if os.path.getmtime(f) < time.time() - log['days'] * 24 * 60 * 60:
            os.remove(f)


# loopごとに読み直す
def load_config(config_file):
    prefix = {
        'default': PROMPT_PREFIX,
        'exception': PROMPT_EXCEPTION_PREFIX,
        'exception_list': EXCEPTION_LIST,
        'suffix': PROMPT_SUFFIX,
    }
    txt2img = {
        'prompts': None,
        'prompt_base': PROMPT_BASE,
        'output': OUTPUT_DIR,
        'models': None,
        'prefix': prefix,
        'abort_matrix': ABORT_MATRIX,
        'coef_matrix': [],
        'folder_suffix': FOLDER_SUFFIX,
        'overrides': '',
    }
    image_dirs = {
        'input': INPUT_DIR,
        'work': WORK_DIR,
        'append': INPUT_APPEND,
        'mask': INPUT_MASK,
        'ended': ENDED_DIR,
        'output': IMG2IMG_OUTPUR_DIR,
        'folder_suffix': FOLDER_SUFFIX,
    }
    img2img = {
        'steps': IMG2IMG_STEPS,
        'denosing_strength': IMG2IMG_DENOSING_STRINGTH,
        'n_iter': IMG2IMG_N_ITER,
        'batch_size': IMG2IMG_BATCH_SIZE,
        'file_pattern': '[num]-[seed]',
        'dir': image_dirs
    }
    log = {
        'path': LOG_PATH,
        'days': LOG_DAYS,
        'level': logging.INFO,
    }
    clone = {
        'clone': MODEL_CLONE,
        'src': MODEL_SRC,
        'dest': MODEL_DEST,
        'folders': [
            'Stable-Diffusion',
            'Lora',
            'embeddings',
            'vae'],
    }
    loop = {
        'mode': False,
        'loop_count': 0,
        'commands': ['clone', 'check', 'ping', 'txt2img', 'img2img', 'sleep 1']
    }
    config = {
        'host': HOST,
        'prompt_base': PROMPT_BASE,
        'start_hour': START_HOUR,
        'stop_hour': STOP_HOUR,
        'txt2img': txt2img,
        'img2img': img2img,
        'log': log,
        'clone': clone,
        'custom': False,   # dispose custom
        'loop': loop,
    }
    # CONFIG ファイルがない場合
    if not os.path.exists(config_file):
        txt2img['prompts'] = load_prompts_csv(PROMPT_CSV)
        txt2img['models'] = load_models_csv(MODEL_CSV)
        txt2img['exception_list'] = load_not_default(EXCEPTION_LIST)
        config['txt2img'] = txt2img
        return config

    with open(config_file, 'r', encoding='utf-8') as f:
        yaml_config = yaml.safe_load(f)
        if 'host' in yaml_config:
            config['host'] = yaml_config['host']
        if 'promppt_base' in yaml_config:
            config['prompt_base'] = yaml_config['prompt_base']
        if 'schedule' in yaml_config:
            schedule = yaml_config['schedule']
            if 'start' in schedule:
                config['start_hour'] = schedule['start']
            if 'stop' in yaml_config['schedule']:
                config['stop_hour'] = schedule['stop']
        if 'loop' in yaml_config:
            loop_config = yaml_config['loop']
        else:
            loop_config = {}
        if 'mode' in loop_config:
            config['loop']['mode'] = loop_config['mode']
        if 'loop_count' in loop_config:
            config['loop']['loop_count'] = loop_config['loop_count']
        if 'commands' in loop_config:
            config['loop']['commands'] = loop_config['commands']

        if 'clone' in yaml_config:
            clone_config = yaml_config['clone']
            if 'clone' in clone:
                clone['clone'] = clone_config['clone']
            if 'src' in clone:
                clone['src'] = clone_config['src']
            if 'dest' in clone:
                clone['dest'] = clone_config['dest']
            if 'folders' in clone:
                clone['folders'] = clone_config['folders']
 
        if 'txt2img' in yaml_config:
            txt_config = yaml_config['txt2img']
        else:
            txt_config = {}
        
        if 'output' in txt_config:
            txt2img['output'] = txt_config['output']
        
        if 'overrides' in txt_config:
            txt2img['overrides'] = txt_config['overrides']

        if 'prompts' in txt_config:
            if type(txt_config['prompts']) == str:
                txt2img['prompts'] = load_prompts_csv(txt_config['prompts'])
            else:
                prompts = []
                for prompt in txt_config['prompts']:
                    [prompt_name, folder, number, genre, file_pattern] = prompt.split(',')
                    prompt = {
                        'prompt_name': prompt_name,
                        'folder': folder,
                        'number': number,
                        'genre': genre,
                        'file_pattern': file_pattern
                    }
                    prompts.append(prompt)
                txt2img['prompts'] = prompts

        if 'abort_matrix' in txt_config:
            txt2img['abort_matrix'] = txt_config['abort_matrix']

        if 'coef_matrix' in txt_config:
            txt2img['coef_matrix'] = txt_config['coef_matrix']

        if 'folder_suffix' in yaml_config:
            config['folder_suffix'] = yaml_config['folder_suffix']
    
        if 'prefix' in txt_config:
            prefix = txt_config['prefix']
            if 'default' in prefix:
                txt2img['prefix']['default'] = prefix['default']
            if 'exception' in prefix:
                txt2img['prefix']['exception'] = prefix['exception']
            if 'exception_list' in prefix:
                txt2img['prefix']['exception_list'] = prefix['exception_list']
            if 'suffix' in prefix:
                txt2img['prefix']['suffix'] = prefix['suffix']

        if 'models' in txt_config:
            if type(txt_config['models']) == str:
                txt2img['models'] = load_models_csv(txt_config['models'])
            else:
                list = txt_config['models']
                models = []
                for model in list:
                    [model_name, vae, mode] = model.split(',')
                    model = {
                        'model_name': model_name,
                        'vae': vae,
                        'mode': mode,
                    }
                    models.append(model)
                txt2img['models'] = models

        if 'log' in yaml_config:
            log = yaml_config['log']
            if not ('days' in log):
                log['days'] = LOG_DAYS
            if not ('path' in log):
                log['path'] = LOG_PATH
            if 'level' in log:
                match log['level']:
                    case 'debug':
                        log_level = logging.DEBUG
                    case 'info':
                        log_level = logging.INFO
                    case 'warning':
                        log_level = logging.WARNING
                    case 'error':
                        log_level = logging.ERROR
                    case 'critical':
                        log_level = logging.CRITICAL
                    case _:
                        log_level = logging.INFO
                log['level'] = log_level
            if 'print_levels' in log:
                global stdprint
                stdprint = Print(log['print_levels'])
            config['log'] = log

        today = datetime.datetime.now().strftime('%Y%m%d')
        logfile = os.path.join(log['path'], today + '.log')
        logging.basicConfig(filename=logfile, level=log['level'])
        log_remover(log)

        dirs = config['img2img']['dir']

        if 'img2img' in yaml_config:
            img_config = yaml_config['img2img']
            if 'steps' in img_config:
                img2img['steps'] = img_config['steps']
            if 'denosing_strength' in img_config:
                img2img['denosing_strength'] = img_config['denosing_strength']
            if 'n_iter' in img_config:
                img2img['n_iter'] = img_config['n_iter']
            if 'batch_size' in img_config:
                img2img['batch_size'] = img_config['batch_size']
            if 'file_pattern' in img_config:
                img2img['file_pattern'] = img_config['file_pattern']
            if 'dir' in img_config:
                dirs = img_config['dir']
                stdprint.debug(dirs)
                if 'input' in dirs:
                    image_dirs['input'] = dirs['input']
                if 'work' in dirs:
                    image_dirs['work'] = dirs['work']
                if 'append' in dirs:
                    image_dirs['append'] = dirs['append']
                if 'mask' in dirs:
                    image_dirs['mask'] = dirs['mask']
                if 'ended' in dirs:
                    image_dirs['ended'] = dirs['ended']
                if 'output' in dirs:
                    image_dirs['output'] = dirs['output']
                if 'folder_suffix' in dirs:
                    image_dirs['folder_suffix'] = dirs['folder_suffix']
                stdprint.debug(image_dirs)
            config['img2img'] = img2img
    return config


# sleep time
def check_time(config_file):
    config = load_config(config_file)
    start_hour = config['start_hour']
    stop_hour = config['stop_hour']
    now = datetime.datetime.now()
    if not (now.hour >= start_hour and now.hour < stop_hour):
        stdprint.info(f'sleeping...{now.hour} running between {start_hour} and {stop_hour}')
    while not (now.hour >= start_hour and now.hour < stop_hour):
        time.sleep(60)
        config = load_config(config_file)
        start_hour = config['start_hour']
        stop_hour = config['stop_hour']
        now = datetime.datetime.now()


def custom(args):
    subprocess.run(args)


def run_custom(command, *args):
    stdprint.info(f'custom {command}')
    logging.info(f'custom {command}')
    
        
def model_copy(clone):
    src_dir = clone['src']
    dest_dir = clone['dest']
    folders = clone['folders']
    for folder in folders:
        src = os.path.join(src_dir, folder)
        dest = os.path.join(dest_dir, folder)
        if not os.path.exists(dest):
            os.makedirs(dest)
        stdprint.info(f'copying {src} to {dest}')
        logging.info(f'copying {src} to {dest}')
        if os.name == 'nt':
            subprocess.Popen(['robocopy', src, dest, '/NP', '/J', '/R:1', '/W:1', '/FFT'], stdout=subprocess.DEVNULL)
            stdprint.verbose('robocopy', src, dest, '/NP', '/J', '/R:1', '/W:1', '/FFT')
        else:
            dest = dest.replace('\\', '/')
            # dest の最後を / にする
            if dest[-1] != '/':
                dest = dest + '/'
            subprocess.Popen(['rsync', '-av', src, dest], stdout=subprocess.DEVNULL)
            stdprint.verbose('rsync', '-av', src, dest)


def run_img2img(config):
    host = config['host']
    config = config['img2img']
    img2img_steps = config['steps']
    img2img_denosing_stringth = config['denosing_strength']
    img2img_n_iter = config['n_iter']
    img2img_batch_size = config['batch_size']
    file_pattern = config['file_pattern']
    dirs = config['dir']
    input_dir = dirs['input']
    work_dir = dirs['work']
    input_append = dirs['append']
    input_mask = dirs['mask']
    ended_dir = dirs['ended']
    output_dir = dirs['output']
    folder_suffix = dirs['folder_suffix']

    stdprint.debug(config)

    # INPUT_DIRの下のフォルダ取得する
    folders = glob.glob(os.path.join(input_dir, '*'))
    stdprint.verbose(input_dir)
    stdprint.verbose(folders)

    for folder in folders:
        stdprint.verbose(f'processing folder {folder}')
        files = glob.glob(os.path.join(folder, '*.png'))
        files.extend(glob.glob(os.path.join(folder, '*.jpg')))
        if len(files) == 0:
            stdprint.verbose(f'no files in {folder}')
            continue
        for file in files:
            stdprint.verbose(f'move {file} to {work_dir}')
            shutil.move(file, work_dir)
        # img2img.pyのrun_from_args_img2img()
        args = [
            '--filename-pattern', file_pattern,
            '--api-base', host,
            '--steps', str(img2img_steps),
            '--mask-dir', input_mask,
            '--alt-image-dir', input_append,
            '--output', os.path.join(output_dir, os.path.basename(folder) + folder_suffix),
            '--denoising_strength', str(img2img_denosing_stringth),
            '--n_iter', str(img2img_n_iter),
            '--batch_size', str(img2img_batch_size),
            work_dir,
        ]
        stdprint.verbose(args)
        result = img2img.run_from_args_img2img(args)
        result = True
        if result:
            stdprint.info(f'img2img.py finished {folder}')
            try:
                # *.png, *.jpg を ended_dir に移動
                files = glob.glob(os.path.join(work_dir, '*.png'))
                files.extend(glob.glob(os.path.join(work_dir, '*.jpg')))
                for file in files:
                    shutil.move(file, ended_dir)
            except Exception:
                pass
        else:
            stdprint.error(f'img2img.py failed {folder}')
            try:
                files = glob.glob(os.path.join(work_dir, '*.png'))
                files.extend(glob.glob(os.path.join(work_dir, '*.jpg')))
                for file in files:
                    shutil.move(file, folder)
            except Exception as e:
                stdprint.error(e)


def escape_split(str, split):
    import re
    regex = re.compile(r'".*?[^\\]*"')
    # 条件を満たす regex を抽出
    regex_list = regex.findall(str)
    # regex_list の 頭と後ろの" を削除
    regex_list = [regex[1:-1] for regex in regex_list]
    regex_replace = [regex.replace(' ', '\\S') for regex in regex_list]
    for regex, replace in zip(regex_list, regex_replace):
        str = str.replace(regex, replace)
    args = str.split(split)
    args = [arg.replace('\\S', ' ') for arg in args]
    return args


def txt2img(config):
    config = config['txt2img']
    output_dir = config['output']
    models = config['models']
    exception_list = config['prefix']['exception_list']
    prompts = config['prompts']
    prompt_base = config['prompt_base']
    abort_matrix = config['abort_matrix']
    coef_matrix = config['coef_matrix']
    prefix = config['prefix']
    folder_suffix = config['folder_suffix']
    overrides = config['overrides']
    if type(overrides) == str:
        overrides = escape_split(overrides, ' ')
    elif type(overrides) == list:
        pass
    else:
        overrides = None

    while True:
        model = models[random.randint(0, len(models) - 1)]
        model_name = model['model_name']
        vae = model['vae']
        mode = model['mode']
        logging.info(f'Set model {model_name} vae {vae} mode {mode}')
        stdprint.info(f'Set model {model_name} vae {vae} mode {mode}')

        if mode in abort_matrix:
            matrix = abort_matrix[mode]
        else:
            matrix = None
        if matrix is None:
            stdprint.info(f'SKIP {model_name} {vae} {mode}')
        else:
            break
    
    coef = 1.0
    if mode in coef_matrix:
        coef = coef_matrix[mode]

    for prompt in prompts:
        prompt_name = prompt['prompt_name']
        if prompt_name in exception_list:
            prompt_name = prompt_base + prefix['exception'] + prompt_name + prefix['suffix']
        else:
            prompt_name = prompt_base + prefix['default'] + prompt_name + prefix['suffix']

        folder = prompt['folder']
        number = float(prompt['number'])
        genre = prompt['genre']

        file_pattern = prompt['file_pattern']
        if file_pattern == '':
            file_pattern = '[num]-[seed]'

        if matrix == '*' or genre in matrix:
            number = int(number * coef)
            output = os.path.join(output_dir, folder + folder_suffix)
            logging.info(f'{model_name}, {prompt_name}, {output}, {genre}')
            args = [
                '--api-mode',
                '--api-base', HOST,
                '--api-set-sd-model', model_name,
                '--api-set-sd-vae', vae,
                '--api-filename-variable',
                '--api-filename-pattern', file_pattern,
                '--api-output-dir', output,
                '--max-number', str(number),
                prompt_name,
            ]
            if overrides is not None:
                args.extend(overrides)
            logging.info(args)
            stdprint.verbose(args)

            try:
                create_prompts.run_from_args(args)
            except Exception as e:
                logging.exception(type(e))
                stdprint.debug(type(e))


def ping(config):
    host = config['host'].split(':')[1].replace('//', '')
    stdprint.info(f'ping {host}')
    result = subprocess.run(['ping', host, '-n', '1', '-w', '1000'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    stdprint.debug(f'ping {host} {result.returncode}')
    return result.returncode


def wait_ping(config):
    res = 1
    while res != 0:
        res = ping(config)
        if res != 0:
            stdprint.info('ping failed')
            time.sleep(5)


def compare(*args):
    length = len(args)
    if length == 0:
        return True
    if length == 1:
        command = args[0]
    else:
        command, *args = args
    match command:
        case 'date':
            pass
        case 'time':
            pass
        case 'day':
            pass
        case 'hour':
            pass
        case 'minute':
            pass
        case 'second':
            pass
        case 'weekday':
            pass
        case 'month':
            pass
        case 'year':
            pass
        case _:
            pass
    return True


def loop(config_file):
    stdprint.info('loop mode')
    config = load_config(config_file)
    stdprint.info(config['loop'])
    if not config['loop']['mode']:
        stdprint.info('loop mode is not setting')
        return
    stdprint.debug(config)
    random.seed()
    loop_counter = 0
    logging.info('start')
    stdprint.info('start')
    loop = config['loop']
    logging.info(f'MAX LOOP {loop["loop_count"]}')
    while True:
        if loop['loop_count'] > 0 and loop_counter >= loop['loop_count']:
            stdprint.info('LOOP completed')
            exit()
        loop_counter += 1
        logging.info(f'LOOP #{loop_counter} / {loop["loop_count"]}')
        stdprint.info(f'LOOP #{loop_counter} / {loop["loop_count"]}')

        next = True

        for command in loop['commands']:
            stdprint.info(command)
            if not next:
                next = True
                continue
            commands = command.split(' ')
            command = commands[0].lower()
            args = commands[1:]
            try:
                match command:
                    case 'check':
                        check_time(config_file)
                    case 'compare':
                        if 'compares' in config:
                            compares = config['compares']
                        else:
                            compares = []
                        if args[0] in compares:
                            args = compares[int(args[0])]
                        else:
                            args = ''
                        next = compare(args)
                    case 'ping':
                        wait_ping(config)
                    case 'txt2img':
                        txt2img(config)
                    case 'img2img':
                        run_img2img(config)
                    case 'custom':
                        run_custom(args)
                    case 'clone':
                        clone = config['clone']
                        model_copy(clone)
                    case 'sleep':
                        time.sleep(int(args[0]))
                    case 'exit':
                        exit()
                    case _:
                        stdprint.info(f'unknown command {command}')
                        logging.info(f'unknown command {command}')

            except Exception as e:
                logging.exception(type(e))
                stdprint.info(type(e))
                continue
            config = load_config(config_file)
            if not config['loop']['mode']:
                break
            loop = config['loop']


def main(config_file=CONFIG):
    config = load_config(config_file)
    if config['loop']['mode']:
        loop(config_file)

    while True:
        try:
            logging.info('start')
            stdprint.info('start')
            check_time(config_file)
            logging.info('running...')
            stdprint.info('running...')
            res = 1
            while res != 0:
                res = ping(config)
                if res != 0:
                    stdprint.info('ping failed')
                    time.sleep(5)
            config = load_config(config_file)
        except Exception as e:
            logging.exception(type(e))
            stdprint.info(e)
            stdprint.info('Please check config.yaml')
            stdprint.info('Wait 60 seconds...')
            time.sleep(60)
            continue
        
        if config['clone']['clone']:
            clone = config['clone']
            print('clone')
            model_copy(clone)
        logging.info('txt2img')
        stdprint.info('txt2img')
        try:
            txt2img(config)
        except Exception as e:
            logging.exception(type(e))
        stdprint.info('img2img')
        logging.info('img2img')
        try:
            run_img2img(config)
        except Exception as e:
            logging.exception(type(e))
        try:
            stdprint.info('custom')
            if (config['custom']):
                run_custom()
        except Exception as e:
            logging.exception(type(e))

        time.sleep(1)


if __name__ == '__main__':
    import sys
    args = sys.argv
    if len(args) == 1:
        main()
    else:
        main(args[1])
