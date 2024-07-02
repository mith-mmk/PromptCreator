import os


def get_part(filename):
    try:
        part = os.path.basename(filename).split("part")[-1].split(".")[0]
        part = "part" + part
    except Exception as e:
        print(f"Failed to get part {e}")
        part = ""
    return part
