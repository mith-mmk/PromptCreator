import sys
import os
import json
from PIL import Image

model_json = './outputs/hash.json'
models = json.load(open(model_json, 'r'))


# parsing json from metadata in an image
def create_parameters(parameters_text):
    para = parameters_text.split('\n')
    if len(para) == 1:
        para.append('')
    parameters = {}
    parameters['prompt'] = para[0]
    neg = 'Negative prompt: '
    if para[1][:len(neg)] == neg:
        parameters['negative_prompt'] = para[1].replace(neg, '')
        options = para[2].split(',')
    else:
        options = para[1].split(',')

    for option in options:
        keyvalue = option.split(': ')
        if len(keyvalue) == 2:
            key = keyvalue[0].strip().replace(' ', '_').lower()
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
                parameters['CLIP_stop_at_last_layers'] = int(keyvalue[1])
            elif key == 'ensd':
                parameters['eta_noise_seed_delta'] = int(keyvalue[1])
            elif key == 'model_hash':
                parameters['model_hash'] = keyvalue[1]
            else:
                parameters[key] = keyvalue[1]
        else:
            print('unknow', option)
    return parameters


def create_img2json(imagefile):
    schema = [
        'enable_hr',
        'denoising_strength',
        'firstphase_width',  # obusolete
        'firstphase_height',  # obusolete
        'hires_upscale',
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
        # img2img inpainting only
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
        parameters = {'width': image.width, 'height': image.height}

    # workaround for hires.fix spec change
    parameters['width'] = image.width
    parameters['height'] = image.height

    json_raw = {}

    override_settings = {}

    sampler_index = None
    # override settings only return sd_model_checkpoint and CLIP_stop_at_last_layers
    # Automatic1111 2023/07/25 verion do not support VAE tag
    for key, value in parameters.items():
        if key in schema:
            json_raw[key] = value
        elif key == 'sampler_index':
            sampler_index = value
        elif key == 'model_hash':
            override_settings['sd_model_checkpoint'] = value
        elif key == 'CLIP_stop_at_last_layers':
            override_settings[key] = value
    if ('sampler' not in json_raw) and sampler_index is not None:
        json_raw['sampler_index'] = sampler_index

    json_raw['override_settings'] = override_settings
    return json_raw


arg = sys.argv[1]
ext = os.path.splitext(arg)[1]
if ext != '.png':
    print('Error: File extension must be .png')
    exit(1)

params = create_img2json(arg)
model_hash = params['override_settings']['sd_model_checkpoint']
print(models[model_hash], model_hash)
