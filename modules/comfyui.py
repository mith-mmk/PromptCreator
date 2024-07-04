#
import asyncio
import datetime
import io
import json
import os
import random
import re
import urllib.parse
import urllib.request
import uuid

import httpx

# import httpx_ws
import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)
from PIL import Image

try:
    from modules.logger import getDefaultLogger

    logger = getDefaultLogger()
except:
    logger = None


def printInfo(*args, **kwargs):
    if logger is not None:
        logger.info(*args, **kwargs)
    else:
        print(*args, **kwargs)


def printError(*args, **kwargs):
    if logger is not None:
        logger.error(*args, **kwargs)
    else:
        print(*args, **kwargs)


def printWarning(*args, **kwargs):
    if logger is not None:
        logger.warning(*args, **kwargs)
    else:
        print(*args, **kwargs)


def printDebug(*args, **kwargs):
    if logger is not None:
        logger.debug(*args, **kwargs)


class ComfyUIWorkflow:
    def __init__(self, options={}):
        self.options = options
        self.checkpoint = None
        self.vae = None

    # todo:
    # ✓ clip layer
    # token BREAK over 75 tokens
    # hiresfix
    # img2img
    # infotext warpper for prompt
    # save_images wrapper
    # img2video and other

    def setModel(self, model):
        self.checkpoint = model

    def setVAE(self, vae):
        self.vae = vae

    def creatCLIPSetLastLayer(self, stop_at_clip_layer, clip):
        if stop_at_clip_layer > 0:
            stop_at_clip_layer = -stop_at_clip_layer
        elif stop_at_clip_layer == 0:
            stop_at_clip_layer = -1

        flow = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {
                "stop_at_clip_layer": stop_at_clip_layer,
                "clip": clip,
            },
        }
        return flow

    def createLoadCheckpoint(self, checkpoint):
        flow = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        }
        return flow

    def createLoadVAE(self, vae):
        flow = {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": vae,
            },
        }
        return flow

    def createKSampler(
        self, latent_from, model_from, positive_from, negative_from, options
    ):
        flow = {
            "class_type": "KSampler",
            "inputs": {
                "cfg": options.get("cfg", 8),
                "denoise": options.get("denoise", 1),
                "latent_image": [latent_from, 0],
                "model": [model_from, 0],
                "positive": [positive_from, 0],
                "negative": [negative_from, 0],
                "sampler_name": options.get("sampler_name", "euler"),
                "scheduler": options.get("scheduler", "normal"),
                "seed": options.get("seed", -1),
                "steps": options.get("steps", 20),
            },
        }
        return flow

    def createEncodeVAE(self, fromSamples, fromVae, otherVae=False):
        if otherVae:
            index = 0
        else:
            index = 2  # model include vae
        flow = {
            "class_type": "VAEDecode",
            "inputs": {"samples": [fromSamples, 0], "vae": [fromVae, index]},
        }
        return flow

    def createSaveWebSocketImage(self, image_form, options):
        flow = {
            "class_type": "SaveImageWebsocket",
            "inputs": {
                "images": [image_form, 0],
            },
        }
        return flow

    def createSaveImage(self, image_form, options):
        flow = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": options.get(
                    "prefix", options.get("filename", "Comfy")
                ),
                # "filename_suffix": options.get("suffix", f"-{options.get('seed', 0)}"),
                "images": [image_form, 0],
            },
        }
        return flow

    def createEmptyLatentImage(self, options):
        flow = {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": options.get("batch_size", 1),
                "height": options.get("height", 512),
                "width": options.get("width", 512),
            },
        }
        return flow

    def createConditioningConcat(self, from_prompt, to_prompt):
        flow = {
            "class_type": "ConditioningConcat",
            "inputs": {
                "conditioning_to": [to_prompt, 0],
                "conditioning_from": [from_prompt, 0],
            },
        }
        return flow

    def createBatchTextEncode(self, wf, prompt, wf_num, clip, type):
        prompts = prompt.split("BREAK")
        from_prompt = None
        if type == "sdxl":
            wf[str(wf_num)] = self.createCLIPTextEncodeSDXL(prompts[0], clip)
        else:
            wf[str(wf_num)] = self.createCLIPTextEncode(prompts[0], clip)
        from_prompt = str(wf_num)
        prompts = prompts[1:]
        for prompt in prompts:
            wf_num += 1
            if type == "sdxl":
                wf[str(wf_num)] = self.createCLIPTextEncodeSDXL(prompt, clip)
            else:
                wf[str(wf_num)] = self.createCLIPTextEncode(prompt, clip)
            to_prompt = str(wf_num)
            wf_num += 1
            wf[str(wf_num)] = self.createConditioningConcat(from_prompt, to_prompt)
            from_prompt = str(wf_num)
        return wf, wf_num

    def createCLIPTextEncode(self, prompt, clip):
        flow = {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": clip, "text": prompt},
        }
        return flow

    def createCLIPTextEncodeSDXL(self, text, clip):
        flow = {
            "class_type": "CLIPTextEncodeSDXL",
            "inputs": {
                "clip": clip,
                "text_g": text,
                "text_l": text,
                "width": 4096,
                "height": 4096,
                "crop_w": 0,
                "crop_h": 0,
                "target_width": 4096,
                "target_height": 4096,
            },
        }
        return flow

    # local でしか使えないので、使わない
    def searchLora(self, loraname, options, subfolder=""):
        import os

        lora_dir = options.get("lora_dir")
        if lora_dir is None:
            return loraname + ".safetensors"
        lora_dir = os.path.join(lora_dir, subfolder)
        if os.path.exists(os.path.join(lora_dir, loraname + ".safetensors")):
            return os.path.join(subfolder, loraname + ".safetensors")
        lora_dirs = os.scandir(lora_dir)
        for dir in lora_dirs:
            if dir.is_dir():
                next_subfolder = os.path.join(subfolder, dir.name)
                result = self.searchLora(loraname, options, next_subfolder)
                if result is not None:
                    return result
        return loraname + ".safetensors"

    def createLoraLoader(self, fromModel, clip, loraname, weight, options={}):
        if not loraname.endswith(".safetensors"):
            loraname = loraname + ".safetensors"
        flow = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": loraname,
                "strength_model": weight,
                "strength_clip": weight,
                "model": [fromModel, 0],
                "clip": clip,
            },
        }
        return flow

    def createWorkflowSDXL(self, prompt, options={}):
        options["type"] = "sdxl"
        return self.createWorkflow(prompt, options)

    def createWorkflowSD15(self, prompt, negative_prompt, options={}):
        options["type"] = "sd15"
        return self.createWorkflow(prompt, negative_prompt, options)

    def createWorkflow(self, prompt, negative_prompt, options={}):
        info = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        }
        other_vae = False
        lora_matcher = re.compile(r"\<lora\:(.+?)\:([0-9\.]+)\>")
        postive_loras = lora_matcher.findall(prompt)
        prompt = lora_matcher.sub("", prompt)
        negative_loras = lora_matcher.findall(negative_prompt)
        negative_prompt = lora_matcher.sub("", negative_prompt)

        if len(postive_loras) == 0 and len(negative_loras) == 0:
            info["loras"] = []
        info["loras"] = postive_loras.copy().extend(negative_loras)

        checkpoint = options.get("checkpoint", self.checkpoint or "None")
        if checkpoint == "None":
            raise ValueError("Checkpoint not set")
        vae = options.get("vae", self.vae or "None")

        seed = options.get("seed", -1)
        if seed == -1:
            seed = random.randint(0, 2**31 - 1)
        info["seed"] = seed

        workflow = {}
        wf_num = 3
        base_width = 1024 if options.get("type") == "sdxl" else 512
        width = options.get("width", base_width)
        base_height = 1024 if options.get("type") == "sdxl" else 512
        height = options.get("height", base_height)
        batch_size = options.get("batch_size", 1)

        workflow[str(wf_num)] = self.createEmptyLatentImage(
            {
                "batch_size": batch_size,
                "height": height,
                "width": width,
            }
        )
        latent_from = str(wf_num)
        wf_num += 1
        info["width"] = width
        info["height"] = height
        info["batch_size"] = batch_size

        workflow[str(wf_num)] = self.createLoadCheckpoint(checkpoint)
        model_from = str(wf_num)
        positive_clip_from = [model_from, 1]  # 1 is clip index
        negative_clip_from = [model_from, 1]
        vae_from = model_from
        wf_num += 1
        info["sd_model_name"] = checkpoint

        if options.get("stop_at_clip_layer") is not None:
            workflow[str(wf_num)] = self.creatCLIPSetLastLayer(
                options.get("stop_at_clip_layer"), positive_clip_from
            )
            positive_clip_from = [str(wf_num), 0]
            negative_clip_from = [str(wf_num), 0]
            wf_num += 1
            info["clip_skip"] = abs(options.get("stop_at_clip_layer", 1))

        if vae != "None":
            workflow[str(wf_num)] = self.createLoadVAE(vae)
            vae_from = str(wf_num)
            wf_num += 1
            other_vae = True
        info["sd_vae_name"] = vae
        if vae == "None":
            info["sd_vae_name"] = None

        for lora, weight in postive_loras:
            wf = self.createLoraLoader(
                model_from, positive_clip_from, lora, float(weight), options
            )
            if wf is not None:
                workflow[str(wf_num)] = wf
                model_from = str(wf_num)
                wf_num += 1
                positive_clip_from = [model_from, 1]

        for lora, weight in negative_loras:
            wf = self.createLoraLoader(
                negative_clip_from, negative_prompt, lora, float(weight), options
            )
            if wf is not None:
                workflow[str(wf_num)] = wf
                model_from = str(wf_num)
                wf_num += 1
                negative_clip_from = [model_from, 1]

        workflow, wf_num = self.createBatchTextEncode(
            workflow, prompt, wf_num, positive_clip_from, options.get("type")
        )
        positive_from = str(wf_num)
        wf_num += 1
        workflow, wf_num = self.createBatchTextEncode(
            workflow, negative_prompt, wf_num, negative_clip_from, options.get("type")
        )
        negative_from = str(wf_num)
        wf_num += 1

        workflow[str(wf_num)] = self.createKSampler(
            latent_from,
            model_from,
            positive_from,
            negative_from,
            {
                "cfg": options.get("cfg_scale", 7),
                "denoise": options.get("nomal_denoising_strength", 1),
                "sampler_name": options.get("sampler_name", "dpmpp_2m_sde"),
                "scheduler": options.get("scheduler", "karras"),
                "seed": seed,
                "steps": options.get("steps", 20),
            },
        )
        sampler_from = str(wf_num)
        wf_num += 1
        info["cfg_scale"] = options.get("cfg_scale", 7)
        # info["denoising_strength"] = options.get("nomal_denoising_strength")
        info["sampler_name"] = options.get(
            "sampler_name", "dpmpp_2m_sde"
        )  # sampler mapper
        info["scheduler"] = options.get("scheduler", "karras")
        info["steps"] = options.get("steps", 20)

        workflow[str(wf_num)] = self.createEncodeVAE(sampler_from, vae_from, other_vae)
        encode_from = str(wf_num)
        wf_num += 1
        if "ui" in options.get("save_image", []):
            workflow[str(wf_num)] = self.createSaveImage(encode_from, options)
            wf_num += 1
        if "websocket" in options.get("save_image", ["websocket"]):
            workflow["save_image_websocket_node"] = self.createSaveWebSocketImage(
                encode_from, options
            )
        return workflow, info


