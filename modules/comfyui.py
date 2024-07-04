# This is an example that uses the websockets api and the SaveImageWebsocket node to get images directly without
# them being saved to disk

import json
import random
import re
import urllib.parse
import urllib.request
import uuid

import httpx
import websocket  # NOTE: websocket-client (https://github.com/websocket-client/websocket-client)


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

    def creatCLIPSetLastLayer(self, stop_at_clip_layer):
        flow = {
            "class_type": "CLIPSetLastLayer",
            "inputs": {"stop_at_clip_layer": stop_at_clip_layer},
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
            "inputs": {"clip": [clip, 1], "text": prompt},
        }
        return flow

    def createCLIPTextEncodeSDXL(self, text, clip):
        flow = {
            "class_type": "CLIPTextEncodeSDXL",
            "inputs": {
                "clip": clip,
            },
            "width": 4096,
            "height": 4096,
            "crop_w": 0,
            "crop_h": 0,
            "target_width": 4096,
            "target_height": 4096,
            "text_g": text,
            "text_r": text,
        }
        return flow

    def searchLora(self, loraname, options, subfolder=""):
        import os

        lora_dir = os.path.join(options.get("lora_dir", "lora"), subfolder)
        if os.path.exists(os.path.join(lora_dir, loraname + ".safetensors")):
            return os.path.join(subfolder, loraname + ".safetensors")
        lora_dirs = os.scandir(lora_dir)
        for dir in lora_dirs:
            if dir.is_dir():
                next_subfolder = os.path.join(subfolder, dir.name)
                result = self.searchLora(loraname, options, next_subfolder)
                if result is not None:
                    return result
        return None

    def createLoraLoader(self, fromModel, clip, loraname, weight, options={}):
        loraname = self.searchLora(loraname, options)
        if loraname is None:
            # print(f"Failed to find lora {loraname}")
            return None
        flow = {
            "class_type": "LoraLoader",
            "inputs": {
                "lora_name": loraname,
                "strength_model": weight,
                "strength_clip": weight,
                "model": [fromModel, 0],
                "clip": [clip, 1],
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
        positive_clip_from = model_from
        negative_clip_from = model_from
        vae_from = model_from
        wf_num += 1
        info["sd_model_name"] = checkpoint

        if options.get("stop_at_clip_layer") is not None:
            workflow[str(wf_num)] = self.creatCLIPSetLastLayer(
                options.get("stop_at_clip_layer")
            )
            positive_clip_from = str(wf_num)
            negative_clip_from = str(wf_num)
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
                positive_clip_from = model_from

        for lora, weight in negative_loras:
            wf = self.createLoraLoader(
                negative_clip_from, negative_prompt, lora, float(weight), options
            )
            if wf is not None:
                workflow[str(wf_num)] = wf
                model_from = str(wf_num)
                wf_num += 1
                negative_clip_from = str(wf_num)

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

        """
        if options.get("type") == "sdxl":
            workflow[str(wf_num)] = self.createCLIPTextEncodeSDXL(
                prompt, positive_clip_from
            )
        else:
            workflow[str(wf_num)] = self.createCLIPTextEncode(
                prompt, positive_clip_from
            )
        positive_from = str(wf_num)
        wf_num += 1
        if options.get("type") == "sdxl":
            workflow[str(wf_num)] = self.createCLIPTextEncodeSDXL(
                negative_prompt, negative_clip_from
            )
        else:
            workflow[str(wf_num)] = self.createCLIPTextEncode(
                negative_prompt, negative_clip_from
            )
        negative_from = str(wf_num)
        wf_num += 1
        """

        workflow[str(wf_num)] = self.createKSampler(
            latent_from,
            model_from,
            positive_from,
            negative_from,
            {
                "cfg": options.get("cfg", 7),
                "denoise": options.get("denoise", 1),
                "sampler_name": options.get("sampler_name", "dpmpp_2m_sde"),
                "scheduler": options.get("scheduler", "karras"),
                "seed": seed,
                "steps": options.get("steps", 20),
            },
        )
        sampler_from = str(wf_num)
        wf_num += 1
        info["cfg_scale"] = options.get("cfg", 7)
        info["denoising_strength"] = options.get("denoise")
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
        self.server_address = "127.0.0.1:8188"

    async def queuePrompt(self, prompt, client_id):
        p = {"prompt": prompt, "client_id": client_id}
        # print(json.dumps(p, indent=4))
        req = await self.client.post(
            "http://{}/prompt".format(self.server_address), json=p
        )
        if req.status_code != 200:
            print(json.dumps(prompt, indent=4))
            print(json.dumps(req.json(), indent=4))
            raise Exception(req.text)
        return req.json()

    async def getImage(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}

        res = await self.client.post(
            "http://{}/get_image".format(self.server_address), json=data
        )
        return res.content

    async def getHistory(self, prompt_id):
        res = await self.client.get(
            "http://{}/history/{}".format(self.server_address, prompt_id)
        )
        return res.json()

    async def getImages(self, ws, prompt, client_id, options={}):
        try:
            res = await self.queuePrompt(prompt, client_id)
            prompt_id = res["prompt_id"]
            output_images = {}
            current_node = ""
            while True:
                out = ws.recv()
                # print(out[:100])
                if isinstance(out, str):
                    message = json.loads(out)
                    if message["type"] == "executing":
                        data = message["data"]
                        if data["prompt_id"] == prompt_id:
                            if data["node"] is None:
                                break  # Execution is done
                            else:
                                current_node = data["node"]
                else:
                    if current_node == "save_image_websocket_node":
                        images_output = output_images.get(current_node, [])
                        images_output.append(out[8:])
                        output_images[current_node] = images_output

            return output_images
        except Exception as e:
            return None

    def imageWrapper(self, images, prompt, options):
        r = {
            "info": {
                "infotexts": [],
            },
            "parameters": {},
            "images": [],
        }
        for node_id in enumerate(images):
            for image_data in images[node_id]:
                r["images"].append(image_data)
                r["info"]["infotexts"].append(prompt)

        return r

    async def arun(self, prompts, options={}):
        client = ComufyClient()
        ws = websocket.WebSocket()
        for prompt in prompts:
            client_id = str(uuid.uuid4())
            ws.connect("ws://{}/ws?clientId={}".format(self.server_address, client_id))
            images = await client.getImages(ws, prompt, client_id)
            if images is None:
                print("Failed to get images")
                continue

            # Commented out code to display the output images:

            for node_id in images:
                for image_data in images[node_id]:
                    import datetime
                    import io
                    import os

                    from PIL import Image

                    image = Image.open(io.BytesIO(image_data))
                    dirctory = options.get("dir", "outputs")
                    os.makedirs(dirctory, exist_ok=True)
                    now = datetime.datetime.now()
                    imagename = now.strftime("%H%M%S")
                    image.save(f"{dirctory}/img{imagename}.png")
            ws.close()

    def run(self, prompt, options={}):
        import asyncio

        asyncio.run(self.arun(prompt, options))


if __name__ == "__main__":
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
        options["save_image"] = ["ui", "websocket"]

        for prompt_text in prompts:
            opt = options.copy()
            if prompt_text.get("prompt") is None:
                workflows.append(prompt_text)  # native prompt
                continue
            prompt_text["lora_dir"] = "e:\\ai\\models\\lora"
            # print(json.dumps(prompt_text, indent=4, ensure_ascii=False))
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
