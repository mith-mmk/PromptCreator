import os
import sys

import piexif
from PIL import Image, PngImagePlugin


def main():
    dir = sys.argv[1]
    print(f"Converting PNG to WEBP in {dir}")
    for root, dirs, files in os.walk(dir):
        for file in files:
            if file.endswith(".png"):
                png = os.path.join(root, file)
                webp = png.replace(".png", ".webp")
                print(f"Converting {png} to {webp}")
                img = PngImagePlugin.PngImageFile(png)
                im = Image.open(png)
                meta = img.info.get("parameters", None)
                if meta is not None:
                    bytes_text = bytes(meta, encoding="utf-16be")
                    exif_dict = {
                        "Exif": {
                            piexif.ExifIFD.UserComment: b"UNICODE\0" + bytes_text,
                        }
                    }
                    exif_bytes = piexif.dump(exif_dict)
                    im.save(webp, "WEBP", exif=exif_bytes)
                else:
                    im.save(webp, "WEBP")


main()
