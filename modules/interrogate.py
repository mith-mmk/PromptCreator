import modules.api as api
import base64
import json


def interrogate(imagefile, base_url, model='clip', userpass=None):
    base_url = api.normalize_base_url(base_url)
    url = (base_url + '/sdapi/v1/interrogate')
    with open(imagefile, 'rb') as f:
        image = base64.b64encode(f.read()).decode("ascii")
    payload = json.dumps(
        {'image': 'data:image/png;base64,' + image, 'model': model})
    response = api.request_post_wrapper(
        url, data=payload, progress_url=None, base_url=base_url, userpass=userpass)
    return response
