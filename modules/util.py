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
            else:
                try:
                    sd_vae = param["override_settings"]["forge_additional_modules"][0]
                    del param["override_settings"]["forge_additional_modules"]
                    vae = api.get_vae(base_url=base_url, vae=sd_vae)
                    if vae is not None:
                        param["override_settings"]["sd_vae"] = vae
                except Exception as e:
                    pass
                return param
        elif "sd_vae" in param["override_settings"]:
            sd_vae = param["override_settings"]["sd_vae"]
            # Automatc1111?
            vae = api.get_vae(base_url=base_url, vae=sd_vae)
            if vae is None:
                # forge
                modules = api.get_modules(base_url=base_url, modules=[sd_vae])
                if modules is None:
                    return param
                models = []
                for module in modules:
                    models.append(module["model_name"])
                del param["override_settings"]["sd_vae"]
                param["override_settings"]["forge_additional_modules"] = models
            else:
                # Automatic1111
                param["override_settings"]["sd_vae"] = param["sd_vae"]
                return param

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
