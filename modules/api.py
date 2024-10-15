import asyncio
import base64
import json
import shutil
import time

import httpx

import modules.logger as logger
import modules.share as share

# shared function for api

Logger = logger.getDefaultLogger()

# workaround
# httpx connection timeout time is influence response time for localhost Web UI
# set 5sec is duration 2sec or 6sec, hut set 0.1sec is duration 0.3 sec


class ProgressWriter:
    def __init__(self):
        pass

    def printProgress(self):
        pass


"""
class WeuUiAPI:
    @staticmethod
    def normalize_base_url(base_url: str) -> str:
        if base_url[-1] == "/":
            base_url = base_url[:-1]
        return base_url

    def __init__(self, hostname="http://localhost:7860", userpass=None):
        self.client = None
        self.timeout_c = 0.1
        self.timeout = 5
        self.max_timeout = 1000
        self.client = httpx.AsyncClient()
        self.sync_client = httpx.Client()
        self.hostname = self.normalize_base_url(hostname)
        self.progress_writer = ProgressWriter()
        self.userpass = userpass

    def getClient(self):
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_c, read=self.max_timeout)
            )
        return self.client

    def getSyncClient(self):
        if self.sync_client is None:
            self.sync_client = httpx.Client(
                timeout=httpx.Timeout(self.timeout_c, read=self.max_timeout)
            )
        return self.sync_client

    def setTimeout(self, timeout, connect_timeout=5):
        self.timeout = timeout
        self.timeout_c = connect_timeout

    async def get(self, endpoint):
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_c, read=self.max_timeout)
            )
        url = self.hostname + endpoint
        headers = {
            "Content-Type": "application/json",
        }
        if self.userpass:
            headers["Authorization"] = "Basic " + str(
                base64.b64encode(self.userpass.encode())
            )
        try:
            res = await self.client.get(url, headers=headers)
            if res.status_code == 200:
                return res
        except httpx.ReadTimeout:
            Logger.error(f"Read timeout {url}")
            raise httpx.ReadTimeout(f"Read timeout {url}")
        except httpx.TimeoutException:
            Logger.error(f"Failed to get {url} connect timeout")
            raise httpx.TimeoutException(f"Failed to get {url} connect timeout")
        except Exception as e:
            raise e
        error_result = {"error": res}
        return error_result

    async def postProgressed(self, endpoint, data):
        url = self.hostname + endpoint
        progress_writer = self.progress_writer
        progress_url = self.hostname + "/sdapi/v1/progress"
   
        async def progress_get():
            start_time = time.time()
            response = await self.getResponse(progress_url)
            result = response.json()
            right = 1.0
            elapsed_time = write_progress(result, start_time)
            await asyncio.sleep(0.5)  # initializing wait
            retry_start = time.time()
            while right != 0.0 and elapsed_time <= share.get("max_timeout"):
                await asyncio.sleep(0.2)
                try:
                    response = self.getClient().get(progress_url, timeout=1)
                    retry_start = time.time()
                    result = response.json()
                    right = result["progress"]
                    elapsed_time = await write_progress(result, start_time)
                    if not isRunning:
                        break
                except Exception:
                    retry_duration = time.time() - retry_start
                    if retry_duration >= share.get("timeout"):
                        print("Progress is unknown")
                        return

            async def post_wrapper(url, data, headers, timeout):
                result = await self.postResponse(url, data, headers, timeout)
                self.isRunning = False
                return result

        self.isRunning = True
        tasks = [
            post_wrapper(url, data, headers, share.get("max_timeout")),
            progress_get(),
        ]
        result = await asyncio.gather(*tasks, return_exceptions=False)
        return result[0]

    async def post(self, endpoint, data):
        if self.client is None:
            self.client = httpx.AsyncClient(
                timeout=httpx.Timeout(self.timeout_c, read=self.max_timeout)
            )
        url = self.hostname + endpoint
        try:
            res = await self.client.post(url, data=data)
            if res.status_code == 200:
                return res
        except httpx.ReadTimeout:
            Logger.error(f"Read timeout {url}")
            raise httpx.ReadTimeout(f"Read timeout {url}")
        except httpx.TimeoutException:
            Logger.error(f"Failed to get {url} connect timeout")
            raise httpx.TimeoutException(f"Failed to get {url} connect timeout")
        except Exception as e:
            raise e
        error_result = {"error": res}
        return error_result
"""


