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

from modules.save import DataSaver

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


def printVerbose(*args, **kwargs):
    if logger is not None:
        logger.verbose(*args, **kwargs)
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
        self.wf_num = 3

    # todo:
    # ✓ clip layer
    # ✓ token BREAK over 75 tokens
    # ✓ lora
    # ✓ BREAK
    # AND
    # [sentens] not implement [[]] [[] xxx ]...
    # [from:to:average]
    # hiresfix
    # img2img
    # ✓ infotext warpper for prompt
    # ✓ save_images wrapper
    # search alternative model
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
        output = {"clip": 0}

        return flow, output

    def createLoadCheckpoint(self, checkpoint):
        flow = {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {"ckpt_name": checkpoint},
        }
        output = {"model": 0, "clip": 1, "vae": 2}
        return flow, output

    def createLoadVAE(self, vae):
        flow = {
            "class_type": "VAELoader",
            "inputs": {
                "vae_name": vae,
            },
        }
        output = {"vae": 0}
        return flow, output

    def createKSampler(
        self, latent_from, model_from, positive_from, negative_from, options
    ):
        flow = {
            "class_type": "KSampler",
            "inputs": {
                "cfg": options.get("cfg", 8),
                "denoise": options.get("denoise", 1),
                "latent_image": latent_from,
                "model": model_from,
                "positive": positive_from,
                "negative": negative_from,
                "sampler_name": options.get("sampler_name", "euler"),
                "scheduler": options.get("scheduler", "normal"),
                "seed": options.get("seed", -1),
                "steps": options.get("steps", 20),
            },
        }
        output = {"latent": 0}
        return flow, output

    def createEncodeVAE(self, fromSamples, fromVae, otherVae=False):
        flow = {
            "class_type": "VAEDecode",
            "inputs": {"samples": fromSamples, "vae": fromVae},
        }
        output = {"images": 0}
        return flow, output

    def createSaveWebSocketImage(self, image_form, options):
        flow = {
            "class_type": "SaveImageWebsocket",
            "inputs": {
                "images": image_form,
            },
        }
        output = {}
        return flow, output

    def createSaveImage(self, image_form, options):
        flow = {
            "class_type": "SaveImage",
            "inputs": {
                "filename_prefix": options.get(
                    "prefix", options.get("filename", "Comfy")
                ),
                "images": image_form,
            },
        }
        output = {}
        return flow, output

    def createEmptyLatentImage(self, options):
        flow = {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "batch_size": options.get("batch_size", 1),
                "height": options.get("height", 512),
                "width": options.get("width", 512),
            },
        }
        output = {"latent": 0}
        return flow, output

    def createConditioningConcat(self, from_prompt, to_prompt):
        flow = {
            "class_type": "ConditioningConcat",
            "inputs": {
                "conditioning_to": to_prompt,
                "conditioning_from": from_prompt,
            },
        }
        output = {"conditioning": 0}
        return flow, output

    def createConditioningAverage(self, from_prompt, to_prompt, average):
        flow = {
            "class_type": "ConditioningAverage",
            "inputs": {
                "conditioning_to": to_prompt,
                "conditioning_from": from_prompt,
                "conditioning_to_strength": average,
            },
        }
        output = {"conditioning": 0}
        return flow, output

    def createConditioningCombine(self, from_prompt, to_prompt):
        flow = {
            "class_type": "ConditioningCombine",
            "inputs": {
                "conditioning_to": to_prompt,
                "conditioning_from": from_prompt,
            },
        }
        output = {"conditioning": 0}
        return flow, output

    def createBatchTextEncode(self, wf, prompt, clip, type, steps=20):
        # and_matcher = re.compile(r"AND")
        blacket_matcher = re.compile(r"\[([^\:\|]?)\]")
        blackets_all = blacket_matcher.findall(prompt)
        for blacket in blackets_all:
            prompt = prompt.replace(f"[{blacket}]", f"({blacket}:0.91)")
        prompts = prompt.split("BREAK")
        from_prompt = None
        if type == "sdxl":
            wf[str(self.wf_num)], o = self.createCLIPTextEncodeSDXL(prompts[0], clip)
        else:
            wf[str(self.wf_num)], o = self.createCLIPTextEncode(prompts[0], clip)
        from_prompt = [str(self.wf_num), o["conditioning"]]
        prompts = prompts[1:]
        for prompt in prompts:
            self.wf_num += 1
            wf, o = self.createBatchTextEncode(wf, prompt, clip, type, steps)
            to_prompt = [str(self.wf_num), o["conditioning"]]
            self.wf_num += 1
            wf[str(self.wf_num)], o = self.createConditioningConcat(
                from_prompt, to_prompt
            )
            from_prompt = [str(self.wf_num), o["conditioning"]]
        prompts = prompt.split("AND")
        prompts = prompts[1:]
        for prompt in prompts:
            self.wf_num += 1
            wf, o = self.createBatchTextEncode(wf, prompt, clip, type, steps)
            to_prompt = [str(self.wf_num), o["conditioning"]]
            self.wf_num += 1
            wf[str(self.wf_num)], o = self.createConditioningCombine(
                from_prompt, to_prompt
            )
            from_prompt = [str(self.wf_num), o["conditioning"]]
        output = {"conditioning": 0}
        return wf, output

    def createCLIPTextEncode(self, prompt, clip):
        flow = {
            "class_type": "CLIPTextEncode",
            "inputs": {"clip": clip, "text": prompt},
        }
        output = {"conditioning": 0}
        return flow, output

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
        output = {"conditioning": 0}
        return flow, output

    def createLoraLoader(self, fromModel, clip, loraname, weight, options={}):
        if not loraname.endswith(".safetensors"):
            loraname = loraname + ".safetensors"
        flow = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": loraname,
                "strength_model": weight,
                "strength_clip": weight,
                "model": fromModel,
                "clip": clip,
            },
        }
        output = {"model": 0, "clip": 1}
        return flow, output

    def createHiresfix(
        self,
        workflow,
        fromLatent,
        fromModel,
        fromPositive,
        formNegative,
        clip,
        seed,
        options={},
    ):
        upscale_method = options.get("upscale_method", "nearest-exact")
        denoising_strength = options.get("denoising_strength", 0)
        scale = options.get("hr_scale", 2)
        width = options.get("hr_resize_x", 0)
        height = options.get("hr_resize_y", 0)
        seconde_step = options.get("hr_second_pass_steps", 0)
        if seconde_step == 0:
            seconde_step = options.get("steps", 20)
        if width == 0 and height == 0:
            if scale == 1:
                return workflow[str(self.wf_num)], {
                    "latent": fromLatent,
                    "model": fromModel,
                    "clip": clip,
                }
            workflow[str(self.wf_num)], o = self.createCustom(
                "LatentUpscaleBy",
                {
                    "samples": fromLatent,
                    "upscale_method": upscale_method,
                    "scale_by": scale,
                },
                {"output": {"latent": 0}},
            )
        else:
            f1width = options.get("width", 512)
            f1height = options.get("height", 512)
            aspect = f1width / f1height
            if width == 0:
                width = height * aspect
            elif height == 0:
                aspect = f1height / f1width
                height = width * aspect
            workflow[str(self.wf_num)], o = self.createCustom(
                "LatentUpscale",
                {
                    "samples": fromLatent,
                    "upscale_method": upscale_method,
                    "width": width,
                    "height": height,
                    "clop": "disabled",
                },
                {"output": {"latent": 0}},
            )
        fromLatent = [str(self.wf_num), o["latent"]]
        self.wf_num += 1

        hr_positive = options.get("hr_prompt", None)
        if hr_positive is not None:
            if options.get("type") == "sdxl":
                workflow[str(self.wf_num)], o = self.createCLIPTextEncodeSDXL(
                    hr_positive, clip
                )
            else:
                workflow[str(self.wf_num)], o = self.createCLIPTextEncode(
                    hr_positive, clip
                )
            fromPositive = [str(self.wf_num), o["conditioning"]]
            self.wf_num += 1

        hr_negative = options.get("hr_negative_prompt", None)
        if hr_negative is not None:
            if options.get("type") == "sdxl":
                workflow[str(self.wf_num)], o = self.createCLIPTextEncodeSDXL(
                    hr_negative, clip
                )
            else:
                workflow[str(self.wf_num)], o = self.createCLIPTextEncode(
                    hr_negative, clip
                )
            formNegative = [str(self.wf_num), o["conditioning"]]
            self.wf_num += 1

        checkpoint = options.get("hr_checkpoint_name", None)
        if checkpoint is not None:
            workflow[str(self.wf_num)], o = self.createLoadCheckpoint(checkpoint)
            self.wf_num += 1
            fromModel = [str(self.wf_num), o["model"]]
            clip = [str(self.wf_num), o["clip"]]

        if "hr_scheduler" in options:
            scheduler = options["hr_scheduler"]
        else:
            scheduler = options.get("scheduler", "karras")
        if "hr_sampler_name" in options:
            sampler_name = options["hr_sampler_name"]
        else:
            sampler_name = options.get("sampler_name", "dpmpp_2m_sde")

        workflow[str(self.wf_num)], o = self.createKSampler(
            fromLatent,
            fromModel,
            fromPositive,
            formNegative,
            {
                "cfg": options.get("cfg_scale", 7),
                "denoise": denoising_strength,
                "sampler_name": scheduler,
                "scheduler": sampler_name,
                "seed": seed,
                "steps": seconde_step,
            },
        )
        result = {
            "latent": o["latent"],
            "model": fromModel,
            "positive": fromPositive,
            "neagative": formNegative,
            "clip": clip,
        }

        return workflow, result

    # example
    # createCustom("UpscaleLatent", {"upscale_method": "nearest-exact", "width": 1024, "height": 1024, "clop": "disabled"}, {"output": {"latent": 0}})

    def createCustom(self, class_type, input, options={}):
        flow = {
            "class_type": class_type,
            "inputs": input,
        }
        output = options.get("output", {})
        return flow, output

    def createWorkflowSDXL(self, prompt, negative_prompt, options={}):
        options["type"] = "sdxl"
        return self.createWorkflow(prompt, negative_prompt, options)

    def createWorkflowSD15(self, prompt, negative_prompt, options={}):
        options["type"] = "sd15"
        return self.createWorkflow(prompt, negative_prompt, options)

    def createWorkflow(self, prompt, negative_prompt, options={}):
        printDebug("Creating workflow")
        info = {
            "prompt": prompt,
            "negative_prompt": negative_prompt,
        }
        other_vae = False
        printDebug(f"parse prompt {prompt}")
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
        self.wf_num = 3
        base_width = 1024 if options.get("type") == "sdxl" else 512
        width = options.get("width", base_width)
        base_height = 1024 if options.get("type") == "sdxl" else 512
        height = options.get("height", base_height)
        batch_size = options.get("batch_size", 1)

        printDebug(f"Creating empty latent image")
        workflow[str(self.wf_num)], o = self.createEmptyLatentImage(
            {
                "batch_size": batch_size,
                "height": height,
                "width": width,
            }
        )
        latent_from = [str(self.wf_num), o["latent"]]
        self.wf_num += 1
        info["width"] = width
        info["height"] = height
        info["batch_size"] = batch_size

        printDebug(f"checkpoint: {checkpoint}")
        workflow[str(self.wf_num)], o = self.createLoadCheckpoint(checkpoint)
        model_from = [str(self.wf_num), o["model"]]
        positive_clip_from = [str(self.wf_num), o["clip"]]  # 1 is clip index
        negative_clip_from = [str(self.wf_num), o["clip"]]
        vae_from = [str(self.wf_num), o["vae"]]
        self.wf_num += 1
        info["sd_model_name"] = checkpoint

        printDebug(f"set stop at clip layer")
        if options.get("stop_at_clip_layer") is not None:
            workflow[str(self.wf_num)], o = self.creatCLIPSetLastLayer(
                options.get("stop_at_clip_layer"), positive_clip_from
            )
            positive_clip_from = [str(self.wf_num), o["clip"]]
            negative_clip_from = [str(self.wf_num), o["clip"]]
            self.wf_num += 1
            info["clip_skip"] = abs(options.get("stop_at_clip_layer", 1))

        printDebug(f"vae: {vae}")
        if vae != "None":
            workflow[str(self.wf_num)], o = self.createLoadVAE(vae)
            vae_from = [str(self.wf_num), o["vae"]]
            self.wf_num += 1
            other_vae = True
        info["sd_vae_name"] = vae
        if vae == "None":
            info["sd_vae_name"] = None

        printDebug(f"load lora")
        for lora, weight in postive_loras:
            wf, o = self.createLoraLoader(
                model_from, positive_clip_from, lora, float(weight), options
            )
            if wf is not None:
                workflow[str(self.wf_num)] = wf
                model_from = [str(self.wf_num), o["model"]]
                positive_clip_from = [str(self.wf_num), o["clip"]]
                self.wf_num += 1

        for lora, weight in negative_loras:
            wf, o = self.createLoraLoader(
                negative_clip_from, negative_prompt, lora, float(weight), options
            )
            if wf is not None:
                workflow[str(self.wf_num)] = wf
                model_from = [str(self.wf_num), o["model"]]
                negative_clip_from = [str(self.wf_num), o["clip"]]
                self.wf_num += 1

        printDebug(f"create batch text encode")
        workflow, o = self.createBatchTextEncode(
            workflow,
            prompt,
            positive_clip_from,
            options.get("type"),
            options.get("steps", 20),
        )
        positive_from = [str(self.wf_num), o["conditioning"]]
        self.wf_num += 1
        workflow, o = self.createBatchTextEncode(
            workflow,
            negative_prompt,
            negative_clip_from,
            options.get("type"),
            options.get("steps", 20),
        )
        negative_from = [str(self.wf_num), o["conditioning"]]
        self.wf_num += 1

        printDebug(f"create k sampler")
        workflow[str(self.wf_num)], o = self.createKSampler(
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
        sampler_from = [str(self.wf_num), o["latent"]]
        self.wf_num += 1
        info["cfg_scale"] = options.get("cfg_scale", 7)
        # info["denoising_strength"] = options.get("nomal_denoising_strength")
        info["sampler_name"] = options.get(
            "sampler_name", "dpmpp_2m_sde"
        )  # sampler mapper
        info["scheduler"] = options.get("scheduler", "karras")
        info["steps"] = options.get("steps", 20)

        if options.get("enable_hr", False):
            printDebug(f"create hiresfix")
            workflow, result = self.createHiresfix(
                workflow,
                sampler_from,
                model_from,
                positive_from,
                negative_from,
                positive_clip_from,
                seed,
                options,
            )
            sampler_from = result["latent"]
            model_from = result["model"]
            positive_from = result["positive"]
            negative_from = result["negative"]
            positive_clip_from = result["clip"]
            self.wf_num += 1

        printDebug(f"create encode vae")
        workflow[str(self.wf_num)], o = self.createEncodeVAE(
            sampler_from, vae_from, other_vae
        )
        encode_from = [str(self.wf_num), o["images"]]
        self.wf_num += 1
        printDebug(f"create save image")
        if "ui" in options.get("save_image", []):
            workflow[str(self.wf_num)], o = self.createSaveImage(encode_from, options)
            self.wf_num += 1
        if "websocket" in options.get("save_image", ["websocket"]):
            workflow["save_image_websocket_node"], o = self.createSaveWebSocketImage(
                encode_from, options
            )
        return workflow, info


class ComufyClient:
    def __init__(self, hostname="http://127.0.0.1:8188") -> None:
        self.client = httpx.AsyncClient()
        self.hostname = hostname
        self.server_address = self.hostname.replace("http://", "").replace(
            "https://", ""
        )
        self.object_info = None
        self.saver = None

    async def getModels(self):
        res = await self.client.get(
            f"{self.hostname}/object_info/CheckpointLoaderSimple"
        )
        if res.status_code != 200:
            printError(f"Failed to get models {res.text}")
            return None
        res_json = res.json()
        models = res_json["inputs"]["required"]["ckpt_name"]  # [][]

        return models

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
        try:
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
                        if seed > 0:
                            seed += 1
                        images.append(data)
                else:
                    data = {
                        "url": url,
                        "image": None,
                    }
                    images.append(data)
            return images
        except Exception as e:
            printError("Failed to get images", e)
            raise Exception("Failed to get images from comfyui in getImageFromUI")

    async def write_progress(self, result):
        import shutil

        width = shutil.get_terminal_size().columns
        header = result["header"]
        percentage = result["progress"]
        footer = result["footer"]
        usefull_width = width - len(f"{header} || {footer}") - 10
        perblock = 100.0 / usefull_width
        if usefull_width > 10:
            sharp = "█" * int(percentage / perblock + 0.5)
            space = " " * (usefull_width - len(sharp))
        else:
            sharp = ""
            space = ""
        string = f"\033[{header} |{sharp}{space}| {footer}"
        print(string, end="\r")

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
                                result = {
                                    "header": "progress",
                                    "progress": percentage,
                                    "footer": f"{value}/{max} {duration:2f} sec",
                                }
                                await self.write_progress(result)
                        elif message.get("type") == "status":
                            try:
                                data = message.get("data", {})
                                status = data.get("status", {})
                                exec_info = status.get("exec_info", {})
                                text = "waiting... "
                                for k, v in exec_info.items():
                                    text += f"{k}: {v} "
                                print(
                                    text,
                                    end="\r",
                                )
                            except Exception as e:
                                printError("- Failed to print status", e)
                    except Exception as e:
                        printError("Failed to parse message", e)
                        printError(out[:100])
                else:
                    if current_node == "save_image_websocket_node":
                        images_output = output_images.get(current_node, [])
                        images_output.append(out[8:])
                        output_images[current_node] = images_output
            return output_images
        except KeyboardInterrupt:
            printWarning("Interrupted")
            await self.client.post(f"{self.hostname}/interrupt")
            raise KeyboardInterrupt
        except Exception as e:
            printError("Failed to get images", e)
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
        if "prompt" not in info:
            text = prompt_text.copy()
            del text["verbose"]
            infotexts = json.dumps(prompt_text)
        else:
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
        try:

            try:
                r, options = await self.imageWrapper(
                    [image_data], prompt_text, options, info
                )
                options["workflow"] = json.dumps(prompt, ensure_ascii=False)
            except Exception as e:
                printError("Failed to wrap image", e)
                raise e

            try:
                if self.saver is None:
                    saver = DataSaver()
                    self.saver = saver
                await self.saver.asave_images(r, options)
            except Exception as e:
                printError("Failed to async save image", e)
                raise e
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

    async def uploadImage(
        self, filename, binary=None, minetype="image/png", overwrite=False
    ):
        if binary is None:
            with open(filename, "rb") as f:
                binary = f.read()
        else:
            file = (filename, binary, minetype)

        payload = {}
        payload["image"] = file
        if overwrite:
            payload["overwrite"] = True

        res = await self.client.post(f"{self.hostname}/upload/image", files=payload)
        if res.status_code != 200:
            printError(f"Failed to upload image {filename} {res.text}")
            return None
        return res.json()

    async def arun(self, prompts, options={}):
        if "websocket" in options.get("save_image", []):
            ws = websocket.WebSocket()
            for i, _prompt in enumerate(prompts):
                prompt = _prompt.get("workflow")
                info = _prompt.get("info", {})
                prompt_text = _prompt["prompt_text"]

                printInfo(f"process queuing {i+1}/{len(prompts)}")
                client_id = str(uuid.uuid4())
                ws.connect(f"ws://{self.server_address}/ws?clientId={client_id}")
                images = await self.getImages(ws, prompt, client_id, _prompt)
                if images is None:
                    printError("Failed to get images")
                    continue

                for node_id in images:
                    seed = int(info.get("seed", -1))
                    for image_data in images[node_id]:
                        _info = info.copy()
                        if seed > 0:
                            _info["seed"] = seed
                            seed += 1
                        await self.saveImage(
                            image_data, prompt, options, _info, prompt_text
                        )
                ws.close()
        elif "ui" in options.get("save_image", ["ui"]):
            for prompt in prompts:
                client_id = str(uuid.uuid4())
                try:
                    images = await self.getImageFromUI(prompt, client_id, options)
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
            printVerbose(f"Sampler {name} converted to {convert[name]}")
            return convert[name]
        return {"sampler": name, "scheduler": None}

    def _model_search(self, model_name, required):
        ext = re.compile(r"\.(safetensors|pt|ckpt)$")
        base_name = ext.sub("", model_name)
        check = False
        alternames = []
        if self.object_info is not None:
            parsed = self.object_info.get("perced", {})
        else:
            printError("Object info not found")
            return False, []
        for model_names in required:
            if model_name in model_names:
                return True, []
            else:
                _model_name = model_name.replace("\\", "/")
                if _model_name in model_names:
                    alternames.append(_model_name)
                    printVerbose(f"Model {model_name} converted to {_model_name}")
                    break
                _model_name = model_name.replace("/", "\\")
                if _model_name in model_names:
                    alternames.append(_model_name)
                    printVerbose(f"Model {model_name} converted to {_model_name}")
                    break
                for name in model_names:
                    _base_name = parsed.get(name)
                    if _base_name is None:
                        _base_name = ext.sub("", name)
                        parsed[name] = _base_name
                    if _base_name.endswith(base_name):
                        printVerbose(f"Model {model_name} converted to {name}")
                        alternames.append(name)
                    elif name.endswith(model_name):
                        printVerbose(f"Model {model_name} converted to {name}")
                        alternames.append(name)
        self.object_info["perced"] = parsed
        return check, alternames

    def checkWorkflow(self, workflow, options={}):
        workflow = workflow.copy()
        try:
            printDebug(f"Checking workflow ...")
            if self.object_info is None:
                with httpx.Client() as client:
                    try:
                        res = client.get(self.hostname + "/object_info")
                    except httpx.TimeoutException as e:
                        printError(f"Connect timeout, Server is down?")
                        raise e
                    except httpx.RequestError as e:
                        printError(f"Failed to get models {e}")
                        raise Exception(f"Failed to get models {e}")
                    if res is None:
                        printError("Failed to get models")
                        return False
                    if res.status_code != 200:
                        printError("Failed to check workflow, object info not found")
                        return False
                object_info = res.json()
                self.object_info = {"object_info": object_info}
            else:
                object_info = self.object_info["object_info"]
            printDebug("ComfyUI object_info")

            # printDebug(json.dumps(object_info, indent=4))
            info = {}
            positive = None
            negative = None
            is_error = False
            for node_id in workflow:

                printDebug(f"Checking node {node_id}")
                node = workflow[node_id]
                class_type = node["class_type"]
                if class_type not in object_info:
                    printError(
                        f"{node_id} Class type {class_type} not found, Check workflow or plugin"
                    )
                    raise Exception(f"Class type {class_type} not found")
                required = object_info[class_type].get("input", {}).get("required", {})
                if class_type not in object_info:
                    printError(f"Class type {class_type} not found")
                    is_error = True
                if class_type == "KSampler":
                    info["sampler_name"] = node["inputs"]["sampler_name"]
                    info["scheduler"] = node["inputs"]["scheduler"]
                    info["steps"] = node["inputs"]["steps"]
                    info["seed"] = node["inputs"]["seed"]
                    info["cfg_scale"] = node["inputs"]["cfg"]
                    info["denoising_strength"] = node["inputs"]["denoise"]
                    if positive is None:
                        positive = node["inputs"]["positive"]
                    if negative is None:
                        negative = node["inputs"]["negative"]

                    check = False
                    for sampler_name in required["sampler_name"]:
                        if info["sampler_name"] in sampler_name:
                            check = True
                            break
                    if not check:
                        printError(f"Sampler {info['sampler_name']} not found")
                        is_error = True
                    check = False
                    for scheduler in required["scheduler"]:
                        if info["scheduler"] in scheduler:
                            check = True
                            break
                    if not check:
                        printError(f"Scheduler {info['scheduler']} not found")
                        is_error = True
                elif class_type == "CLIPSetLastLayer":
                    if node["inputs"]["stop_at_clip_layer"] >= 0:
                        is_error = True
                    info["clip_skip"] = abs(node["inputs"]["stop_at_clip_layer"])
                elif class_type == "VAELoader":
                    info["sd_vae_name"] = node["inputs"]["vae_name"]
                    check, alternames = self._model_search(
                        info["sd_vae_name"], required["vae_name"]
                    )
                    if not check:
                        if len(alternames) > 0:
                            printWarning(
                                f"VAE {info['sd_vae_name']} not found, but found similar models {alternames} use {alternames[0]}"
                            )
                            node["inputs"]["vae_name"] = alternames[0]
                        else:
                            is_error = True
                            printError(f"VAE {info['sd_vae_name']} not found")
                elif class_type == "CheckpointLoaderSimple":
                    info["sd_model_name"] = node["inputs"]["ckpt_name"]
                    check, alternames = self._model_search(
                        info["sd_model_name"], required["ckpt_name"]
                    )

                    if not check:
                        if len(alternames) > 0:
                            printWarning(
                                f"Model {info['sd_model_name']} not found, but found similar models {alternames} use {alternames[0]}"
                            )
                            node["inputs"]["ckpt_name"] = alternames[0]
                        else:
                            is_error = True
                            printError(f"Model {info['sd_model_name']} not found")
                            raise Exception(f"Model {info['sd_model_name']} not found")
                elif class_type == "LoraLoader":
                    if "lora" not in info:
                        info["lora"] = []

                    lora_name = node["inputs"]["lora_name"]
                    info["lora"].append(lora_name)
                    check, alternames = self._model_search(
                        lora_name, required["lora_name"]
                    )

                    if not check:
                        if len(alternames) > 0:
                            printWarning(
                                f"Lora {lora_name} not found, but found similar loras {alternames} use {alternames[0]}"
                            )
                            node["inputs"]["lora_name"] = alternames[0]
                        else:
                            is_error = True
                            printError(f"Lora {lora_name} not found")
                            raise Exception(f"Lora {lora_name} not found")
                elif class_type == "CLIPTextEncode":
                    info["prompt"] = node["inputs"]["text"]

                # all required inputs check
                for key in required:
                    if key in node["inputs"]:
                        node_type = required[key][0]
                        if not isinstance(node_type, str):
                            if isinstance(node_type, list):
                                printVerbose(f"Array Node type {node_type}")
                                input_values = node["inputs"][key]
                                if (
                                    key != "ckpt_name"
                                    or key != "lora_name"
                                    or key != "vae_name"
                                ):

                                    if input_values not in node_type:
                                        printError(
                                            f'node "{node_id}" {key} must be one of required_values, but got {input_values} not found'
                                        )
                                        printVerbose(f"Required values {node_type}")
                                        is_error = True
                        elif node_type == "INT":
                            if not isinstance(node["inputs"][key], int):
                                try:
                                    node["inputs"][key] = int(node["inputs"][key])
                                except Exception as e:
                                    printError(
                                        f"{node_id} {key} must be integer, but got {node['inputs'][key]}"
                                    )
                                    is_error = True
                            min = required[key][1].get("min", None)
                            max = required[key][1].get("max", None)
                            if min is not None and node["inputs"][key] < min:
                                printError(
                                    f"{node_id} {key} must be greater than {min}, but got {node['inputs'][key]}"
                                )
                                is_error = True
                            if max is not None and node["inputs"][key] > max:
                                printError(
                                    f"{node_id} {key} must be less than {max}, but got {node['inputs'][key]}"
                                )
                                is_error = True
                        elif node_type == "FLOAT":
                            if not isinstance(node["inputs"][key], float):
                                try:
                                    node["inputs"][key] = float(node["inputs"][key])
                                except Exception as e:
                                    printError(
                                        f"node \"{node_id}\" {key} must be float, but got {node['inputs'][key]}"
                                    )
                                    is_error = True
                            min = required[key][1].get("min", None)
                            max = required[key][1].get("max", None)
                            if min is not None and node["inputs"][key] < min:
                                printError(
                                    f"{node_id} {key} must be greater than {min}, but got {node['inputs'][key]}"
                                )
                                is_error = True
                            if max is not None and node["inputs"][key] > max:
                                printError(
                                    f"{node_id} {key} must be less than {max}, but got {node['inputs'][key]}"
                                )
                                is_error = True
                        elif node_type == "STRING":
                            if not isinstance(node["inputs"][key], str):
                                printError(
                                    f"{node_id} {key} must be string, but got {node['inputs'][key]}"
                                )
                                is_error = True
                            allow_mutli = required[key][1].get("multiline", False)
                            if not allow_mutli:
                                if "\n" in node["inputs"][key]:
                                    printError(
                                        f"{node_id} {key} must be single line, but got multiline"
                                    )
                                    is_error = True

                    else:
                        printError(f"Required input {key} not found")

            def prompt_search(workflow, position, prompt=""):
                node_id = position[0]
                index = position[1]
                node = workflow[node_id]
                if node is None:
                    return prompt
                class_type = node["class_type"]
                if class_type == "CLIPTextEncode":
                    prompt = node["inputs"]["text"] + prompt
                    return prompt
                elif class_type == "CLIPTextEncodeSDXL":
                    prompt = node["inputs"]["text_g"] + prompt
                    return prompt
                elif class_type == "ConditioningConcat":
                    prompt_1 = prompt_search(
                        workflow, node["inputs"]["conditioning_from"]
                    )
                    if prompt_1 is None:
                        prompt_1 = ""
                    prompt_2 = prompt_search(
                        workflow, node["inputs"]["conditioning_to"]
                    )
                    prompt = prompt_1 + " BREAK " + prompt_2
                    return prompt
                elif class_type == "ConditioningAverage":
                    prompt_to = prompt_search(
                        workflow, node["inputs"]["conditioning_to"]
                    )
                    prompt_from = prompt_search(
                        workflow, node["inputs"]["conditioning_from"]
                    )
                    average = node["inputs"]["conditioning_to_strength"]
                    prompt = f"[{prompt_to}:{prompt_from}:{average}]"
                    return prompt
                elif class_type == "ConditioningCombine":
                    prompt_1 = prompt_search(workflow, node["inputs"]["conditioning_1"])
                    prompt_2 = prompt_search(workflow, node["inputs"]["conditioning_2"])
                    prompt = prompt_1 + " AND " + prompt_2
                    return prompt
                else:
                    printVerbose(
                        f"Class type {class_type} is unknown,also custom node, try search before node"
                    )
                    try:
                        obj_info = object_info.get(class_type, {})
                        required = obj_info["input"]["required"]
                        conds = []
                        for key in required:
                            if required[key][0] == "CONDITIONING":
                                conds.append(key)
                        if len(conds) > index:
                            return prompt_search(workflow, node["inputs"][conds[index]])
                        elif len(conds) == 1:
                            return prompt_search(workflow, node["inputs"][conds[0]])
                        else:
                            for key in required:
                                if (
                                    required[key][0] == "STRING"
                                    and required[key][1]["multiline"]
                                ):
                                    return prompt_search(workflow, node["inputs"][key])
                    except Exception as e:
                        printError("Failed to search prompt", e)
                        return prompt

            positive_prompt = prompt_search(workflow, positive)
            negative_prompt = prompt_search(workflow, negative)
            printVerbose(f"reconstruct prompts:")
            printVerbose(f"Positive prompt: {positive_prompt}")
            printVerbose(f"Negative prompt: {negative_prompt}")

            if positive_prompt != "":
                info["prompt"] = positive_prompt
            if negative_prompt != "":
                info["negative_prompt"] = negative_prompt
        except Exception as e:
            printError("Failed to check workflow", e)
            return None, None
        if is_error:
            printError("Workflow is invalid")
            return None, None
        printDebug("Workflow is valid")
        return workflow, info

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
            wf.setModel(sd_model)
            client = ComufyClient(hostname=hostname)
            if vae is not None:
                wf.setVAE(vae)
            workflows = []
            for prompt_text in prompts:
                opt = options.copy()
                if prompt_text.get("prompt") is None:
                    import copy

                    workflow = copy.deepcopy(prompt_text)
                    del workflow["verbose"]
                    printDebug("Use Workflow")
                    workflow, info = client.checkWorkflow(workflow, opt)
                    if info is None:
                        printError("Failed to check workflow")
                        continue
                    workflows.append(
                        {
                            "workflow": workflow,
                            "info": info,
                            "prompt_text": prompt_text,
                        }
                    )
                    continue
                if sd_model is None:
                    printError("Model not set")
                    continue
                prompt = prompt_text.get("prompt", "")
                n_iter = prompt_text.get("n_iter", 1)
                negative_prompt = prompt_text.get("negative_prompt", "")
                sampler_name = prompt_text.get("sampler_name", "euler")
                sampler = client.convertSamplerNameWebUi2Comfy(sampler_name)
                if sampler_name is None or sampler is None:
                    raise ValueError(f"Sampler {sampler_name} not found")
                prompt_text["sampler_name"] = sampler["sampler"]
                scheduler = prompt_text.get("scheduler")
                if scheduler is None:
                    scheduler = sampler.get("scheduler", "normal")
                prompt_text["scheduler"] = scheduler
                for key in prompt_text:
                    opt[key] = prompt_text[key]
                seed = opt.get("seed", -1)
                if seed == -1:
                    seed = random.randint(0, 2**31 - 1)
                for _ in range(n_iter):
                    opt["seed"] = seed
                    _workflow, info = wf.createWorkflow(prompt, negative_prompt, opt)
                    if _workflow is None:
                        printError("Failed create workflow")
                        continue
                    workflow, _ = client.checkWorkflow(_workflow, opt)
                    if workflow is None:
                        printError("Failed to check workflow")
                        continue
                    if seed > 0:
                        opt["seed"] = seed
                        seed += info.get("batch_size", 1)
                    workflows.append(
                        {"workflow": workflow, "info": info, "prompt_text": prompt_text}
                    )
            opt["dir"] = output_dir
            client = ComufyClient(hostname=hostname)
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

        client = ComufyClient()
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
            try:
                client.checkWorkflow(workflow, opt)
            except httpx.TimeoutException as e:
                printError("Timeout server is down?", e)
                raise e
            except Exception as e:
                printError("Failed to check workflow", e)

            n_iter = prompt_text.get("n_iter", 1)
            for _ in range(prompt_text["n_iter"]):
                workflow, info = wf.createWorkflow(prompt, negative_prompt, opt)
            infos.append(info)
        client.run(workflows, opt)
    duration = time.time() - start_time
    minutes = duration // 60
    seconds = duration % 60
    printInfo(f"Total Duration: {minutes}m {seconds}s")
