import base64
import os

from PIL import Image


def parser(args):
    # array ?
    if isinstance(args, list):
        return args
    # object ?
    if not isinstance(args, dict):
        return [True, True, "Basic", "", "Horizontal", "None", None, None]

    """
    "forge couple": {
    "args": [
        true,
        true,
        "Basic",
        "",
        "Horizontal",
        "None",
        null,
        null
      ]
    }
    """

    parsed = []
    if args.get("enbaled", False):
        parsed.append(True)
    else:
        parsed.append(False)
    if args.get("disale_hr", False):
        parsed.append(True)
    else:
        parsed.append(False)
    if args.get("mode"):
        # applied
        parsed.append(args.get("mode"))  # "Basic", "Advanced", "Mask"
    else:
        parsed.append("Basic")
    if args.get("separator"):
        parsed.append(args.get("separator"))
    else:
        parsed.append("")
    parsed.append(args.get("direction"))  # "Horizontal", "Vertical", null
    parsed.append(args.get("background"))  # "None", "First Line", "Last Line", null
    weight = args.get("background_weight")  # 0.1 - 1.5 | null
    # float purser
    weight = args.get("background_weight")
    try:
        if weight:
            weight = float(weight)
            if weight < 0.1:
                weight = 0.1
            elif weight > 1.5:
                weight = 1.5
    except ValueError:
        weight = None
    parsed.append(weight)
    # mapping Array[] | Object[] | null
    mapping = args.get("mapping")
    if mapping:
        if isinstance(mapping, list):
            pass
        elif isinstance(mapping, dict):
            mapping = [mapping]
        else:
            mapping = None
    if mapping is not None:
        for map in mapping:
            mask_filename = map.get("mask")
            # exists mask file
            if mask_filename and os.path.exists(mask_filename):
                with open(mask_filename, "rb") as f:
                    mask = f.read()
                    b64mask = base64.b64encode(mask)
                    map["mask"] = b64mask.decode("utf-8")

    parsed.append(mapping)

    parsed.append(args.get("common_parser"))  # "off"| "{ }"| "< >" | null

    common_debug = args.get("common_debug")

    if type(common_debug) == bool:
        parsed.append(common_debug)
    else:
        if common_debug == "true":
            parsed.append(True)
        elif common_debug == "false":
            parsed.append(False)
        else:
            parsed.append(None)

    return parsed
