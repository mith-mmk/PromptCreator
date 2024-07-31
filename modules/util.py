import os


def get_part(filename):
    try:
        part = os.path.basename(filename).split("part")[-1].split(".")[0]
        parts = part.split("-")
        parts.reverse()
        part = []
        for p in parts:
            if not p.isdigit():
                part.append(p)
            else:
                break
        part.reverse()
        part = "-".join(part)

    except Exception as e:
        print(f"Failed to get part {e}")
        part = ""
    return part
