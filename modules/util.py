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
    if part == "-":
        part = ""
    return part


def divide_values(values):
    """
    values "width=256,height=256"
    return ["width=256", "height=256"]
    """
    result = {}
    for value in values.split(","):
        key, value = value.split("=")
        result[key] = value
    return result
