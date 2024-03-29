# sample of iterrogate api
# iterrogate api call has bug call self.__base64_to_image() but its function is not implementent
# workaround call decode_base64_to_image()
import argparse

import modules.logger as logger
from modules.interrogate import interrogate

Logger = logger.getDefaultLogger()


parser = argparse.ArgumentParser()

parser.add_argument(
    "--output",
    type=str,
    default=None,
    help="direcory of output file of prompt list file",
)
parser.add_argument(
    "--api-base", type=str, default="http://127.0.0.1:7860", help="api base url"
)
parser.add_argument(
    "--model", type=str, default="clip", help="set clip or deepdanbooru"
)
parser.add_argument("input", nargs="+", help="input files or dirs")
parser.parse_args()
args = parser.parse_args()

base_url = args.api_base
if type(args.input) is str:
    filenames = [args.input]
else:
    filenames = args.input

# model = 'deepdanbooru' need set webui --deepdanbooru option
for filename in filenames:
    result = interrogate(
        filename, base_url=base_url, model=args.model
    )  # 'clip' or 'deepdanbooru'
    Logger.info(result)
    if result.status_code == 200:
        Logger.info(filename)
        Logger.info(result.json()["caption"])
    else:
        Logger.info(result.text)
        Logger.info("Is Web UI replace newest version?")
