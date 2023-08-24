import httpx
import logging


def run(args, _):
    try:
        if len(args) == 0:
            host = 'http://localhost:7860/'
        else:
            host = args[0]
        with httpx.Client() as client:
            r = client.get(host)
            status = r.status_code
            if status == 200:
                return True
            else:
                return False
    except Exception as e:
        logging.exception(e)
        return False
    
