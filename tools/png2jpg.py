from PIL import Image, PngImagePlugin

filename = "test\\test.png"
output = "test\\test.jpg"

img = Image.open(filename)
# "get" text from png
imgtext = PngImagePlugin.PngInfo()
text = img.info['parameters']
print(text)
# "set" text to jpg
try:
    import piexif
    bytes_text = bytes(text, encoding='utf-16be')
    user_comment = 'ユーザーコメント'
    user_bytes = bytes(user_comment, encoding='utf-16le')
    exif_dict = {
        "0th": {
            piexif.ImageIFD.XPComment: user_bytes
        },
        "Exif": {
            piexif.ExifIFD.UserComment: b'UNICODE\0' + bytes_text,
        }
    }
    exif_bytes = piexif.dump(exif_dict)
    exif = exif_bytes
    img.save(output, exif=exif_bytes)
except ImportError:
    print("piexif not found")
    img.save(output)
    exit(1)




    