class ComufyClient:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient()
        self.hostname = "http://127.0.0.1:8188"
        self.server_address = self.hostname.replace("http://", "").replace(
            "https://", ""
        )

    def setHostname(self, hostname):
        self.hostname = hostname
        self.server_address = hostname.replace("http://", "").replace("https://", "")

    async def queuePrompt(self, prompt, client_id):
        p = {"prompt": prompt, "client_id": client_id}
        req = await self.client.post(f"{self.hostname}/prompt", json=p)
        if req.status_code != 200:
            printError("Failed to queue prompt")
            printDebug(json.dumps(prompt, indent=4))
            printDebug(json.dumps(req.json(), indent=4))
            raise Exception(req.text)
        return req.json()

    async def getImage(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}

        res = await self.client.post(f"{self.hostname}/get_image", json=data)
        if res.status_code != 200:
            printError(
                f"Failed to get image {filename} in {subfolder} of {folder_type}"
            )
            printDebug(json.dumps(res.json(), indent=4))
            raise Exception(res.text)
        return res.content

    async def getHistory(self, prompt_id):
        res = await self.client.get(f"{self.hostname}/history/{prompt_id}")
        if res.status_code != 200:
            printError(f"Failed to get history for {prompt_id}")
            printDebug(json.dumps(res.json(), indent=4))
            raise Exception(res.text)
        return res.json()

    async def getImageFromUI(self, prompt, client_id, options={}):
        res = await self.queuePrompt(prompt, client_id)
        prompt_id = res["prompt_id"]
        images = []
        urls = await self.checkQueue([prompt_id], options)
        for url in urls:
            if "save" in options.get("save_image"):
                res = await self.client.get(url)
                if res.status_code == 200:
                    image_data = res.content
                    data = {
                        "url": url,
                        "image": image_data,
                    }
                    images.append(data)
            else:
                data = {
                    "url": url,
                    "image": None,
                }
                images.append(data)
        return images

    async def getImages(self, ws, prompt, client_id, options={}):
        try:
            start_time = datetime.datetime.now()
            res = await self.queuePrompt(prompt, client_id)
            prompt_id = res["prompt_id"]
            output_images = {}
            current_node = ""
            while True:
                out = ws.recv()
                if isinstance(out, str):
                    try:

                        message = json.loads(out)
                        if message["type"] == "executing":
                            data = message["data"]
                            if data["prompt_id"] == prompt_id:
                                if data["node"] is None:
                                    # clear row
                                    print("\033[K", end="\r")
                                    duration = datetime.datetime.now() - start_time
                                    duration = duration.total_seconds()
                                    print(f"Execution is done {duration:.2f} sec")
                                    break  # Execution is done
                                else:
                                    current_node = data["node"]
                        elif message.get("type") == "progress":
                            data = message.get("data", {})
                            if data.get("prompt_id") == prompt_id:
                                max = data.get("max", 1)
                                value = data.get("value", 0)
                                percentage = (float(value) / float(max)) * 100.0
                                duration = datetime.datetime.now() - start_time
                                duration = duration.total_seconds()
                                print(
                                    f"progress {percentage:.1f} {value}/{max} {duration:2f} sec",
                                    end="\r",
                                )
                    except Exception as e:
                        printError("Failed to parse message", e)
                        printError(out[:100])
                else:
                    if current_node == "save_image_websocket_node":
                        images_output = output_images.get(current_node, [])
                        images_output.append(out[8:])
                        output_images[current_node] = images_output
            return output_images

        except Exception as e:
            return None

    async def checkQueue(self, prompt_ids, options={}):
        urls = []
        for prompt_id in prompt_ids:
            while True:
                history = await self.getHistory(prompt_id)
                try:
                    history = history[prompt_id]
                except KeyError:
                    await asyncio.sleep(0.1)
                    continue
                if history["status"]["completed"]:
                    break
            outputs = history["outputs"]
            for id in outputs:
                output = outputs[id]
                if "images" in output:
                    for image in output["images"]:
                        filename = image["filename"]
                        subfolder = image["subfolder"]
                        folder_type = image["type"]
                        payload = {
                            "filename": filename,
                            "subfolder": subfolder,
                            "type": folder_type,
                        }
                        urlencode = urllib.parse.urlencode(payload)
                        url = f"{self.hostname}/view?{urlencode}"
                        urls.append(url)
        return urls

    # use modules.save.save_image method
    async def imageWrapper(self, images, prompt_text, options, info={}):
        import copy

        options = copy.deepcopy(options)
        options["verbose"] = prompt_text.get("verbose", {})
        keys = {
            "Steps": "steps",
            "Sampler": "sampler_name",
            "CFG scale": "cfg_scale",
            "Seed": "seed",
            "Size": "{width}x{height}",
            "Model": "sd_model_name",
            "VAE": "sd_vae_name",
            "Clip Skip": "clip_skip",
            "Denoising Strength": "denoising_strength",
        }
        infotexts = f"{info['prompt']}\n"
        if "negative_prompt" in info:
            infotexts += f"Negative prompt: {info['negative_prompt']}\n"
        lines = []
        matching = re.compile(r"{(.+?)}")
        for key in keys:
            mapping_key = keys[key]
            if mapping_key in info:
                value = info[mapping_key]
                if matching.search(key):
                    groups = matching.findall(key)
                    for group in groups:
                        if group in info:
                            key = key.replace(f"{{{group}}}", str(info[group]))
                if value is not None:
                    lines.append(f"{key}: {value}")
        line = ", ".join(lines)
        infotexts += line
        r = {
            "info": {
                "infotexts": [infotexts],
            },
            "parameters": {},
            "images": images,
        }
        return r, options

    async def saveImage(self, image_data, prompt, options={}, info={}, prompt_text={}):

        # print(prompt_text.get("verbose", {}).get("values", {}).get("title", "None"))
        try:
            import modules.save as save

            r, options = await self.imageWrapper(
                [image_data], prompt_text, options, info
            )

            await save.async_save_images(r, options)
        except Exception as e:
            printError("Failed to save image", e)
            printError("retrying to other method save image")
            image = Image.open(io.BytesIO(image_data))
            dirctory = options.get("dir", "outputs")
            os.makedirs(dirctory, exist_ok=True)
            now = datetime.datetime.now()
            imagename = now.strftime("%H%M%S")
            image.save(f"{dirctory}/img{imagename}.png")
            printInfo(f"Image saved as {dirctory}/img{imagename}.png")

    async def arun(self, prompts, options={}):
        client = ComufyClient()

        if "websocket" in options.get("save_image", []):
            ws = websocket.WebSocket()
            for i, _prompt in enumerate(prompts):
                prompt = _prompt.get("workflow")
                info = _prompt.get("info", {})
                prompt_text = _prompt["prompt_text"]

                printInfo(f"process queuing {i+1}/{len(prompts)}")
                client_id = str(uuid.uuid4())
                ws.connect(f"ws://{self.server_address}/ws?clientId={client_id}")
                images = await client.getImages(ws, prompt, client_id, _prompt)
                if images is None:
                    printError("Failed to get images")
                    continue

                for node_id in images:
                    for image_data in images[node_id]:
                        await self.saveImage(
                            image_data, prompt, options, info, prompt_text
                        )
                ws.close()
        elif "ui" in options.get("save_image", ["ui"]):
            for prompt in prompts:
                client_id = str(uuid.uuid4())
                try:
                    images = await client.getImageFromUI(prompt, client_id, options)
                    for image_data in images:
                        if image_data["image"] is not None:
                            await self.saveImage(image_data["image"], prompt, options)
                        else:
                            printInfo(f"image show url: {image_data['url']}")
                except Exception as e:
                    printError("Connection error", e)

    def run(self, prompt, options={}):
        import asyncio

        asyncio.run(self.arun(prompt, options))

    def convertSamplerNameWebUi2Comfy(self, name):
        name = name.lower()
        convert = {
            "dpm++ 2m": {"sampler": "dpmpp_2m", "scheduler": "karras"},
            "dpm++ sde": {"sampler": "dpmpp_sde", "scheduler": "karras"},
            "dpm++ 2M SDE": {"sampler": "dpmpp_2m_sde", "scheduler": "karras"},
            "dpm++ 2M SDE Heun": {
                "sampler": "dpmpp_2m_sde_heun",
                "scheduler": "karras",
            },
            "dpm++ 2S a": {"sampler": "dpmpp_2s_a", "scheduler": "karras"},
            "dpm++ 3M SDE": {"sampler": "dpmpp_3m_sde", "scheduler": "karras"},
            "euler a": {"sampler": "euler_ancestral", "scheduler": "normal"},
            "euler": {"sampler": "euler", "scheduler": "normal"},
            "lms": {"sampler": "lms", "scheduler": "normal"},
            "heun": {"sampler": "heun", "scheduler": "normal"},
            "dpm2": {"sampler": "dpm_2", "scheduler": "normal"},
            "dpm2 a": {"sampler": "dpm_2_ancestral", "scheduler": "normal"},
            "dpm fast": {"sampler": "dpm_fast", "scheduler": "normal"},
            "dpm adaptive": {"sampler": "dpm_adaptive", "scheduler": "normal"},
            "restart": {"sampler": None, "scheduler": "normal"},
            "ddim": {"sampler": "ddim", "scheduler": "normal"},
            "plms": {"sampler": "plms", "scheduler": "normal"},
            "unipc": {"sampler": "unipc", "scheduler": "normal"},
            "lcm": {"sampler": "lcm", "scheduler": "normal"},
        }
        if name in convert:
            printDebug(f"Sampler {name} converted to {convert[name]}")
            return convert[name]
        return {"sampler": name, "scheduler": None}

    @staticmethod
    def txt2img(
        prompts,
        vae=None,
        hostname="http://127.0.0.1:8188",
        output_dir="outputs",
        options={},
    ):
        try:
            sd_model = options.get("sd_model", None)
            vae = options.get("sd_vae", None)
            wf = ComfyUIWorkflow()
            if sd_model is None:
                raise ValueError("Comfyui is model must needs to be set")
            wf.setModel(sd_model)
            if vae is not None:
                wf.setVAE(vae)
            workflows = []
            for prompt_text in prompts:
                opt = options.copy()
                if prompt_text.get("prompt") is None:
                    workflows.append(prompt_text)
                    continue
                prompt = prompt_text.get("prompt", "")
                n_iter = prompt_text.get("n_iter", 1)
                negative_prompt = prompt_text.get("negative_prompt", "")
                sampler_name = prompt_text.get("sampler_name", "euler")
                sampler = ComufyClient().convertSamplerNameWebUi2Comfy(sampler_name)
                if sampler_name is None:
                    raise ValueError(f"Sampler {sampler_name} not found")
                prompt_text["sampler_name"] = sampler["sampler"]
                scheduler = prompt_text.get("scheduler")
                if scheduler is None:
                    scheduler = sampler.get("scheduler", "normal")
                prompt_text["scheduler"] = scheduler
                for key in prompt_text:
                    opt[key] = prompt_text[key]
                for _ in range(n_iter):
                    workflow, info = wf.createWorkflow(prompt, negative_prompt, opt)
                workflows.append(
                    {"workflow": workflow, "info": info, "prompt_text": prompt_text}
                )
            opt["dir"] = output_dir
            client = ComufyClient()
            client.setHostname(hostname)
            client.run(workflows, opt)
            return True
        except Exception as e:
            printError("Failed to run comfyui", e)
            return False


