# -*- coding: utf-8 -*-

from PIL import Image, ImageDraw
from misakifont import MisakiFont
from misakifont.fontdata import fontdata
import numpy as np


class Draw():
    def __init__(self):
        self.WIDTH = 800
        self.HEIGHT = 480
        self.blackimage = Image.new("1", (self.WIDTH, self.HEIGHT), 1)
        self.blackdraw = ImageDraw.Draw(self.blackimage)
        self.redimage = Image.new("1", (self.WIDTH, self.HEIGHT), 1)
        self.reddraw = ImageDraw.Draw(self.redimage)
        self.BLACK = 1
        self.RED = 2
        self.draw_method = {
            self.BLACK: self.blackdraw,
            self.RED: self.reddraw
        }
        self.image_method = {
            self.BLACK: self.blackimage,
            self.RED: self.redimage
        }

    def text(self, string, x, y, m=1, color=1, fill=False, dx=0, dy=0, align="l", width=0):
        if align == "c" and width < len(string):
            raise ValueError
        elif align == "c":
            offset_char = (width - len(string)) / 2
            offset_px = int(offset_char * 8 * m)
            x += offset_px

        if fill:
            self.draw_method[color].rectangle((x-dx, y-dy, x+(8*m*len(string))+(2*dx), y+(8*m)+(2*dy)), fill=0)
        for c in string:
            char_code = ord(c)
            try:
                if char_code >= 32 and char_code <= 127:
                    yoko_char_bytes = [fontdata[((char_code-32)*8)+b] for b in range(8)]
                    char_bytes = np.rot90(np.array([[i for i in f"{j:08b}"] for j in yoko_char_bytes])).tolist()
                    char_bytes = [int("".join(i), 2) for i in char_bytes]
                else:
                    mf = MisakiFont()
                    char_bytes = mf.font(char_code)

                for row in range(8):
                    row_byte = char_bytes[row]
                    for col in range(8):
                        if (row_byte >> (7 - col)) & 1:
                            px = x + col * m
                            py = y + row * m

                            if not fill:
                                self.draw_method[color].rectangle((px, py, px + m, py + m), fill=0)
                            else:
                                self.reddraw.rectangle((px, py, px + m, py + m), fill=255)
                                self.blackdraw.rectangle((px, py, px + m, py + m), fill=255)

                x += 8 * m
            
            except ValueError:
                x += 8 * m
    
    def line(self, x1, y1, x2, y2, m=1, color=1):
        self.draw_method[color].line(((x1, y1), (x2, y2)), fill=0, width=m)

    def img_pil(self, pil, x=0, y=0, m=1, color=1):
        img = pil.resize((round(pil.width * m), round(pil.height * m)), Image.Resampling.LANCZOS)
        binimg = img.convert("L")
        binimg.point(lambda x: 0 if x < 200 else x)
        self.image_method[color].paste(binimg, (x, y))

    def img_path(self, path, x=0, y=0, m=1, color=1):
        img = Image.open(path)
        self.img_pil(img, x, y, m, color)

    def to_bytes(self):
        blackbytes = self.blackimage.tobytes()
        redbytes = self.redimage.tobytes()
        return blackbytes, redbytes

    def _save(self, filename="img/image.png"):
        merged_image = Image.new('RGB', (self.WIDTH, self.HEIGHT), (255, 255, 255))
        merged_image.paste(self.blackimage)

        for y in range(self.HEIGHT):
            for x in range(self.WIDTH):
                p = self.redimage.getpixel((x,y))
                if p == 0:
                    merged_image.putpixel((x,y), (255, 0, 0))

        merged_image.save(filename)

    def _scale(self):
        for y in range(self.HEIGHT // 100 + 1):
            self.blackdraw.line(((0, y*100), (self.WIDTH, y*100)), 0, 2)
        for x in range(self.WIDTH // 100 + 1):
            self.blackdraw.line(((x*100, 0), (x*100, self.HEIGHT)), 0, 2)


if __name__ == "__main__":
    draw = Draw()
    draw.img("img/pose_galpeace_schoolgirl.png", 0, 0)

    draw._save("img/binaryimage.png")