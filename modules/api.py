import asyncio
import base64
import json
import time

import httpx

import modules.logger as logger
import modules.share as share

# shared function for api

Logger = logger.getDefaultLogger()

share.set("timeout", 5)
share.set("max_timeout", 1000)


def set_timeout(timeout):
    share.set("timeout", timeout)


def set_max_timeout(timeout):
    share.set("max_timeout", timeout)


def init():
    if share.get("loop") is None:
        loop = asyncio.new_event_loop()
        share["loop"] = loop


def shutdown():
    pass


async def async_post(url, data, userpass=None):
    headers = {
        "Content-Type": "application/json",
    }
    if userpass:
        headers["Authorization"] = "Basic " + base64.b64encode(userpass.encode())

    async with httpx.AsyncClient() as client:
        try:
            return await client.post(
                url,
                data=data,
                headers=headers,
                timeout=(share.get("timeout"), share.get("max_timeout")),
            )
        except httpx.ReadTimeout:
            print("Read timeout")
            return None
        except httpx.TimeoutException:
            print("Connect Timeout")
            return None
        except BaseException as error:
            print("Exception: ", error)
            return None


isRunning = False


async def progress_writer(url, data, progress_url, userpass=None):
    headers = {
        "Content-Type": "application/json",
    }
    if userpass:
        headers["Authorization"] = "Basic " + base64.b64encode(userpass.encode())
    result = None

    async with httpx.AsyncClient() as client:

        async def write_progress(result, start_time):
            right = result["progress"] * 100
            state = result["state"]
            step = state["sampling_step"]
            steps = state["sampling_steps"]
            job = state["job"]
            elapsed_time = time.time() - start_time
            sharp = "#" * int(right / 2)
            space = " " * (50 - len(sharp))
            string = (
                f"{right:.1f}%  {job} step ({step:d}/{steps:d}) {elapsed_time:.2f} sec"
            )
            if right >= 0.0:
                string = f"\033[KCreate Image [{sharp}{space}] {string}"
            else:
                right = -right
                sharp = "#" * int(right / 2)
                space = " " * (50 - len(sharp))
                string = f"\033[KWeb UI interrupts using resource [{sharp}{space}] {string} {isRunning}"
            print(string, end="\r")
            return elapsed_time

        async def progress_get(progress_url, userpass=None):
            headers = {}
            if userpass:
                headers["Authorization"] = "Basic " + base64.b64encode(
                    userpass.encode()
                )
            retry = 0
            start_time = time.time()
            response = await client.get(progress_url, headers=headers)
            result = response.json()
            right = 1.0
            elapsed_time = await write_progress(result, start_time)
            await asyncio.sleep(0.5)  # initializing wait
            while right != 0.0 and elapsed_time <= share.get("max_timeout"):
                await asyncio.sleep(0.2)
                try:
                    response = await client.get(progress_url, timeout=1)
                    retry = 0
                    result = response.json()
                    right = result["progress"]
                    elapsed_time = await write_progress(result, start_time)
                    if not isRunning:
                        break
                except Exception:
                    retry += 1
                    if retry >= 20:
                        print("Progress is unknown")
                        return

        async def post_wrapper(url, data, headers, timeout):
            result = await client.post(url, data=data, headers=headers, timeout=timeout)
            global isRunning
            isRunning = False
            return result

        global isRunning
        isRunning = True
        tasks = [
            post_wrapper(url, data, headers, (share.get("timeout"), None)),
            progress_get(progress_url, userpass),
        ]
        result = await asyncio.gather(*tasks, return_exceptions=False)
    return result[0]


# force interrupt process


def progress_interrupt(url, userpass=None):
    try:
        headers = {}
        if userpass:
            headers = {"Authorization": "Basic " + base64.b64encode(userpass.encode())}
        return httpx.post(url, headers=headers)
    except httpx.ReadTimeout:
        print("Read timeout")
        return None
    except httpx.TimeoutException:
        print("Connect Timeout")
        return None
    except BaseException as error:
        print(str(error))
        return None


def request_post_wrapper(url, data, progress_url=None, base_url=None, userpass=None):
    try:
        if progress_url is not None:
            result = asyncio.run(progress_writer(url, data, progress_url, userpass))
        else:
            result = asyncio.run(async_post(url, data, userpass))
    except KeyboardInterrupt:
        if base_url:
            progress_interrupt(base_url + "/sdapi/v1/skip")  # chage api?
        Logger.error("enter Ctrl-c, Process stopping")
        raise KeyboardInterrupt
    except httpx.ConnectError:
        Logger.error("All connection attempts failed,Is the server down?")
        raise httpx.ConnectError
    except httpx.ConnectTimeout:
        Logger.error(
            "Connection Time out,Is the server down or server address mistake?"
        )
        raise httpx.ConnectTimeout
    return result


def normalize_base_url(base_url):
    if base_url[-1] == "/":
        base_url = base_url[:-1]
    return base_url