# options
# --api-comfy   # use comfy api
# --api-comfy-save ui    # save_image ["ui"]
# --api-comfy-save both    # save_image ["ui", "save"]
# --api-comfy-save save    # save_image ["websocket]

if __name__ == "__main__":
    import time

    start_time = time.time()
    filename = "test/comfy.json"
    with open(filename, "r") as f:
        prompts = json.load(f)
        wf = ComfyUIWorkflow()
        # wf.setModel("sd15\\AOM3.safetensors")
        # wf.setVAE("kl-f8-anime2-vae.safetensors")
        wf.setModel("pony\\waiANINSFWPONYXL_v50.safetensors")
        workflows = []
        infos = []
        options = {}
        # options["save_image"] = ["ui", "websocket"]
        options["save_image"] = ["websocket"]
        options["dir"] = "f:/ai/outputs/txt2img-images"

        for prompt_text in prompts:
            opt = options.copy()
            if prompt_text.get("prompt") is None:
                workflows.append(prompt_text)  # native prompt
                continue
            prompt_text["lora_dir"] = "e:\\ai\\models\\lora"
            prompt = prompt_text.get("prompt", "")
            prompt_text["sampler_name"] = "euler_ancestral"
            prompt_text["scheduler"] = "normal"
            negative_prompt = prompt_text.get("negative_prompt", "")
            for key in prompt_text:
                opt[key] = prompt_text[key]
            workflow, info = wf.createWorkflow(prompt, negative_prompt, opt)
            workflows.append(workflow)
            infos.append(info)
        client = ComufyClient()
        client.run(workflows, opt)
    duration = time.time() - start_time
    minutes = duration // 60
    seconds = duration % 60
    printInfo(f"Total Duration: {minutes}m {seconds}s")
