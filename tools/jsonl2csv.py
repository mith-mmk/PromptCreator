# python tools/jsonl2csv.py [input_dir] [output_file]

import csv
import json
import os
import re


def load_jsonl(input_file):
    with open(input_file, "r", encoding="utf-8") as f:
        all_text = f.read()
    all_text = re.sub(r"/\*.*?\*/", "", all_text, flags=re.DOTALL)
    lines = all_text.split("\n")
    data = []
    for idx, line in enumerate(lines):
        org_line = line
        line = re.sub(r"\s*//.*", "", line)
        line = line.strip()
        if not line:
            continue
        try:
            data.append(json.loads(line))
        except json.JSONDecodeError:
            print(f"Error in {input_file}: {idx}: {org_line}")
    return data


def grab_jsonl(input_dir):
    data = os.listdir(input_dir)
    files = []
    for i in range(len(data)):
        file = data[i]
        file = os.path.join(input_dir, file)
        print(file)
        if os.path.isdir(file):
            ret = grab_jsonl(file)
            files.extend(ret)
        elif file.endswith(".jsonl"):
            files.append(file)
    return files


def jsonl2csv(input_dir, output_file, bom=False, args={}):
    with open(output_file, "w", encoding="utf-8") as csvfile:
        if bom:
            csvfile.write("\ufeff")
        writer = csv.writer(csvfile, lineterminator="\n")
        files = grab_jsonl(input_dir)
        if args.expand:
            writer.writerow(
                [
                    "subject",
                    "choice",
                    "weight",
                    "title",
                    "lora",
                    "prompt",
                    "append",
                    "neg",
                    "variable1",
                    "variable2",
                    "variable3",
                    "variable4",
                    "variable5",
                    "variable6",
                    "variable7",
                    "variable8",
                    "multipy",
                    "width",
                    "height",
                    "attirbutes",
                    "comment",
                ]
            )
        else:
            writer.writerow(
                [
                    "subject",
                    "choice",
                    "weight",
                    "title",
                    "lora",
                    "prompt",
                    "append",
                    "neg",
                    "variables",
                    "multipy",
                    "width",
                    "height",
                    "attirbutes",
                    "comment",
                ]
            )
        for file in files:
            data = load_jsonl(file)
            subject = (
                file.replace(input_dir, "")
                .replace("/", "-")
                .replace("\\", "-")
                .replace(".jsonl", "")
                .strip("-")
            )
            print(f"output {subject}")
            for item in data:
                choice = item["C"] or item.get("choice", [])
                if isinstance(choice, list):
                    for i in range(len(choice)):
                        if isinstance(choice[i], dict):
                            choice[i] = str(choice[i])
                        choice[i] = str(choice[i])
                    choice = ",".join(choice)
                weight = item["W"] or item.get("weight", 1.0)
                if args.expand:
                    variables = item.get("V", []) or item.get("variables", [])
                    if isinstance(variables, str):
                        variables = [variables]
                    else:
                        variables = variables.copy()
                    for i in range(9 - len(variables)):
                        variables.append("")
                    print(variables)
                    prompt = (
                        item.get("prompt", "") or item.get("do", variables[0]) or ""
                    )
                else:
                    variables = item.get("V") or item.get("variables", [])
                    if isinstance(variables, str):
                        variable = variables.split(";")[0]
                    elif isinstance(variables, list):
                        if len(variables) > 0:
                            variable = variables[0]
                        else:
                            variable = ""
                    else:
                        variable = ""
                    prompt = item.get("prompt", "") or item.get("do", variable) or ""
                lora = item.get("lora", "")
                loras_in_prompt = re.findall(r"\[lora\](.*?)\[/lora\]", prompt)
                for lora_in_prompt in loras_in_prompt:
                    prompt = prompt.replace(lora_in_prompt, " ")
                prompt.strip()
                lora = lora + " ".join(loras_in_prompt)
                width = item.get("width", "")
                height = item.get("height", "")
                if not args.expand:
                    if isinstance(variables, list):
                        variables = ";".join(variables)
                attributes = {}
                for key in item.keys():
                    if key not in [
                        "C",
                        "W",
                        "V",
                        "choice",
                        "lora",
                        "weight",
                        "variables",
                        "title",
                        "prompt",
                        "do",
                        "append",
                        "neg",
                        "width",
                        "height",
                        "multiply",
                        "comment",
                    ]:
                        attributes[key] = item[key]

                if args.expand:
                    writer.writerow(
                        [
                            subject,
                            choice,
                            weight,
                            item.get("title", ""),
                            item.get("lora", ""),
                            prompt,
                            item.get("append", ""),
                            item.get("neg", ""),
                            variables[0],
                            variables[1],
                            variables[2],
                            variables[3],
                            variables[4],
                            variables[5],
                            variables[6],
                            variables[7],
                            item.get("multiply", ""),
                            width,
                            height,
                            json.dumps(attributes, ensure_ascii=False),
                            item.get("comment", ""),
                        ]
                    )
                else:

                    writer.writerow(
                        [
                            subject,
                            choice,
                            weight,
                            item.get("title", ""),
                            item.get("lora", ""),
                            prompt,
                            item.get("append", ""),
                            item.get("neg", ""),
                            variables,
                            item.get("multiply", ""),
                            width,
                            height,
                            json.dumps(attributes, ensure_ascii=False),
                            item.get("comment", ""),
                        ]
                    )


