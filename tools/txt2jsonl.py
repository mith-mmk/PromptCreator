import json
import os
import re
import sys

OUTPUT_DIR = "$jsonl/temp"


def item_split_txt(item, error_info="", default_weight=0.1):
    # comment
    if re.search(r"^\s*\#.*$", item):
        # 最初の#を // に変換
        item = item.replace("#", "//", 1)
        return {"comment": item}
    if type(item) is not str:
        return {"variables": [str(item)], "weight": default_weight}
    item = item.replace("\n", " ").strip().replace(r"\;", r"${semicolon}")
    split = item.split(";")

    if type(split) is list:
        for i in range(0, len(split)):
            split[i] = split[i].replace(r"${semicolon}", ";")
    try:
        weight = float(split[0])
        if len(split) == 1:
            return {"weight": default_weight, "variables": [weight]}
    except ValueError:
        weight = default_weight
        return {"weight": weight, "variables": split}
    variables = split[1:]
    return {"weight": weight, "variables": variables}


def read_file_v2(filename, error_info=""):
    strs = []
    filenames = filename.split()
    for filename in filenames:

        try:
            with open(filename, "r", encoding="utf_8") as f:
                for i, item in enumerate(f.readlines()):
                    try:
                        item = item_split_txt(item, error_info, 0.1)
                        strs.append(item)
                    except Exception:
                        print(f"Error happen line {error_info} {filename} {i} {item}")
        except FileNotFoundError:
            raise FileNotFoundError
    return strs


def convert_txt2jsonl(texts):
    data = []
    for text in texts:
        data.append(read_file_v2(text))
    return data


def save_jsonl(data, filename):
    with open(filename, "w", encoding="utf_8") as f:
        for item in data:
            if "W" not in item:
                if "comment" in item:
                    comment = item["comment"]
                    f.write(comment + "\n")
                continue
            # "W" "V" その他 "C" の順番でdump
            # formatの文字列は ''ではなく""で括る
            output_json = {}
            output_json["W"] = item["W"]
            output_json["C"] = item["C"]
            del item["W"]
            del item["C"]
            comment = item.get("comment", "")
            if comment is not None:
                if item.get("comment") is not None:
                    del item["comment"]
            for key in item.keys():
                output_json[key] = item[key]
            f.write(json.dumps(output_json, ensure_ascii=False) + comment + "\n")


def search_files(directory, category):
    files = os.listdir(directory)
    texts = []
    print(f"category: {category}")
    for file in files:
        if os.path.isdir(f"{directory}/{file}"):
            search_files(f"{directory}/{file}", category + "-" + file)
        else:
            basename = os.path.basename(file).split(".")[0]
            print(f"file: {file}")
            if file.endswith(".txt"):
                new_texts = read_file_v2(f"{directory}/{file}", category + "-" + file)

                for text in new_texts:
                    if "comment" in text:
                        texts.append(text)
                        continue
                    text["C"] = [basename]
                    text["W"] = text["weight"]
                    del text["weight"]
                    text["V"] = text["variables"]
                    del text["variables"]
                    texts.append(text)
    #  jsonl ファイルに変換
    save_jsonl(texts, f"{OUTPUT_DIR}/{category}.jsonl")


def convert(DIR):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # ディレクトリ一覧を取得
    files = os.listdir(DIR)
    for file in files:
        # directory?
        if os.path.isdir(f"{DIR}/{file}"):
            search_files(f"{DIR}/{file}", file)

    # 表示する
    print(files)


def jsonl2jonsl(files):
    # jsonl ファイルを読み込む
    for file in files:
        with open(file, "r", encoding="utf_8") as f:
            data = f.readlines()
        for idx, item in enumerate(data):
            item = json.loads(item)
            val = item["V"]
            length = len(val)
            # prompt = val[0]
            # negative = val[1]
            # height = val[2]
            # width = val[3]
            # scale = val[4]
            if length > 1:
                item["prompt"] = val[0]
            if length > 2:
                item["negative"] = val[1]
            if length > 3:
                item["height"] = val[2]
            if length > 4:
                item["width"] = val[3]
            if length > 5:
                item["scale"] = val[4]
            del item["V"]
            item["V"] = val[0]
            data[idx] = item
        # save new jsonl file
        new_filename = file.replace(".jsonl", "-new.jsonl")
        with open(new_filename, "w", encoding="utf_8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")


