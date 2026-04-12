#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import base64
import glob
import json
import os
import re
import ssl
import time
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from urllib.parse import urlsplit

import yaml
from PIL import Image

APP_ROOT = Path(__file__).resolve().parent

# model = "gemma-4-e4b-uncensored-hauhaucs-aggressive"
# server_url = "http://localhost:1234"
auth_token = os.getenv("AUTH_TOKEN", "")


@dataclass
class PreparedImage:
    path: Path
    filename: str
    notes: str
    error: bool
    image_url: str


@dataclass
class PrepareError:
    path: Path
    filename: str
    error: str


@dataclass
class CheckOutput:
    index: int
    item: PreparedImage | PrepareError
    result: dict
    raw: str
    text: str


pattern = re.compile(r"\$\{(\w+)\}")


def yaml_loader(filename):
    with open(filename, encoding="utf-8") as f:
        text = f.read()
    # text = pattern.sub(lambda m: os.getenv(m.group(1), ""), text)
    return yaml.safe_load(text)


def decode_windows_filename(s: str) -> str:
    import urllib.parse

    return urllib.parse.unquote(s)


def prepare_image(path, filename):
    path = Path(path)
    img = Image.open(path).convert("RGB")
    buffer = BytesIO()
    img.save(buffer, format="jpeg")
    b64 = base64.b64encode(buffer.getvalue()).decode()
    return PreparedImage(
        path=path,
        notes="",
        error=False,
        filename=filename,
        image_url=f"data:image/jpeg;base64,{b64}",
    )


async def prepare_image_async(path, filename):
    return await asyncio.to_thread(prepare_image, path, filename)


async def post_json(url: str, payload: dict, headers: dict, timeout: float = 120.0):
    parts = urlsplit(url)
    if parts.scheme not in {"http", "https"}:
        raise ValueError(f"unsupported scheme: {parts.scheme}")
    host = parts.hostname
    if not host:
        raise ValueError(f"missing host in URL: {url}")
    port = parts.port or (443 if parts.scheme == "https" else 80)
    target = parts.path or "/"
    if parts.query:
        target += f"?{parts.query}"

    body = json.dumps(payload).encode("utf-8")
    request_headers = {
        "Host": host if parts.port is None else f"{host}:{port}",
        "Content-Type": "application/json",
        "Content-Length": str(len(body)),
        "Connection": "close",
        "Accept": "application/json",
        **headers,
    }
    ssl_context = ssl.create_default_context() if parts.scheme == "https" else None

    reader, writer = await asyncio.wait_for(
        asyncio.open_connection(
            host,
            port,
            ssl=ssl_context,
            server_hostname=host if ssl_context else None,
        ),
        timeout=timeout,
    )
    try:
        request_text = [f"POST {target} HTTP/1.1\r\n"]
        request_text.extend(
            f"{key}: {value}\r\n" for key, value in request_headers.items()
        )
        request_text.append("\r\n")
        writer.write("".join(request_text).encode("utf-8") + body)
        await asyncio.wait_for(writer.drain(), timeout=timeout)

        status_line = await asyncio.wait_for(reader.readline(), timeout=timeout)
        if not status_line:
            raise RuntimeError("empty response")
        try:
            _, status_code_text, _ = (
                status_line.decode("iso-8859-1").rstrip("\r\n").split(" ", 2)
            )
            status_code = int(status_code_text)
        except Exception as exc:
            raise RuntimeError(f"invalid status line: {status_line!r}") from exc

        response_headers: dict[str, str] = {}
        while True:
            line = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if line in {b"\r\n", b"\n", b""}:
                break
            decoded = line.decode("iso-8859-1").rstrip("\r\n")
            if ":" not in decoded:
                continue
            key, value = decoded.split(":", 1)
            response_headers[key.strip().lower()] = value.strip()

        transfer_encoding = response_headers.get("transfer-encoding", "").lower()
        if transfer_encoding == "chunked":
            chunks: list[bytes] = []
            while True:
                size_line = await asyncio.wait_for(reader.readline(), timeout=timeout)
                size_text = size_line.decode("iso-8859-1").strip().split(";", 1)[0]
                size = int(size_text, 16)
                if size == 0:
                    await asyncio.wait_for(reader.readline(), timeout=timeout)
                    break
                chunks.append(
                    await asyncio.wait_for(reader.readexactly(size), timeout=timeout)
                )
                await asyncio.wait_for(reader.readexactly(2), timeout=timeout)
            body_text = b"".join(chunks).decode("utf-8", errors="replace")
        else:
            content_length = response_headers.get("content-length")
            if content_length is not None:
                body_bytes = await asyncio.wait_for(
                    reader.readexactly(int(content_length)), timeout=timeout
                )
            else:
                body_bytes = await asyncio.wait_for(reader.read(), timeout=timeout)
            body_text = body_bytes.decode("utf-8", errors="replace")

        return status_code, body_text
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def check_image(yml, prepared: PreparedImage):
    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    variables = yml.get("variables", {})
    variables["image_url"] = prepared.image_url
    variables["model"] = yml["model"]

    prompt = yml.get("prompt", "{}")
    prompt = pattern.sub(lambda m: variables.get(m.group(1), ""), prompt)
    try:
        prompt = json.loads(prompt)
    except Exception as e:
        print("prompt error:", e)
        exit(1)
    url = yml["server_url"] + "/v1/chat/completions"

    status_code, body = await post_json(url, prompt, headers, timeout=120.0)
    if status_code != 200:
        try:
            payload = json.loads(body)
        except Exception:
            payload = body
        print(status_code, payload)
        return {"error": status_code}, f"error {status_code}"
    response = json.loads(body)
    result = response["choices"][0]["message"]["content"]
    jsoned = {}
    try:
        if type(result) == str:
            result = re.sub(r"^```json\s*", "", result.strip())
            result = re.sub(r"\s*```$", "", result)
            jsoned = json.loads(result)
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception:
        print(f"parse error {result}")
        return {"error": "return not json", "text": result}, ""
    return jsoned, result


