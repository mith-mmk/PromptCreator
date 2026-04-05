#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import base64
import glob
import json
import os
import re
from io import BytesIO
from pathlib import Path

import httpx
import yaml
from PIL import Image

client = httpx.Client()

pattern = re.compile(r"\$\{(\w+)\}")
model = "gemma-4-e4b-it"
model = "qwen/qwen3.5-9b"
model = os.getenv("MODEL", model)
server_url = os.getenv("SERVER_URL") or os.getenv("SERVER") or "http://localhost:1234"
auth_token = os.getenv("AUTH_TOKEN", "")


def yaml_loader(filename):
    with open(filename, encoding="utf-8") as f:
        text = f.read()
    text = pattern.sub(lambda m: os.getenv(m.group(1), ""), text)
    return yaml.safe_load(text)


def decode_windows_filename(s: str) -> str:
    import urllib.parse

    s = s.replace("%252525", "%")
    s = s.replace("%2525", "%")
    return urllib.parse.unquote(s)


def check_image(path):
    img = Image.open(path)
    buffer = BytesIO()
    img.save(buffer, format="PNG")

    b64 = base64.b64encode(buffer.getvalue()).decode()
    message = "画像を評価してください。それぞれ0-100点までで判定してください。"

    headers = {"Authorization": f"Bearer {auth_token}"} if auth_token else {}

    response_format = {
        "type": "json_schema",
        "json_schema": {
            "name": "analysis_of_tag",
            "properties": {
                "human_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                },
                "background_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                },
                "total_score": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                },
                "buzz": {
                    "type": "number",
                    "minimum": 0,
                    "maximum": 100,
                },
                "notes": {"type": "strings"},
            },
            "required": ["human_score", "background_score", "total_score"],
            "additionalProperties": False,
        },
    }

    url = server_url + "/v1/chat/completions"

    json_data = {
        "model": model,
        "reasoning": {"effort": "low"},
        "messages": [
            {
                "role": "system",
                "content": """
                        あなたは画像解析機で、構造化されたイメージパーサーです。
                        You return data in JSON format, 
                        `human_score` は 人体描写に解剖学的な破綻がないかを0-100点で評価します
                        - 90-100: 完全に自然（破綻なし）
                        - 70-89: 軽微な違和感()
                        - 40-69: 明確な破綻あり(関節の曲がり具合など)
                        - 0-39: 深刻な破綻（指や手の数が多い、少ないなど）
                       
                        `background_score` は 背景描写に破綻がないかを0-100点で評価します
                        - 90-100: 完全に自然（破綻なし）
                        - 70-89: 軽微な違和感
                        - 40-69: 明確な破綻あり(線が歪んでいるなど)
                        - 0-39: 深刻な破綻（物体が歪んでいる、曲がっている、融合しているなど）                      
                        `total_score` は 全体の出来を0-100点で評価します
                        平均が50点になるように調子してください
                        `notes` は簡潔な日本語(Japanese)のみで返します
                     """,
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": message},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/png;base64,{b64}"},
                    },
                ],
                "response_format": response_format,
                "max_tokens": 1024,
            },
        ],
    }

    print("post server")

    res = client.post(
        url,
        json=json_data,
        headers=headers,
    )
    if res.status_code != 200:
        print(f"error {res.status_code}")
        return {"error": res.status_code}
    print(res)
    result = res.json()["choices"][0]["message"]["content"]
    jsoned = {}
    try:
        if type(result) == str:
            result = re.sub(r"^```json\s*", "", result.strip())
            result = re.sub(r"\s*```$", "", result)
            jsoned = json.loads(result)
            # print(type(jsoned))
    #        elif isinstance(result, dict):
    #            jsoned = result
    except Exception as err:
        print(f"parse error {result}")
        return {"error": "return not json", "text": result}, ""
    return jsoned, result


def create_table(image_file):
    image_file = Path(image_file)
    try:
        print(f"Check {image_file}")
        r, raw = check_image(image_file)
        raw = raw.replace("\n", "\\n")
    except Exception as e:
        r = {"error": e}
        raw = e
    human_score = r.get("human_score")  # type: ignore
    background_score = r.get("background_score")  # type: ignore
    score = r.get("total_score", "")  # type: ignore
    buzz = r.get("buzz", "")  # type: ignore
    notes = r.get("notes", "")  # type: ignore
    text = f'|{buzz}|{score}|{human_score}|{background_score}|{notes}|<img src="{image_file.name}" width="300">|'
    return text


def loader(path, outputfile):
    def text_saver(outputfile, text):
        file = os.path.join(outputfile, f"0000.md")
        print(f"output {file}")
        dir_path = os.path.dirname(file)
        os.makedirs(dir_path, exist_ok=True)
        with open(file, "w", encoding="utf-8") as fw:
            fw.write(text)

    import os

    files = []
    # kinds以下のwebpファイルを全て取得
    files += glob.glob(os.path.join(path, "*.jpg"))
    # print(files)
    pre_text = "- AIによる判定です(誤判定率高め)\n\n"
    pre_text += "|タグ|判定|注記||\n"
    pre_text += "|----|----|----|----|\n"
    text = ""
    files_no = len(files)
    print(f"check {files_no} files")
    for idx, file in enumerate(files):
        _str = create_table(file)
        text = text + _str + "\n"
        print(_str)

    text_saver(outputfile, text)


def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input folder", type=str)
    parser.add_argument(
        "output", help="output file", type=str, default="./test/image_check.md"
    )
    args = parser.parse_args()
    loader(args.input, args.output)


if __name__ == "__main__":
    main()
