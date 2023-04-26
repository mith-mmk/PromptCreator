import asyncio
import time
import base64
import httpx
import sys
import json

share = {
    'timeout': 5,
    'max_timeout': 1000
}


def init():
    loop = asyncio.new_event_loop()
    share['loop'] = loop


def shutdown():
    pass


async def async_post(url, data, userpass=None):
    headers = {
        'Content-Type': 'application/json',
    }
    if userpass:
        headers['Authorization'] = 'Basic ' + \
            base64.b64encode(userpass.encode())

    async with httpx.AsyncClient() as client:
        try:
            return await client.post(url, data=data, headers=headers, timeout=(share.get('timeout'), share.get('max_timeout')))
        except httpx.ReadTimeout:
            print('Read timeout', file=sys.stderr)
            return None
        except httpx.TimeoutException:
            print('Connect Timeout', file=sys.stderr)
            return None
        except BaseException as error:
            print('Exception: ', error, file=sys.stderr)
            return None


async def progress_writer(url, data, progress_url, userpass=None):
    headers = {
        'Content-Type': 'application/json',
    }
    if userpass:
        headers['Authorization'] = 'Basic ' + \
            base64.b64encode(userpass.encode())
    result = None
    async with httpx.AsyncClient() as client:
        async def write_progress(result, start_time):
            right = result['progress'] * 100
            state = result['state']
            step = state['sampling_step']
            steps = state['sampling_steps']
            job = state['job']
            elapsed_time = time.time() - start_time
            sharp = '#' * int(right / 2)
            space = ' ' * (50 - len(sharp))
            string = f'{right:.1f}%  {job} step ({step:d}/{steps:d}) {elapsed_time:.2f} sec'
            if right >= 0.0:
                string = f'\033[KCreate Image [{sharp}{space}] {string}'
            else:
                right = - right
                sharp = '#' * int(right / 2)
                space = ' ' * (50 - len(sharp))
                string = f'\033[KWeb UI interrupts using resource [{sharp}{space}] {string}'
            print(string, end='\r')
            return elapsed_time

        async def progress_get(progress_url, userpass=None):
            headers = {}
            if userpass:
                headers['Authorization'] = 'Basic ' + \
                    base64.b64encode(userpass.encode())
            async with httpx.AsyncClient() as client:
                retry = 0
                start_time = time.time()
                response = await client.get(progress_url, headers=headers)
                result = response.json()
                right = 1.0

                elapsed_time = await write_progress(result, start_time)
                await asyncio.sleep(0.5)  # initializing wait
                while right != 0.0 and elapsed_time <= share.get('max_timeout'):
                    await asyncio.sleep(0.2)
                    try:
                        response = await client.get(progress_url)
                        retry = 0
                        result = response.json()
                        right = result['progress']
                        elapsed_time = await write_progress(result, start_time)
                    except Exception:
                        retry += 1
                        if retry >= 10:
                            print('Progress is unknown', file=sys.stderr)
                            return

        tasks = [
            client.post(url, data=data, headers=headers, timeout=(
                share.get('timeout'), share.get('max_timeout'))),
            progress_get(progress_url, userpass)
        ]
        result = await asyncio.gather(*tasks, return_exceptions=False)
    return result[0]

# force interrupt process


def progress_interrupt(url, userpass=None):
    try:
        headers = {}
        if userpass:
            headers = {'Authorization': 'Basic ' +
                       base64.b64encode(userpass.encode())}
        return httpx.post(url, headers=headers)
    except httpx.ReadTimeout:
        print('Read timeout', file=sys.stderr)
        return None
    except httpx.TimeoutException:
        print('Connect Timeout', file=sys.stderr)
        return None
    except BaseException as error:
        print(str(error), file=sys.stderr)
        return None


def request_post_wrapper(url, data, progress_url=None, base_url=None, userpass=None):
    try:
        if progress_url is not None:
            result = asyncio.run(progress_writer(
                url, data, progress_url, userpass))
        else:
            result = asyncio.run(async_post(url, data, userpass))
    except KeyboardInterrupt:
        if base_url:
            progress_interrupt(base_url + '/sdapi/v1/skip')  # chage api?
        print('enter Ctrl-c, Process stopping', file=sys.stderr)
        exit(2)
    except httpx.ConnectError:
        print('All connection attempts failed,Is the server down?', file=sys.stderr)
        exit(2)
    except httpx.ConnectTimeout:
        print('Connection Time out,Is the server down or server address mistake?', file=sys.stderr)
        exit(2)
    return result


def normalize_base_url(base_url):
    if base_url[-1] == '/':
        base_url = base_url[:-1]
    return base_url


def get_sd_model(base_url='http://127.0.0.1:7860', sd_model=None):
    headers = {
        'Content-Type': 'application/json',
    }
    base_url = normalize_base_url(base_url)
    model_url = (base_url + '/sdapi/v1/sd-models')
    try:
        res = httpx.get(model_url, headers=headers,
                        timeout=(share.get('timeout')))
        for model in res.json():
            if model['model_name'] == sd_model or model['hash'] == sd_model or model['title'] == sd_model:
                return model
    except Exception:
        pass
    return None


def set_sd_model(sd_model, base_url='http://127.0.0.1:7860', sd_vae='Automatic'):
    print(f'Try change sd model to {sd_model}')
    headers = {
        'Content-Type': 'application/json',
    }
    base_url = normalize_base_url(base_url)
    model_url = (base_url + '/sdapi/v1/sd-models')

    url = (base_url + '/sdapi/v1/options')
    try:
        res = httpx.get(model_url, headers=headers,
                        timeout=(share.get('timeout')))
        load_model = None
        for model in res.json():
            if model['model_name'] == sd_model or model['hash'] == sd_model or model['title'] == sd_model:
                load_model = model['title']
                break
        if load_model is None:
            print(f'{sd_model} model is not found')
            exit()
        sd_model = load_model
        print(f'{sd_model} model loading...')
        payload = {"sd_model_checkpoint": sd_model, "sd_vae": sd_vae}
        data = json.dumps(payload)
        res = httpx.post(url, data=data, headers=headers, timeout=(
            share.get('timeout'), share.get('max_timeout')))
        # Version Return null only
        if res.status_code == 200:
            print('change success sd_model')
        else:
            print('change failed')

    except Exception:
        print('Change SD Model Error')
        exit()
