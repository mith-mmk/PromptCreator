from modules.logger import getDefaultLogger

Logger = getDefaultLogger()


def xyz_index(name, method="txt2img"):
    """
    from xyz_grid.py 1.9
    """
    options = []
    options.append("Nothing")  # 0
    options.append("Seed")  # 1
    options.append("Var. seed")  # 2
    options.append("Var. strength")  # 3
    options.append("Steps")  # 4
    if method == "txt2img":
        options.append("Hires steps")
    options.append("CFG Scale")
    if method == "img2img":
        options.append("Image CFG Scale")
    options.append("Prompt S/R")
    options.append("Prompt order")
    if method == "txt2img":
        options.append("Sampler")  # txt2img
        options.append("Hires sampler")  # txt2img
    if method == "img2img":
        options.append("Sampler")  # img2img
    options.append("Checkpoint name")
    options.append("Negative Guidance minimum sigma")
    options.append("Sigma Churn")
    options.append("Sigma min")
    options.append("Sigma max")
    options.append("Sigma noise")
    options.append("Schedule type")
    options.append("Schedule min sigma")
    options.append("Schedule max sigma")
    options.append("Schedule rho")
    options.append("Eta")
    options.append("Clip skip")
    options.append("Denoising")
    options.append("Initial noise multiplier")
    options.append("Extra noise")
    if method == "txt2img":
        options.append("Hires upscaler")  # txt2img
    if method == "img2img":
        options.append("Cond. Image Mask Weight")  # img2img
    options.append("VAE")
    options.append("Styles")
    options.append("UniPC Order")
    options.append("Face restore")
    options.append("Token merging ratio")
    options.append("Token merging ratio high-res")
    options.append("Always discard next-to-last sigma")
    options.append("SGM noise multiplier")
    options.append("Refiner checkpoint")
    options.append("Refiner switch at")
    options.append("RNG source")
    options.append("FP8 mode")  #  1.8
    options.append("Size")  #  1.9.0 RC
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
