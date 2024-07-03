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

client_id = str(uuid.uuid4())


class ComfyUIWorkflow:
    def __init__(self, options={}):
        self.options = options
        self.checkpoint = None
        self.vae = None

    def setModel(self, model):
        self.checkpoint = model

    def setVAE(self, vae):
        self.vae = vae

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
        other_vae = False
        lora_matcher = re.compile(r"\<lora\:(.+?)\:([0-9\.]+)\>")
        postive_loras = lora_matcher.findall(prompt)
        prompt = lora_matcher.sub("", prompt)
        negative_loras = lora_matcher.findall(negative_prompt)
        negative_prompt = lora_matcher.sub("", negative_prompt)

        checkpoint = options.get("checkpoint", self.checkpoint or "None")
        if checkpoint == "None":
            raise ValueError("Checkpoint not set")
        vae = options.get("vae", self.vae or "None")

        seed = options.get("seed", -1)
        if seed == -1:
            seed = random.randint(0, 2**31 - 1)
        workflow = {}
        wf_num = 3
        base_width = 1024 if options.get("type") == "sdxl" else 512
        base_height = 1024 if options.get("type") == "sdxl" else 512

        workflow[str(wf_num)] = self.createEmptyLatentImage(
            {
                "batch_size": options.get("batch_size", 1),
                "height": options.get("height", base_height),
                "width": options.get("width", base_width),
            }
        )
        latent_from = str(wf_num)
        wf_num += 1
        workflow[str(wf_num)] = self.createLoadCheckpoint(checkpoint)
        model_from = str(wf_num)
        positive_clip_from = model_from
        negative_clip_from = model_from
        vae_from = model_from
        wf_num += 1
        if vae != "None":
            workflow[str(wf_num)] = self.createLoadVAE(vae)
            vae_from = str(wf_num)
            wf_num += 1
            other_vae = True

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
        workflow[str(wf_num)] = self.createCLIPTextEncode(
            negative_prompt, negative_clip_from
        )
        negative_from = str(wf_num)
        wf_num += 1

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
        workflow[str(wf_num)] = self.createEncodeVAE(sampler_from, vae_from, other_vae)
        encode_from = str(wf_num)
        wf_num += 1
        workflow[str(wf_num)] = self.createSaveImage(encode_from, options)
        wf_num += 1
        workflow["save_image_websocket_node"] = self.createSaveWebSocketImage(
            encode_from, options
        )
        return workflow


class ComufyClient:
    def __init__(self) -> None:
        self.client = httpx.AsyncClient()
        self.server_address = "127.0.0.1:8188"

    async def queue_prompt(self, prompt):
        p = {"prompt": prompt, "client_id": client_id}
        # print(json.dumps(p, indent=4))
        req = await self.client.post(
            "http://{}/prompt".format(self.server_address), json=p
        )
        if req.status_code != 200:
            raise Exception(req.text)
        return req.json()

    async def get_image(self, filename, subfolder, folder_type):
        data = {"filename": filename, "subfolder": subfolder, "type": folder_type}

        res = await self.client.post(
            "http://{}/get_image".format(self.server_address), json=data
        )
        return res.content

    async def get_history(self, prompt_id):
        res = await self.client.get(
            "http://{}/history/{}".format(self.server_address, prompt_id)
        )
        return res.json()

    async def get_images(self, ws, prompt):
        res = await self.queue_prompt(prompt)
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

    async def arun(self, prompts, options={}):
        client = ComufyClient()
        ws = websocket.WebSocket()
        ws.connect("ws://{}/ws?clientId={}".format(self.server_address, client_id))
        for prompt in prompts:
            images = await client.get_images(ws, prompt)

        # Commented out code to display the output images:

        for node_id in images:
            for image_data in images[node_id]:
                import datetime
                import io
                import os

                from PIL import Image

                image = Image.open(io.BytesIO(image_data))
                dirctory = options.get("save_dir", "outputs")
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
        for prompt_text in prompts:
            if prompt_text.get("prompt") is None:
                workflows.append(prompt_text)  # native prompt
                continue
            prompt_text["lora_dir"] = "e:\\ai\\models\\lora"
            # print(json.dumps(prompt_text, indent=4, ensure_ascii=False))
            prompt = prompt_text.get("prompt", "")
            prompt_text["sampler_name"] = "euler_ancestral"
            prompt_text["scheduler"] = "normal"
            negative_prompt = prompt_text.get("negative_prompt", "")
            workflow = wf.createWorkflow(prompt, negative_prompt, prompt_text)
            workflows.append(workflow)
            import time

            start_time = time.time()
            client = ComufyClient()
            client.run(workflows, {})