def create_table(prepared: PreparedImage, result, raw):
    filename = Path(prepared.filename).name
    raw = raw.replace("\n", "\\n")
    notes = result.get("notes", "")  # type: ignore
    score = result.get("score", "")  # type: ignore
    error = "👎" if result.get("error", True) else "👍"
    text = f'|<img loading="lazy"  width="256" src="{filename}">|{error}|{score}|{notes}<!--{raw}-->|'
    return text


def parse_file_metadata(file: str):
    return Path(file)


tick_time = 2.0  # s
program_started_at = time.time()


async def process_file(index, file, yml, sem):
    path = parse_file_metadata(file)
    progress_label = f"t{index % max(int(yml.get('threads', 4)), 1)}"
    started_at = time.time()
    try:
        prepared = await prepare_image_async(path, file)
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as exc:
        item = PrepareError(path, file, str(exc))
        print(f"{progress_label} {index}: preprocess error: {item.error}")
        return CheckOutput(index, item, {"error": "preprocess"}, f"error {exc}", "")

    try:
        async with sem:
            result, raw = await check_image(yml, prepared)
    except KeyboardInterrupt:
        raise KeyboardInterrupt
    except Exception as exc:
        result, raw = {"error": str(exc)}, f"error {exc}"
        print(f"error: {index} {str(exc)}")
    text = create_table(prepared, result, raw)
    elapsed_from_start = time.time() - program_started_at
    elapsed_for_file = time.time() - started_at
    print(
        f"{elapsed_from_start:.3f}s since start, "
        f"+{elapsed_for_file:.3f}s {progress_label} {index}: {prepared.filename}"
    )
    return CheckOutput(index, prepared, result, raw, text)


async def collect_tick_tack_results(yml, files):
    thread_number = max(int(yml.get("threads", 4)), 1)
    sem = asyncio.Semaphore(thread_number)
    tasks = [
        asyncio.create_task(process_file(index, file, yml, sem))
        for index, file in enumerate(files)
    ]
    results = await asyncio.gather(*tasks)
    return sorted(results, key=lambda x: x.index)


def loader(yml, path):
    def text_saver(file, text):
        print(f"output {file}")
        dir_path = os.path.dirname(file)
        os.makedirs(dir_path, exist_ok=True)
        with open(file, "w", encoding="utf-8") as fw:
            fw.write(text)

    outputfile = yml.get("output", os.path.join(path + "index.md"))

    webp = glob.glob(os.path.join(path, "*.webp"))
    png = glob.glob(os.path.join(path, "*.png"))
    jpeg = glob.glob(os.path.join(path, "*.jpg"))

    files = [] + webp + png + jpeg
    files = sorted(files, key=lambda x: x.split("-")[0])
    if not files:
        return
    pre_text = "- AIによる判定です(誤判定率高め)\n\n"
    pre_text += "|画像|チェック|スコア|ノート|\n"
    pre_text += "|----|----|----|----|\n"
    text = "# " + path + "\n"
    text += pre_text
    print(f"check {len(files)} files")
    for idx, item in enumerate(asyncio.run(collect_tick_tack_results(yml, files))):
        if isinstance(item.item, PrepareError):
            print(
                f"{idx+1}/{len(files)}, {files[idx]} preprocess error: {item.item.error}"
            )
            text += f"|||{item.item.filename}<!-- {item.item.error} -->|\n"
            continue
        print(f"{idx+1}/{len(files)},{item.item.filename}")
        print(item.text)
        text += item.text + "\n"
        text_saver(outputfile, text)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("path", help="input directory")
    parser.add_argument(
        "--config",
        type=str,
        default="../prompts/image_checker.yaml",
        help="yaml config path",
    )
    args = parser.parse_args()
    config_path = Path(args.config)
    if not config_path.is_absolute():
        config_path = (APP_ROOT / config_path).resolve()
    yml = yaml_loader(config_path)
    yml["model"] = yml.get("model", "gemma-4-e4b-it")  # type: ignore
    yml["server_url"] = yml.get("server", "http://localhost:1234")  # type: ignore
    try:
        loader(yml, args.path)
    except KeyboardInterrupt:
        raise KeyboardInterrupt


if __name__ == "__main__":
    main()
