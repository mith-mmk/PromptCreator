import asyncio
import base64
import io
import json
import os
import re
import threading
from datetime import datetime
from hashlib import sha256
from operator import ge
from zoneinfo import ZoneInfo

import aiofiles.os as aos
from PIL import Image, PngImagePlugin

import modules.api as api

# import modules.queing as queing
from modules.logger import getDefaultLogger
from modules.parse import create_parameters

Logger = getDefaultLogger()


class DataSaver:
    def __init__(self):
        self.thread = None

    def save_images(self, r, opt={"dir": "./outputs"}):
        import copy

        opt = copy.deepcopy(opt)
        if self.thread is not None:
            self.thread.join()
        self.thread = threading.Thread(target=save_images_wapper, args=(r, opt))
        self.thread.start()

    async def asave_images(self, r, opt={"dir": "./outputs"}):
        return await async_save_images(r, opt=opt)

    def save(self, filename, data):
        with open(filename, "wb") as f:
            f.write(data)

    def save_text(self, filename, data):
        with open(filename, "w", encoding="utf-8") as f:
            f.write(data)

    def __del__(self):
        if self.thread is not None:
            self.thread.join()


def save_images(r, opt={"dir": "./outputs"}):
    return asyncio.run(async_save_images(r, opt=opt))
    # if opt.get("multithread", False):
    # return save_images_thread(r, opt)


# async queueが上手くいかないからThread
def save_images_thread(r, opt={"dir": "./outputs"}):
    # 参照渡しなので、コピーして渡さないと処理中に中身が変わる（スレッドセーフではない）
    import copy

    opt = copy.deepcopy(opt)
    t = threading.Thread(target=save_images_wapper, args=(r, opt))
    t.start()
    return t


def save_images_wapper(r, opt={"dir": "./outputs"}):
    # async にすると2割ぐらい速くなる（みたい）
    asyncio.run(async_save_images(r, opt=opt))


async def create_files(r, opt={"dir": "./outputs"}):
    dir = opt["dir"]

    nameseed = opt.get("filename_pattern", "[num]-[seed]")
    need_names = re.findall(r"\[.+?\]", nameseed)
    need_names = [n[1:-1] for n in need_names]
    #    before_counter = re.sub(r"\[num\].*", "", nameseed)
    #    before_counter = re.sub(r"\[.*?\]", "", before_counter)
    #    count = len(before_counter)
    use_num = False
    for name in need_names:
        if name == "num":
            use_num = True
            break
    #    count = search_num_start(nameseed, use_num)
    Logger.debug("need_names", need_names)

    #    if "startnum" in opt:
    #        num = opt["startnum"]
    #    else:
    #        start_time = datetime.now()
    #        num = number_of_files(dir, count)
    #        end_time = datetime.now()
    #        Logger.debug("scan time", end_time - start_time)

    if type(r["info"]) is str:
        info = json.loads(r["info"])
    else:
        info = r["info"]
    Logger.debug("info", info)

    filename_pattern = {}

    variables = get_variables(opt)

    attributes = opt.get("attributes", opt.get("verbose", {}).get("attributes", {}))
    for key, value in info.items():
        filename_pattern[key] = value

    for key, value in variables.items():
        if type(value) is list:  # for multi value
            try:
                filename_pattern["var:" + key] = value[0]
                for n, v in enumerate(value):
                    filename_pattern["var:" + key + "(" + str(n + 1) + ")"] = v
            except Exception as e:
                Logger.verbose(f"create filenames - check multi value error {value}")
        else:
            filename_pattern["var:" + key] = value
    filename_pattern["part"] = opt.get("filepart", "")

    if attributes:
        for key, value in attributes.items():
            # it's dict
            for k, v in value.items():
                filename_pattern["var:" + key + ":" + k] = v
    if "info" in opt:
        for key, value in opt["info"].items():
            if type(key) is str:
                if type(value) is list:
                    value = value[0]  # only first value
                filename_pattern["info:" + key] = value

    if "command" in opt:
        for key, value in opt["command"].items():
            if type(key) is str:
                filename_pattern["command:" + key] = value

    Logger.debug(
        "filename_pattern", json.dumps(filename_pattern, ensure_ascii=False, indent=2)
    )
    num = 0  # disipose return value
    return filename_pattern, need_names, num, nameseed


