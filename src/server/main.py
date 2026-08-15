import io
import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps
from epd_7in5b_V2_test import run_demo
from lib.draw_calendar import DrawCalendar
from lib.epd_backend import get_epd


app = FastAPI()
media_type = "application/octet-stream"

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMG_DIR = os.path.join(BASE_DIR, "img")
PREVIEW_PATH = os.path.join(IMG_DIR, "image.png")


def save_preview(blackimage, redimage):
    merged = Image.new("RGB", (800, 480), (255, 255, 255))
    merged.paste(blackimage)
    for y in range(480):
        for x in range(800):
            if redimage.getpixel((x, y)) == 0:
                merged.putpixel((x, y), (255, 0, 0))
    merged.save(PREVIEW_PATH)


def push_to_epd(blackimage, redimage):
    save_preview(blackimage, redimage)

    epd = get_epd()
    epd.init()
    epd.display(epd.getbuffer(blackimage), epd.getbuffer(redimage))
    epd.sleep()


@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/calendar")
async def calendar():
    c = DrawCalendar()
    black_bytes, red_bytes = c.generate()
    save_preview(c.draw.blackimage, c.draw.redimage)

    return Response(content=black_bytes + red_bytes, media_type=media_type)


@app.get("/draw")
def draw():
    c = DrawCalendar()
    c.generate()
    push_to_epd(c.draw.blackimage, c.draw.redimage)

    return {"ok": True}


@app.post("/draw/clear")
def draw_clear():
    epd = get_epd()
    epd.init()
    epd.Clear()
    epd.sleep()

    blank = Image.new("1", (800, 480), 1)
    save_preview(blank, blank)

    return {"ok": True}


@app.post("/draw/test")
def draw_test():
    run_demo()

    return {"ok": True}


@app.post("/draw/image")
async def draw_image(file: UploadFile = File(...)):
    data = await file.read()
    try:
        img = Image.open(io.BytesIO(data)).convert("RGB")
    except Exception:
        raise HTTPException(status_code=400, detail="画像を読み込めませんでした")

    img = ImageOps.exif_transpose(img)
    img = ImageOps.fit(img, (800, 480), Image.Resampling.LANCZOS)
    img = img.convert("1")
    redimage = Image.new("1", (800, 480), 1)
    push_to_epd(img, redimage)

    return {"ok": True}
