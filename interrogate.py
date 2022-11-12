# sample of iterrogate api
# iterrogate api call has bug call self.__base64_to_image() but its function is not implementent
# workaround call decode_base64_to_image()
from create_prompts import iterrogate
import sys

if len(sys.argv) <=2:
    print ('itterrogate.py [filename] ([base_url defualt:http://127.0.0.1:7860])')
    exit(1)


filename = sys.argv[1]
if len(sys.argv) >= 3:
    base_url = sys.argv[2]
else:
    base_url ='http://127.0.0.1:7860'

# model = 'deepdanbooru' need set webui --deepdanbooru option
result = iterrogate(filename,base_url=base_url,model = 'deepdanbooru') # 'clip' or 'deepdanbooru'
if result.status_code == 200:
    print (result.json()['caption'])
else:
    print(result.text)
    print('iterrogate api has bug call self.__base64_to_image() but this function is not implementent')
    print('workaround it is replace decode_base64_to_image()')

