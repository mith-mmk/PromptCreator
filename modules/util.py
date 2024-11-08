import os

import modules.api as api


def get_forge_additional_module_names(base_url, param):

    if param.get("override_settings", {}):
        # if "forge_additional_modules" in param["override_settings"]: get module names
        if "forge_additional_modules" in param["override_settings"]:
            modules = api.get_modules(
                base_url=base_url,
                modules=param["override_settings"]["forge_additional_modules"],
            )

            if modules is not None:
                models = []

                for module in modules:
                    models.append(module["model_name"])
                param["override_settings"]["forge_additional_modules"] = models
    return param


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
        key = key.strip()
        value = value.strip()
        result[key] = value
    return result
