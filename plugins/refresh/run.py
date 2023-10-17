import modules.api as api
import modules.logger as logger
import modules.share as share

Logger = logger.getDefaultLogger()


def run(host=None, *args):
    if host is None or len(host) == 0:
        host = share.get("config").get("host")
        if host is None:
            host = "http://localhost:7860"
    else:
        host = host[0]
    host = api.normalize_base_url(host)

    if len(args) == 1:
        userpass = args[0]
    else:
        userpass = None
    Logger.info(f"refreshing checkpoint {host}")
    url = host + "/sdapi/v1/refresh-checkpoint"
    result1 = api.request_post_wrapper(
        url,
        data={},
        progress_url=None,
        base_url=host,
        userpass=userpass,
    )
    Logger.info(f"refreshing vae {host}")
    url = host + "/sdapi/v1/refresh-vae"
    result2 = api.request_post_wrapper(
        url,
        data={},
        progress_url=None,
        base_url=host,
        userpass=userpass,
    )
    url = host + "/sdapi/v1/refresh-loras"
    Logger.info(f"refreshing lora {host}")
    result3 = api.request_post_wrapper(
        url,
        data={},
        progress_url=None,
        base_url=host,
        userpass=userpass,
    )
    return [result1, result2, result3]
