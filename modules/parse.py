import os
import base64
from PIL import Image
import modules.api as api


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


# parsing json from image's metadata
def create_img2json(imagefile, alt_image_dir=None, mask_image_dir=None, base_url=None):
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

    load_image = imagefile
    if alt_image_dir is not None:
        basename = os.path.basename(imagefile)
        alt_imagefile = os.path.join(alt_image_dir, basename)
        if os.path.isfile(alt_imagefile):
            print(f'\033[Kbase image use alternative {alt_imagefile}')
            if 'line_count' in api.share:
                api.share['line_count'] += 1
            load_image = alt_imagefile
    with open(load_image, 'rb') as f:
        init_image = base64.b64encode(f.read()).decode('ascii')
    json_raw = {}
    json_raw['init_images'] = ['data:image/png;base64,' + init_image]

    if mask_image_dir is not None:
        basename = os.path.basename(imagefile)
        mask_imagefile = os.path.join(mask_image_dir, basename)
        if os.path.isfile(mask_imagefile):
            with open(mask_imagefile, 'rb') as f:
                print(f'\033[KUse image mask {mask_imagefile}')
                if 'line_count' in api.share:
                    api.share['line_count'] += 1
                mask_image = base64.b64encode(f.read()).decode("ascii")
                json_raw['mask'] = 'data:image/png;base64,' + mask_image
                json_raw['mask_blur'] = 4
                json_raw['inpainting_fill'] = 0
                json_raw['inpaint_full_res'] = True
                json_raw['inpaint_full_res_padding'] = 0
                json_raw['inpainting_mask_invert'] = 0

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