def search_num_start(filname_base, use_num=False):
    if not use_num:
        return 0
    need_names = re.findall(r"\[.+?\]", filname_base)
    need_names = [n[1:-1] for n in need_names]
    count = 0
    for name in need_names:
        if name == "num":
            return count
        else:
            count += 1
    # if not found num
    return 0


def number_of_files(dir, count=0):
    num = -1
    if not os.path.exists(dir):
        return 0
    for entry in os.scandir(dir):
        parts = entry.name.split("-")
        if parts[count].isdigit():
            num = max(num, int(parts[count]))
    num += 1
    return num


async def async_save_images(r, opt={"dir": "./outputs"}):
    import copy

    Logger.debug("deepcopy opt")
    opt = copy.deepcopy(opt)
    Logger.debug("aysnc_save_images")
    try:
        filename_pattern, need_names, num, nameseed = await create_files(r, opt)
    except Exception as e:
        Logger.error("create_files error", e)
        raise e
    dir = opt["dir"]

    variables = get_variables(opt)
    count = len(r["images"])
    Logger.stdout(f"\033[Kreturn {count} images")
    if isinstance(r["info"], str):
        info = json.loads(r["info"])
    else:
        info = r["info"]

    Logger.debug("info", info)
    Logger.verbose("save images", len(r["images"]))

    for n, i in enumerate(r["images"]):
        Logger.verbose(
            f"save image {n + 1} of {len(r['images'])}, {len(info['infotexts'])}"
        )
        try:
            Logger.debug("save", n)
            try:
                if n >= len(info["infotexts"]):
                    if not opt.get("cn_save_pre"):
                        Logger.verbose("infotexts is not enough")
                        break
                    meta = ""
                else:
                    meta = info["infotexts"][n]
            except Exception as e:
                Logger.warning("infotexts error", e)
                meta = info["infotexts"][n]
            if isinstance(i, str):
                image = Image.open(io.BytesIO(base64.b64decode(i)))
            else:
                image = Image.open(io.BytesIO(i))
            parameters = create_parameters(meta)
            Logger.debug("parameters are", parameters)

            filename = create_filename(
                nameseed, num, filename_pattern, need_names, parameters, opt
            )
            Logger.debug("filename is", filename)
            print("\033[Ksave... ", filename)
            filename = os.path.join(dir, filename)
            dirname = os.path.dirname(filename)
            Logger.debug("dirname", dirname)
            if dirname != dir:
                await aos.makedirs(dirname, exist_ok=True)
            num += 1
            if "num_once" in opt:
                opt["startnum"] = num
            # extendend_meta is expantion meta data for this app
            # vae, model_name, filename_pattern, command options, variables, info, command

            extendend_meta = get_extendmeta(meta, variables, opt)
            image_save(image, filename, meta, extendend_meta, opt)

        except KeyboardInterrupt:
            Logger.error("Process stopped Ctrl+C break")
            raise KeyboardInterrupt
        except BaseException as e:
            Logger.error("save error", e, filename)
            # raise e
    #    opt['startnum'] = num
    return len(r["images"])


def get_variables(opt):

    variables = {}
    if "verbose" in opt:
        Logger.debug(
            "verbose", json.dumps(opt["verbose"], ensure_ascii=False, indent=2)
        )
        for key, value in (
            opt["verbose"].get("values", opt["verbose"].get("variables", {})).items()
        ):
            variables[key] = value
    elif "values" in opt:
        Logger.debug("values", json.dumps(opt["values"], ensure_ascii=False, indent=2))
        for key, value in opt["values"].items():
            variables[key] = value
    elif "variables" in opt:
        Logger.debug(
            "variables", json.dumps(opt["variables"], ensure_ascii=False, indent=2)
        )
        var = re.compile(r"\$\{(.+?)\}")
        for key, value in opt["variables"].items():
            Logger.debug("variable", key, value)
            if type(value) is list:
                value = value[0]
            value = str(value)
            match = var.search(value)
            max_loop = 100
            count = 0
            while match is not None and count < max_loop:
                count += 1
                for new_key in match.groups():
                    if new_key in opt["variables"]:
                        new_value = opt["variables"][new_key]
                        if type(new_value) is list:
                            new_value = new_value[0]
                        try:
                            value = value.replace("${%s}" % (new_key), new_value)
                        except Exception as e:
                            Logger.error(
                                f"key replace error variables {new_key} {new_value} {e}"
                            )
                    else:
                        try:
                            value = value.replace("${%s}" % (new_key), "")
                        except Exception as e:
                            Logger.error(
                                f"key replace error value, new key {value} {new_key} {e}"
                            )
                match = var.search(value)
            variables[key] = value
    return variables


