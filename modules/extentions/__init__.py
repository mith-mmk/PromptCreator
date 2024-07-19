from modules.logger import getDefaultLogger

Logger = getDefaultLogger()


def parse_extentions(base_url, item, opt):
    alwayson = item.get("alwayson_scripts")
    for key, value in alwayson.items():
        # load module modules/extentions/{key}.py
        try:
            module = __import__(f"modules.extentions.{key}", fromlist=[key])
        except ModuleNotFoundError:
            Logger.error(f"Module {key} not found")
            continue
        parsed = module.parse(base_url, value, opt)
        if parsed is not None:
            item["alwayson_scripts"][key] = parsed
