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
                        print(
                            f"Error happen line {i+1}, {error_info} {filename} {item}"
                        )
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


def search_files(directory, category, output_dir=OUTPUT_DIR):
    files = []
    if os.path.isdir(directory):
        files = os.listdir(directory)
    elif os.path.isfile(directory):
        file = os.path.basename(directory)
        directory = os.path.dirname(directory)
        files = [file]
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
    save_jsonl(texts, f"{output_dir}/{category}.jsonl")


def convert(path_or_file, output_dir):

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    if os.path.isdir(path_or_file):
        DIR = path_or_file
        # ディレクトリ一覧を取得
        files = os.listdir(DIR)
        for file in files:
            # directory?
            if os.path.isdir(f"{DIR}/{file}"):
                search_files(f"{DIR}/{file}", file, output_dir)
    else:
        basename = os.path.basename(path_or_file).split(".")[0]
        search_files(path_or_file, basename, output_dir)
        files = path_or_file

    # 表示する
    print(files)


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
                print(f"Error happen line {idx+1}, {file} {item}")
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


def sort_jsonl(files, keys, rebulid=False, expand=False, append=False):
    if isinstance(keys, str):
        keys = [keys]
    for file in files:
        with open(file, "r", encoding="utf_8") as f:
            data = f.readlines()
        items = []
        comment_mode = False
        for idx, item in enumerate(data):
            # //   がある場合はコメントとして処理
            try:
                comment = item.split("//")
                if len(comment) == 1:
                    items.append(json.loads(item))
                else:
                    items.append(json.loads(comment[0]))
            except Exception as e:
                print(f"Wornig: line{idx+1} {e}")
        # sort of key data
        for key in keys:
            print(f"sort {key}")
            # Vの場合は、arrayの場合[0]、array以外はそのまま
            if key == "V":
                items.sort(
                    key=lambda x: x[key][0] if isinstance(x[key], list) else x[key]
                )
            else:
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
                if "series" in item:
                    copy_item["series"] = item["series"]
                    del item["series"]
                if "title" in item:
                    copy_item["title"] = item["title"]
                    del item["title"]
                if "lora" in item:
                    copy_item["lora"] = item["lora"]
                    del item["lora"]
                if "prompt" in item:
                    copy_item["prompt"] = item["prompt"]
                    del item["prompt"]
                    if "append" in item:
                        copy_item["append"] = item["append"]
                        del item["append"]
                    else:
                        copy_item["append"] = ""
                if append:
                    if copy_item["append"] == "":
                        if len(item["V"]) > 1:
                            copy_item["append"] = item["V"][1]
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
                if expand:
                    for v in item["V"]:
                        new_prompt = v
                        copy_item["prompt"] = new_prompt
                        f.write(json.dumps(copy_item, ensure_ascii=False) + "\n")
                else:
                    f.write(json.dumps(copy_item, ensure_ascii=False) + "\n")


def check_jsonl(files, keys):
    # // がある場合はコメントとして処理
    for file in files:
        items = {}
        for key in keys:
            items[key] = {}
        print(items)
        with open(file, "r", encoding="utf_8") as f:
            data = f.readlines()
        log_file = file.replace(".jsonl", "-log.jsonl")
        with open(log_file, "w", encoding="utf_8") as f:
            for idx, item in enumerate(data):
                try:
                    comment = item.split("//")
                    if len(comment) >= 2:
                        item = json.loads(comment[0])
                        comment = comment[1]
                    else:
                        item = json.loads(item)
                        comment = ""
                except Exception as e:
                    print(f"Wornig: line{idx+1} {e}")
                if not isinstance(comment, str):
                    comment = ""
                if isinstance(item, str):
                    print(f"Error: line{idx+1} {item} is str")
                    continue
                # prompt が存在する場合 V[0]に入れる
                if "prompt" in item:
                    if item.get("V") is None:
                        item["V"] = [item["prompt"]]
                    elif isinstance(item["V"], list):
                        item["V"][0] = item["prompt"]
                    elif isinstance(item["V"], str):
                        item["V"] = [item["prompt"]]
                for key in keys:
                    if item[key] is not None:
                        if isinstance(item[key], list):
                            _key = item[key][0]
                        else:
                            _key = item[key]
                        if _key is None:
                            continue
                        if items[key].get(_key) is None:
                            items[key][_key] = idx + 1
                        else:
                            comment += f' duplicate: line:{items[key][_key]} {idx+1} {key} "{_key}"'

                f.write(json.dumps(item, ensure_ascii=False))
                if comment != "":
                    f.write(" // " + comment + "\n")
                else:
                    f.write("\n")


def usage():
    print("Usage: python txt2jsonl.py convert txtfile|dir output_dir")
    print(
        "       python txt2jsonl.py [format|lora|sort|rebuild|expand|append] [filename, filename, ...]"
    )
    sys.exit(1)


argv = sys.argv
if len(argv) < 3:
    usage()

if argv[1] == "convert":
    if len(argv) < 4:
        usage()
    convert(argv[2], argv[3])
elif argv[1] == "lora":
    jsonl2jsonl(argv[2:], True)
elif argv[1] == "format":
    jsonl2jsonl(argv[2:])
elif argv[1] == "sort":
    sort_jsonl(argv[2:], ["prompt", "V", "C"], False)
elif argv[1] == "rebuild":
    sort_jsonl(argv[2:], "C", rebulid=False)
elif argv[1] == "expand":
    sort_jsonl(argv[2:], ["title", "C"], expand=True)
elif argv[1] == "append":
    sort_jsonl(argv[2:], ["title", "C"], append=True)
elif argv[1] == "check":
    check_jsonl(argv[2:], ["prompt"])
else:
    print("error: invalid command use [convert, format, lora, sort, rebuild]")
    usage()