def get_api(
    base_url="http://localhost:7860", apiname=None, options=None, userpass=None
):
    headers = {
        "Content-Type": "application/json",
    }
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/" + apiname
    try:
        res = httpx.get(model_url, headers=headers, timeout=(share.get("timeout")))
        if res.status_code != 200:
            Logger.error(f"Failed to get {apiname} {res.status_code}")
            return None
        results = res.json()
    except Exception:
        Logger.error(f"Failed to get {apiname}")
        return None
    return results


def get_sd_model(base_url="http://127.0.0.1:7860", sd_model=None):
    headers = {
        "Content-Type": "application/json",
    }
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-models"
    try:
        Logger.verbose(f"Try get sd model from {model_url}")
        res = httpx.get(model_url, headers=headers, timeout=(share.get("timeout")))
        Logger.verbose(f"Get sd model from {json.dumps(res.json())}")
        for model in res.json():
            if (
                model["model_name"] == sd_model
                or model["hash"] == sd_model
                or model["title"] == sd_model
            ):
                return model
    except Exception:
        pass
    return None


def get_vae(base_url="http://127.0.0.1:7860", vae=None):
    headers = {
        "Content-Type": "application/json",
    }
    if vae == "Automatic":
        return "Automatic"
    if vae == "None":
        return "None"
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-vae"
    try:
        res = httpx.get(model_url, headers=headers, timeout=(share.get("timeout")))
        # automatic1111 1.6 <- no yet hash support but use metadata?
        for model in res.json():
            if (
                model["model_name"] == vae
                or model["hash"] == vae
                or model["title"] == vae
            ):
                return model
    except Exception:
        pass
    return None


def set_sd_model(sd_model, base_url="http://127.0.0.1:7860", sd_vae="Automatic"):
    Logger.info(f"Try change sd model to {sd_model}")
    headers = {
        "Content-Type": "application/json",
    }
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-models"

    url = base_url + "/sdapi/v1/options"
    try:
        res = httpx.get(model_url, headers=headers, timeout=(share.get("timeout")))
        load_model = None
        for model in res.json():
            import os

            title = os.path.basename(model["title"]).replace(".safetensors", "")

            if (
                model["model_name"] == sd_model
                or model["hash"] == sd_model
                or model["title"] == sd_model
                or title == sd_model  # for backward compatibility
            ):
                load_model = model["title"]
                break
        if load_model is None:
            Logger.info(f"{sd_model} model is not found")
            raise Exception(f"{sd_model} model is not found")
        sd_model = load_model
        Logger.info(f"checkpoint {sd_model} ,vae {sd_vae} models loading...")
        payload = {"sd_model_checkpoint": sd_model, "sd_vae": sd_vae}
        data = json.dumps(payload)
        res = httpx.post(
            url,
            data=data,
            headers=headers,
            timeout=(share.get("timeout"), share.get("max_timeout")),
        )
        # Version Return null only
        if res.status_code == 200:
            Logger.info("change success sd_model")
        else:
            Logger.info("change failed")

    except Exception:
        Logger.error("Change SD Model Error")
        raise


def refresh(
    base_url="http://localhost:7860", userpass=None, sd_model=True, vae=True, lora=True
):
    host = normalize_base_url(base_url)
    result = True
    if sd_model:
        Logger.info(f"refreshing checkpoint {host}")
        url = host + "/sdapi/v1/refresh-checkpoint"
        try:
            res = request_post_wrapper(
                url,
                data={},
                progress_url=None,
                base_url=host,
                userpass=userpass,
            )
            if res.status_code == 200:
                result = result and True
            else:
                result = result and False
        except Exception:
            Logger.error("refresh checkpoint failed")
            raise
    if vae:
        Logger.info(f"refreshing vae {host}")
        try:
            url = host + "/sdapi/v1/refresh-vae"
            res = request_post_wrapper(
                url,
                data={},
                progress_url=None,
                base_url=host,
                userpass=userpass,
            )
            if res.status_code == 200:
                result = result and True
            else:
                result = result and False
        except Exception:
            Logger.error("refresh vae failed")
            raise
    if lora:
        url = host + "/sdapi/v1/refresh-loras"
        Logger.info(f"refreshing lora {host}")
        try:
            res = request_post_wrapper(
                url,
                data={},
                progress_url=None,
                base_url=host,
                userpass=userpass,
            )
            if res.status_code == 200:
                result = result and True
            else:
                result = result and False
        except Exception:
            Logger.error("refresh lora failed")
            raise
    return result


def get_upscalers(base_url="http://localhost:7860"):
    return get_api(base_url, "upscalers")


def get_samplers(base_url="http://localhost:7860"):
    return get_api(base_url, "samplers")


def get_sd_models(base_url="http://127.0.0.1:7860"):
    return get_api(base_url, "sd-models")


def get_sd_vaes(base_url="http://127.0.0.1:7860"):
    return get_api(base_url, "sd-vae")


def get_loras(base_url="http://127.0.0.1:7860"):
    return get_api(base_url, "loras")