# connect timeout for local connection case, remote connection case is 5 sec
share.set("timeout_c", 0.1)
share.set("timeout", 5)
# read timeout / txt2img, img2img timeout
share.set("max_timeout", 1000)

client = None


def get_client():
    global client
    if client is None:
        # connect timeout is 0.1 sec and read timeout is 1000 sec
        client = httpx.Client(
            timeout=httpx.Timeout(share.get("timeout_c"), read=share.get("max_timeout"))
        )

    return client


def get_response(url, userpass=None):
    headers = {
        "Content-Type": "application/json",
    }
    if userpass:
        headers["Authorization"] = "Basic " + str(base64.b64encode(userpass.encode()))
    current_timeout = share.get("timeout_c")  # fast trick
    start_time = time.time()
    while True:
        try:
            timeout = httpx.Timeout(current_timeout, read=share.get("max_timeout"))
            duration = time.time() - start_time
            if duration > share.get("max_timeout"):
                Logger.error(f"Failed to get {url} connect timeout {duration} sec")
                raise httpx.ReadTimeout(
                    f"Failed to get {url} connect timeout {duration} sec"
                )
            res = get_client().get(url, headers=headers, timeout=timeout)

            if res.status_code == 200:
                return res
            if res.status_code == 404:
                return None
        except httpx.ReadTimeout:
            Logger.error(f"Read timeout {duration} sec")
            raise httpx.ReadTimeout(f"Read timeout {duration} sec")
        except httpx.TimeoutException:
            if duration > share.get("max_timeout"):
                raise httpx.TimeoutException(f"Failed to get {url} connect timeout")
            current_timeout = share.get("timeout")
        except Exception as e:
            raise e


def set_timeout(timeout):
    share.set("timeout", timeout)


def set_max_timeout(timeout):
    share.set("max_timeout", timeout)


def init():
    if share.get("loop") is None:
        loop = asyncio.new_event_loop()
        share.set("loop", loop)


def shutdown():
    if share.get("httpx_client"):
        share.get("httpx_client").close()
        share.set("httpx_client", None)
    pass


async def async_post(url, data, userpass=None):
    headers = {
        "Content-Type": "application/json",
    }
    if userpass:
        headers["Authorization"] = "Basic " + str(base64.b64encode(userpass.encode()))

    async with httpx.AsyncClient() as client:
        start_time = time.time()
        current_timeout = share.get("timeout_c")  # fast trick
        while True:
            try:
                return await client.post(
                    url,
                    data=data,
                    headers=headers,
                    timeout=httpx.Timeout(
                        current_timeout, read=share.get("max_timeout")
                    ),
                )
            except httpx.ReadTimeout:
                duration = time.time() - start_time
                Logger.error(f"Read timeout {duration} sec")
                return None
            except httpx.TimeoutException:
                duration = time.time() - start_time
                if duration > share.get("max_timeout"):
                    Logger.error(f"Failed to post {url} connect timeout {duration} sec")
                    return None
                current_timeout = share.get("timeout")
            except BaseException as error:
                Logger.error(str(error))
                return None


isRunning = False