def create_filename(nameseed, num, filename_pattern, need_names, parameters, opt={}):
    filename = nameseed + ".png"
    if opt.get("image_type") == "jpg":
        filename = nameseed + ".jpg"
    elif opt.get("image_type") == "webp":
        filename = nameseed + ".webp"

    for seeds in need_names:
        replacer = ""
        if seeds == "num":
            replacer = "[num]"  # after repalce
        # elif seeds == "seed" and "all_seeds" in filename_pattern:
        #    replacer = filename_pattern["all_seeds"][n]
        # elif seeds == "subseed" and "all_subseeds" in filename_pattern:
        #    replacer = filename_pattern["all_subseeds"][n]
        elif seeds == "styles" and seeds in filename_pattern:
            replacer = filename_pattern[seeds].join(" ")
        elif seeds == "DATE" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][:8]  # OLD Date
        elif seeds == "DATE":
            date = datetime.now()
            replacer = date.strftime("%Y%m%d")
        elif seeds == "date":
            date = datetime.now()
            replacer = date.strftime("%Y-%m-%d")  # Web UI Date
        elif seeds == "datetime" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"]
        elif re.match(r"datetime<.+?><.+?>", seeds):
            try:
                match = re.search(r"datetime<(.+)><(.+)>", seeds)
                if match is None:
                    replacer = "[" + seeds + "]"
                    continue
                date = datetime.now(tz=ZoneInfo(key=match.group(2)))
                replacer = date.strftime(match.group(1))
            except ValueError:
                replacer = "[" + seeds + "]"
        elif re.match(r"datetime<.+>", seeds):
            try:
                date = datetime.now()
                match = re.search(r"datetime<(.+)>", seeds)
                if match is None:
                    replacer = "[" + seeds + "]"
                    continue
                replacer = date.strftime(match.group(1))
            except ValueError:
                replacer = "[" + seeds + "]"
                replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\s]", "_", str(replacer))[:127]
        elif seeds == "shortdate" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][2:8]
        elif seeds == "year" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][:4]
        elif seeds == "shortyear" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][2:4]
        elif seeds == "month" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][4:6]
        elif seeds == "day" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][6:8]
        elif seeds == "time" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][8:]
        elif seeds == "hour" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][8:10]
        elif seeds == "min" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][10:12]
        elif seeds == "sec" and "job_timestamp" in filename_pattern:
            replacer = filename_pattern["job_timestamp"][12:14]
        elif seeds == "model_name":
            base_url = opt["base_url"]
            model = api.get_sd_model(base_url, parameters["model_hash"])
            replacer = model["model_name"] if model is not None else ""
        elif seeds == "prompt":
            replacer = parameters["prompt"]
            replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\s]", "_", str(replacer))[:127]
        elif seeds == "prompt_spaces":
            replacer = parameters["prompt"]
            replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\s]+", " ", str(replacer))[:127]
        elif seeds == "prompt_words":
            replacer = parameters["prompt"]
            replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+", " ", str(replacer))[
                :127
            ]
        elif seeds == "prompt_hash":
            replacer = sha256(parameters["prompt"].encode("utf-8")).hexdigest()[:8]
        elif seeds == "prompt_no_styles":
            replacer = filename_pattern["prompt"]
            replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+", "_", str(replacer))[
                :127
            ]
        elif seeds in parameters:
            replacer = parameters[seeds]
            replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+", "_", str(replacer))[
                :127
            ]
        # elif seeds in filename_pattern and type(filename_pattern[seeds]) is list:
        #    replacer = filename_pattern[seeds][n]
        #    replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\,\(\)\{\}]+", "_", str(replacer))[
        #        :127
        #    ]
        elif seeds in filename_pattern:
            replacer = filename_pattern[seeds]
            replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\s]", "_", str(replacer))[:127]
        else:
            replacer = "[" + seeds + "]"
            replacer = re.sub(r"[\<\>\:\"\/\\\\|?\*\n\s]", "_", str(replacer))[:127]
        try:
            filename = filename.replace("[" + seeds + "]", str(replacer))
        except Exception as e:
            Logger.error("replace error", e, filename, seeds, replacer)

    #            seed = filename_pattern['all_seeds'] [n]
    #            filename = str(num).zfill(5) +'-' +  str(seed) + '.png'
    filename = re.sub(r"\[.+?\:.+?\]", "", filename)

    filebase = os.path.basename(filename)
    dir = os.path.dirname(filename)
    # sarch "[num]"
    num_match = re.search(r"\[num\]", filebase)
    num_length = opt.get("num_length", 5)
    if num_match is not None:
        parts = filebase.split("-")
        if len(parts) > 1:
            for n, part in enumerate(parts):
                if "[num]" in part:
                    try:
                        num = number_of_files(os.path.join(opt["dir"], dir), count=n)
                    except Exception as e:
                        Logger.error("number_of_files error", e)
                        num = 0
                    filename = filename.replace("[num]", str(num).zfill(num_length))
                    break

    return filename