def csv2jsonl(filename, ouput_dir, bom=False, args={}):
    utf8 = "utf-8"
    if bom:
        utf8 = "utf-8-sig"
    with open(filename, "r", encoding=utf8) as csvfile:
        reader = csv.reader(csvfile)
        header = next(reader)
        mapper = {}
        all_data = {}
        for i in range(len(header)):
            mapper[header[i]] = i
        subject_idx = mapper.get("subject", None)
        if mapper.get("subject", None) is not None:
            del mapper["subject"]
        for row in reader:
            subject = row[subject_idx]
            if subject not in all_data.keys():
                all_data[subject] = []
            data = {}
            for key in mapper.keys():
                attributes = {}
                if key in ["variables"]:
                    if not args.expand:
                        data["V"] = row[mapper[key]].split(";")
                elif key in ["attirbutes"]:
                    try:
                        attributes = json.loads(row[mapper[key]])
                        for key in attributes.keys():
                            data[key] = attributes[key]
                    except json.JSONDecodeError:
                        pass
                elif key in ["choice"] or key in ["C"]:
                    data["C"] = row[mapper[key]].split(",")
                elif key in ["weight"]:
                    try:
                        data["W"] = float(row[mapper[key]])
                    except ValueError:
                        try:
                            data["W"] = json.loads(row[mapper[key]])
                        except json.JSONDecodeError:
                            data["W"] = 0.1
                else:
                    data[key] = row[mapper[key]]

            for key in attributes.keys():
                data[key] = attributes[key]
            if args.expand:
                variables = []
                for i in range(1, 9):
                    key = f"variable{i}"
                    if key in data.keys():
                        if data[key] != "":
                            variables.append(data[key])
                    del data[key]
                data["V"] = variables
            all_data[subject].append(data)
    for subject in all_data.keys():
        data = all_data[subject]
        this_os = os.name
        if this_os == "nt":
            file = subject.replace("-", "\\") + ".jsonl"
        else:
            file = subject.replace("-", "/") + ".jsonl"
        output_file = os.path.join(ouput_dir, file)
        dir = os.path.dirname(output_file)
        print(f"output {dir} {output_file}")
        os.makedirs(dir, exist_ok=True)
        print(f"make dir {dir}")
        with open(output_file, "w", encoding="utf-8") as f:
            for line in data:
                f.write(json.dumps(line, ensure_ascii=False) + "\n")


# main


def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="input file or directory")
    parser.add_argument("output", help="output file or directory")
    parser.add_argument("--bom", action="store_true", help="add BOM to output file")
    parser.add_argument(
        "--expand", action="store_true", help="expand Variables to columns"
    )
    args = parser.parse_args()

    if args.input.endswith(".jsonl"):
        jsonl2csv(args.input, args.output, args.bom, args)
    elif os.path.isdir(args.input):
        jsonl2csv(args.input, args.output, args.bom, args)
    elif args.input.endswith(".csv"):
        csv2jsonl(args.input, args.output, args.bom, args)
    else:
        print(
            "Usage: python tools/jsonl2csv.py [input_dir] [output_csv_file] | jsonl [input_csv_file] [output_dir]"
        )
        sys.exit(1)


main()
