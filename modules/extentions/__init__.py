from modules.logger import getDefaultLogger

Logger = getDefaultLogger()


def xyz_index(name):
    """
    from xyz_grid.py 1.9
    """
    options = [
        "Nothing",  # 0
        "Seed",  # 1
        "Var. seed",  # 2
        "Var. strength",  # 3
        "Steps",  # 4
        "Hires steps",  # txt2img
        "CFG Scale",
        # "Image CFG Scale", # img2img
        "Prompt S/R",
        "Prompt order",
        "Sampler",  # txt2img
        "Hires sampler",  # txt2img
        # "Sampler", # img2img
        "Checkpoint name",
        "Negative Guidance minimum sigma",
        "Sigma Churn",
        "Sigma min",
        "Sigma max",
        "Sigma noise",
        "Schedule type",
        "Schedule min sigma",
        "Schedule max sigma",
        "Schedule rho",
        "Eta",
        "Clip skip",
        "Denoising",
        "Initial noise multiplier",
        "Extra noise",
        "Hires upscaler",  # txt2img
        # "Cond. Image Mask Weight", # img2img
        "VAE",
        "Styles",
        "UniPC Order",
        "Face restore",
        "Token merging ratio",
        "Token merging ratio high-res",
        "Always discard next-to-last sigma",
        "SGM noise multiplier",
        "Refiner checkpoint",
        "Refiner switch at",
        "RNG source",
        "FP8 mode",  #  1.8
        "Size",  #  1.9.0 RC
    ]
    if isinstance(name, str):
        return options.index(name)
    elif isinstance(name, int):
        return name
    else:
        raise ValueError(f"Invalid type {type(name)} for xyz_index")


def xyz_parse(item):
    script_name = item.get("script_name")
    if script_name == "x/y/z plot":
        value = item.get("script_args")
        if isinstance(value, list):
            value[0] = xyz_index(value[0])
            value[3] = xyz_index(value[3])
            value[6] = xyz_index(value[6])
        elif isinstance(value, dict):
            item["script_args"] = [
                xyz_index(value.get("x_type", "Nothing")),
                value.get("x_values", ""),
                value.get("x_values_dropdown"),
                xyz_index(value.get("y_type", "Nothing")),
                value.get("y_values", ""),
                value.get("y_values_dropdown"),
                xyz_index(value.get("z_type", "Nothing")),
                value.get("z_values", ""),
                value.get("z_values_dropdown"),
                value.get("draw_legend", "True"),
                value.get("include_lone_images", True),
                value.get("include_sub_grids", False),
                value.get("no_fixed_seeds", False),
                value.get("margin_size", 0),
                # value.get("vary_seeds_x", False),
                # value.get("vary_seeds_y", False),
                # value.get("vary_seeds_z", False),
                # value.get("csv_mode)", False),
            ]
        else:
            Logger.error(f"Invalid type {type(value)} for x/y/z plot")
    return item


def parse_extentions(base_url, item, opt):
    for key, value in item["alwayson_scripts"].items():
        try:
            module = __import__(f"modules.extentions.{key}", fromlist=[key])
        except ModuleNotFoundError:
            Logger.verbose(f"extentions perser Module {key} not found")
            continue
        parsed = module.parse(base_url, value, opt)
        if parsed is not None:
            item["alwayson_scripts"][key] = parsed