def get_extendmeta(meta, variables, opt):
    if opt.get("save_extend_meta"):
        extentend_meta = {}
        if "model_name" in opt:
            extentend_meta["model_name"] = opt["sd_model"]
        if "sd_vae" in opt:
            extentend_meta["vae_filename"] = opt["sd_vae"]
        if "filename_pattern" in opt:
            extentend_meta["filename_pattern"] = opt["filename_pattern"]
        if "command" in opt:
            extentend_meta["command"] = opt["command"]
        if "variables" in opt:
            extentend_meta["variables"] = variables
        if "verbose" in opt:
            extentend_meta["verbose"] = opt["verbose"]
        if "info" in opt:
            extentend_meta["info"] = opt["info"]
        extentend_meta["automatic1111"] = meta
        return json.dumps(extentend_meta)
    return None


def image_save(image, filename, meta, extendend_meta, opt={}):
    directory = os.path.dirname(filename)
    if not os.path.exists(directory):
        os.makedirs(directory, exist_ok=True)
    if opt.get("image_type") == "jpg":
        Logger.debug("save jpg", filename)
        quality = opt.get("image_quality", 80)
        Logger.debug("quality", quality)
        try:
            import piexif

            # piexif only uses big-endian in headers
            #   _dump.py:23 header = b"Exif\x00\x00\x4d\x4d\x00\x2a\x00\x00\x00\x08"
            # The exif specification does not define Unicode encoding types set in User Comment.
            # It does only define using Unicode Standard.
            # But some libiraies use UTF-16 and piexif uses big-endian, so I use UTF-16BE.
            bytes_text = bytes(meta, encoding="utf-16be")
            exif_dict = {
                "Exif": {
                    piexif.ExifIFD.UserComment: b"UNICODE\0" + bytes_text,
                }
            }
            if extendend_meta is not None:
                # XPComment is little-endian(UCS2LE ≒ UTF-16LE), It is defind by Microsoft.
                user_bytes = bytes(extendend_meta, encoding="utf-16le")
                exif_dict["0th"] = {}
                exif_dict["0th"][piexif.ImageIFD.XPComment] = user_bytes
            Logger.debug(exif_dict)
            exif_bytes = piexif.dump(exif_dict)
            image.save(filename, exif=exif_bytes, quality=quality)
        except ImportError:
            Logger.error("piexif not found")
            image.save(filename, quality=quality)
        Logger.debug("saved")
    elif opt.get("image_type") == "webp":
        import piexif

        quality = opt.get("image_quality", 80)
        bytes_text = bytes(meta, encoding="utf-16be")
        exif_dict = {
            "Exif": {
                piexif.ExifIFD.UserComment: b"UNICODE\0" + bytes_text,
            }
        }
        exif_bytes = piexif.dump(exif_dict)
        try:
            image.save(filename, "webp", exif=exif_bytes, quality=quality)
        except Exception as e:
            Logger.error("save webp error", e)
    else:
        Logger.debug("save png", filename)
        pnginfo = PngImagePlugin.PngInfo()
        pnginfo.add_text("parameters", meta)
        Logger.debug("parameters", meta)
        if "workflow" in opt:
            pnginfo.add_text("prompt", opt["workflow"])
        if extendend_meta is not None:
            pnginfo.add_text("expantion", extendend_meta)
        try:
            image.save(filename, pnginfo=pnginfo)
        except Exception as e:
            Logger.error("save png error", e)
    Logger.debug("saved")
