import sys

from modules.parse import create_img2params

args = sys.argv
filename = sys.argv[1]
json = create_img2params(filename)


print(json)