async def progress_writer(url, data, progress_url, userpass=None):
    headers = {
        "Content-Type": "application/json",
    }
    if userpass:
        headers["Authorization"] = "Basic " + str(base64.b64encode(userpass.encode()))
    result = None

    async with httpx.AsyncClient() as client:

        async def write_progress(result, start_time):
            width = shutil.get_terminal_size().columns
            right = result["progress"] * 100
            state = result["state"]
            step = state["sampling_step"]
            steps = state["sampling_steps"]
            job = state["job"]
            elapsed_time = time.time() - start_time
            string = (
                f"{right:3.1f}%  {job} step ({step:d}/{steps:d}) {elapsed_time:.2f} sec"
            )
            if right >= 0.0:
                usefull_width = width - len(f"Create Image || {string}") - 10
                perblock = 100.0 / usefull_width
                if usefull_width > 10:
                    sharp = "█" * int(right / perblock + 0.5)
                    space = " " * (usefull_width - len(sharp))
                else:
                    sharp = ""
                    space = ""
                string = f"\033[KCreate Image |{sharp}{space}| {string}"
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
                headers["Authorization"] = "Basic " + str(
                    base64.b64encode(userpass.encode())
                )
            start_time = time.time()
            response = await client.get(progress_url, headers=headers)
            result = response.json()
            right = 1.0
            elapsed_time = await write_progress(result, start_time)
            await asyncio.sleep(0.5)  # initializing wait
            retry_start = time.time()
            while right != 0.0 and elapsed_time <= share.get("max_timeout"):
                await asyncio.sleep(0.2)
                try:
                    response = await client.get(progress_url, timeout=1)
                    retry_start = time.time()
                    result = response.json()
                    right = result["progress"]
                    await write_progress(result, start_time)
                    elapsed_time = time.time() - start_time
                    if not isRunning:
                        break
                except Exception:
                    retry_duration = time.time() - retry_start
                    if retry_duration >= share.get("timeout"):
                        print("Progress is unknown", end="\r")
                        retry_start = time.time()
                        elapsed_time = time.time() - start_time

        async def post_wrapper(url, data, headers, timeout):
            #            result = await client.post(url, data=data, headers=headers, timeout=timeout)
            result = await client.post(
                url, data=data, headers=headers, timeout=share.get("max_timeout")
            )
            global isRunning
            isRunning = False
            return result

        global isRunning
        isRunning = True
        tasks = [
            post_wrapper(url, data, headers, share.get("max_timeout")),
            progress_get(progress_url, userpass),
        ]
        result = await asyncio.gather(*tasks, return_exceptions=False)
    return result[0]


# force interrupt process


def progress_interrupt(url, userpass=None):
    try:
        headers = {}
        if userpass:
            headers = {
                "Authorization": "Basic " + str(base64.b64encode(userpass.encode()))
            }
        client = get_client()
        return client.post(url, headers=headers)
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
        raise httpx.ConnectError("All connection attempts failed,Is the server down?")
    except httpx.ConnectTimeout:
        Logger.error(
            "Connection Time out,Is the server down or server address mistake?"
        )
        raise httpx.ConnectTimeout(
            "Connection Time out,Is the server down or server address mistake?"
        )
    if result is None:
        Logger.error("Failed to post")
        raise Exception("Failed to post")
    return result


def normalize_base_url(base_url):
    if base_url[-1] == "/":
        base_url = base_url[:-1]
    return base_url


def get_api(base_url="http://localhost:7860", apiname="", options=None, userpass=None):
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/" + apiname
    try:
        res = get_response(model_url, userpass)
        if res.status_code != 200:
            Logger.error(f"Failed to get {apiname} {res.status_code}")
            return None
        results = res.json()
    except Exception:
        Logger.error(f"Failed to get {apiname}")
        return None
    return results


def get_sd_model(base_url="http://127.0.0.1:7860", sd_model=None, userpass=None):
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-models"
    try:
        Logger.verbose(f"Try get sd model from {model_url}")
        res = get_response(model_url, userpass)
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


def get_vae(base_url="http://127.0.0.1:7860", vae=None, userpass=None):
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-vae"
    try:
        Logger.verbose(f"Try get vae from {model_url}")
        res = get_response(model_url, userpass=userpass)
        # automatic1111 1.6 <- no yet hash support but use metadata?
        for model in res.json():
            if (
                model["model_name"] == vae
                or model["hash"] == vae
                or model["title"] == vae
            ):
                return model
    except Exception:
        Logger.error("Failed to get vae")
        pass
    return None