def jsonl2jsonl(files, islora=False):
    for file in files:
        print(file)
        data = []
        outdata = []
        with open(file, "r", encoding="utf_8") as f:
            data = f.readlines()
        for idx, item in enumerate(data):
            # //
            comment = item.split("//")
            try:
                # コメントがない場合
                if len(comment) == 1:
                    item = json.loads(comment[0])
                    item["comment"] = ""
                else:
                    item = json.loads(comment[0])
                    item["comment"] = "//" + comment[1]
            except json.JSONDecodeError:
                continue
            # "W"  "C" その他 "V" の順番でdump
            output_json = {}
            output_json["W"] = item["W"]
            output_json["C"] = item["C"]
            if islora:
                output_json["title"] = item["V"][0]
                prompt = item["V"][1]
                if len(item["V"]) > 2:
                    neg = item["V"][2]
                else:
                    neg = ""
                # promptから<lora::> を抽出
                lora = re.search(r"<lora\:.+?\:.*?>", prompt)
                if lora:
                    lora = lora.group()
                    prompt = prompt.replace(lora, "")

            del item["W"]
            del item["C"]
            if islora:
                output_json["lora"] = lora
                output_json["prompt"] = prompt
                output_json["neg"] = neg

            # その他のデータをソートして追加
            for key in sorted(item.keys()):
                output_json[key] = item[key]
            outdata.append(output_json)
        # save new jsonl file
        new_filename = file.replace(".jsonl", "-new.jsonl")
        save_jsonl(outdata, new_filename)


def sort_jsonl(files, keys, rebulid=False):
    if isinstance(keys, str):
        keys = [keys]
    for file in files:
        with open(file, "r", encoding="utf_8") as f:
            data = f.readlines()
        items = []
        for idx, item in enumerate(data):
            # //   がある場合はコメントとして処理
            try:
                comment = item.split("//")
                if len(comment) == 1:
                    items.append(json.loads(item))
                else:
                    items.append(json.loads(item))
            except Exception as e:
                print(f"Wornig: line{idx} {e}")
        # sort of key data
        for key in keys:
            items.sort(key=lambda x: x[key])
        # save new jsonl file
        new_filename = file.replace(".jsonl", "-new.jsonl")
        with open(new_filename, "w", encoding="utf_8") as f:
            for item in items:
                copy_item = {}
                copy_item["W"] = item["W"]
                copy_item["C"] = item["C"]
                del item["W"]
                del item["C"]
                if "comment" in item:
                    del item["comment"]
                if "title" in item:
                    copy_item["title"] = item["title"]
                    del item["title"]
                if "lora" in item:
                    copy_item["lora"] = item["lora"]
                    del item["lora"]
                if "prompt" in item:
                    copy_item["prompt"] = item["prompt"]
                    del item["prompt"]
                if "neg" in item:
                    copy_item["neg"] = item["neg"]
                    del item["neg"]
                else:
                    copy_item["neg"] = ""
                for key in item.keys():
                    copy_item[key] = item[key]
                if rebulid:
                    if "prompt" in copy_item and "title" in copy_item:
                        del copy_item["V"]
                        copy_item["V"] = [
                            copy_item["title"],
                            f"{copy_item['prompt']}f{copy_item['lora']}",
                            copy_item["neg"],
                        ]
                f.write(json.dumps(copy_item, ensure_ascii=False) + "\n")


def usage():
    print("Usage: python txt2jsonl.py convert [dir]")
    print(
        "       python txt2jsonl.py [format|lora|sort|rebuild] [filename, filename, ...]"
    )
    sys.exit(1)


argv = sys.argv
if len(argv) < 3:
    usage()

if argv[1] == "convert":
    convert(argv[2])
elif argv[1] == "lora":
    jsonl2jsonl(argv[2:], True)
elif argv[1] == "format":
    jsonl2jsonl(argv[2:])
elif argv[1] == "sort":
    sort_jsonl(argv[2:], ["title", "C"], False)
elif argv[1] == "rebuild":
    sort_jsonl(argv[2:], "C", False)
else:
    print("error: invalid command use [convert, format, lora, sort, rebuild]")
    usage()
