import os
import json
import modules.api as api
from modules.save import save_images


def txt2img(output_text, base_url='http://127.0.0.1:8760', output_dir='./outputs', opt={}):
    base_url = api.normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/txt2img')
    progress = base_url + '/sdapi/v1/progress?skip_current_image=true'
    print('Enter API mode, connect', url)
    dir = output_dir
    opt['dir'] = output_dir
    print('output dir', dir)
    os.makedirs(dir, exist_ok=True)
#    dt = datetime.datetime.now().strftime('%y%m%d')
    count = len(output_text)
    print(f'API loop count is {count} times')
    print('')
    flash = ''

    if opt.get('userpass'):
        userpass = opt.get('userpass')
    else:
        userpass = None

    for (n, item) in enumerate(output_text):
        api.share['line_count'] = 0
        print(flash, end='')
        print(f'\033[KBatch {n + 1} of {count}')
        # Why is an error happening? json=payload or json=item
        if 'variables' in item:
            opt['variables'] = item.pop('variables')
        payload = json.dumps(item)
        response = api.request_post_wrapper(
            url, data=payload, progress_url=progress, base_url=base_url, userpass=userpass)

        if response is None:
            print('http connection - happening error')
            exit(-1)
        if response.status_code != 200:
            print('\033[KError!', response.status_code, response.text)
            print('\033[2A', end='')
            continue

        r = response.json()
        prt_cnt = save_images(r, opt=opt)
        if 'line_count' in api.share:
            prt_cnt += api.share['line_count']
            api.share['line_count'] = 0
        flash = f'\033[{prt_cnt}A'
    print('')
