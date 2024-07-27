import os


def get_part(filename):
    try:
        part = os.path.basename(filename).split("part")[-1].split(".")[0]
        parts = part.split("-")
        parts.reverse()
        part = ""
        for p in parts:
            if not p.isdigit():
                part = p + "-" + part
            else:
                break
        part = part[:-1]

    except Exception as e:
        print(f"Failed to get part {e}")
        part = ""
    return part