def get_modules(base_url="http://127.0.0.1:7860", modules=[], userpass=None):
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-modules"
    try:
        res = get_response(model_url, userpass)
        if res.status_code != 200:
            Logger.error(f"Failed to get modules {res.status_code}")
            return None
        results = []
        for module in modules:
            if module in res.json():
                results.append(module)
    except Exception:
        Logger.error(f"Failed to get modules")
        return None
    return results


def set_sd_model(
    sd_model, base_url="http://127.0.0.1:7860", sd_vae="Automatic", userpass=None
):
    Logger.info(f"Try change sd model to {sd_model}")
    headers = {
        "Content-Type": "application/json",
    }
    if userpass:
        headers["Authorization"] = "Basic " + str(base64.b64encode(userpass.encode()))
    base_url = normalize_base_url(base_url)
    model_url = base_url + "/sdapi/v1/sd-models"
    options_url = base_url + "/sdapi/v1/options"

    try:
        sd_opts = get_response(options_url, userpass).json()
        sd_models = get_response(model_url, userpass).json()

        load_model = None

        for model in sd_models:
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
        Logger.verbose("check current server")
        model = get_vae(base_url, sd_vae, userpass=userpass)
        Logger.verbose(f"Current vae is {model}")
        forge = False
        if model is None:
            forge = True
            Logger.info("This sever is forge WebUi, use forge_additional_modules")
            # change forge_additional_modules from sd_vae
            if sd_vae == "None" or sd_vae == "Automatic" or sd_vae is None:
                sd_vae = []
            if isinstance(sd_vae, str):
                # ex) flux.1 "ae.vae, t5xxl_fp8_e4m3fn.safetensors, clip_l.safetensors" -> ["ae.vae", "t5xxl_fp8_e4m3fn", "clip_l"]
                sd_vae = sd_vae.split(",")
                sd_vae = [x.strip() for x in sd_vae]
            if not isinstance(sd_vae, list):
                # sdxl, stable diffusion 1,2
                sd_vae = [sd_vae]

        else:
            Logger.info(f"This server is automatic1111 WebUI")

        if load_model is None:
            Logger.info(f"{sd_model} model is not found")
            raise Exception(f"{sd_model} model is not found")
        sd_model = load_model
        if load_model == sd_opts.get("sd_model_checkpoint"):
            if forge == False and sd_vae == sd_opts.get("sd_vae"):
                Logger.info(f"Checkpoint {sd_model} and {sd_vae} are already loaded")
                return
            else:
                Logger.info(f"Checkpoint {sd_model} is already loaded")
                payload = {"sd_vae": sd_vae}
        elif sd_vae == sd_opts.get("sd_vae"):
            payload = {"sd_model_checkpoint": sd_model}
        else:
            if forge:
                payload = {
                    "sd_model_checkpoint": sd_model,
                    "forge_additional_modules": sd_vae,
                }
            else:
                payload = {"sd_model_checkpoint": sd_model, "sd_vae": sd_vae}
        Logger.info(f"Checkpoint {sd_model} and {sd_vae} are loading...")
        data = json.dumps(payload)
        res = request_post_wrapper(options_url, data, None, base_url, userpass)
        # Version Return null only
        if res.status_code == 200:
            Logger.info("change success sd_model")
        else:
            Logger.info("change failed")

    except Exception as e:
        Logger.error(f"Change SD Model Error {e}")
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


def get_upscalers(base_url="http://localhost:7860", userpass=None):
    return get_api(base_url, "upscalers", userpass=userpass)


def get_samplers(base_url="http://localhost:7860", userpass=None):
    return get_api(base_url, "samplers", userpass=userpass)


def get_sd_models(base_url="http://127.0.0.1:7860", userpass=None):
    return get_api(base_url, "sd-models", userpass=userpass)


def get_sd_vaes(base_url="http://127.0.0.1:7860", userpass=None):
    return get_api(base_url, "sd-vae", userpass=userpass)


def get_loras(base_url="http://127.0.0.1:7860", userpass=None):
    return get_api(base_url, "loras", userpass=userpass)
