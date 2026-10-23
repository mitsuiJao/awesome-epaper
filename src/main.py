import io
import os
import threading

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response
from PIL import Image, ImageOps
from epd_7in5b_V2_test import run_demo
from lib.draw_calendar import DrawCalendar
from lib.epd_backend import get_epd
from apscheduler.schedulers.asyncio import AsyncIOScheduler


app = FastAPI()
media_type = "application/octet-stream"

BASE_DIR = os.path.dirname(__file__)
STATIC_DIR = os.path.join(BASE_DIR, "static")
IMG_DIR = os.path.join(BASE_DIR, "img")
PREVIEW_PATH = os.path.join(IMG_DIR, "image.png")

scheduler = AsyncIOScheduler(timezone="Asia/Tokyo")
epd_lock = threading.Lock()


@app.on_event("startup")
async def start_scheduler():
    scheduler.start()


@app.on_event("shutdown")
async def stop_scheduler():
    scheduler.shutdown(wait=False)


def save_preview(blackimage, redimage):
    os.makedirs(IMG_DIR, exist_ok=True)
    merged = Image.new("RGB", (800, 480), (255, 255, 255))
    merged.paste(blackimage)
    for y in range(480):
        for x in range(800):
            if redimage.getpixel((x, y)) == 0:
                merged.putpixel((x, y), (255, 0, 0))
    merged.save(PREVIEW_PATH)


def push_to_epd(blackimage, redimage):
    save_preview(blackimage, redimage)

    with epd_lock:
        epd = get_epd()
        epd.init()
        try:
            epd.display(epd.getbuffer(blackimage), epd.getbuffer(redimage))
        finally:
            epd.sleep()


def calendar_job():
    c = DrawCalendar()
    c.generate()
    push_to_epd(c.draw.blackimage, c.draw.redimage)


def cancel_job():
    if scheduler.get_job("job"):
        scheduler.remove_job("job")
        
        
@app.get("/")
async def index():
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


# @app.get("/draw/calendar/preview")
# async def draw_calendar_preview():
#     c = DrawCalendar()
#     black_bytes, red_bytes = c.generate()
#     save_preview(c.draw.blackimage, c.draw.redimage)

#     return Response(content=black_bytes + red_bytes, media_type=media_type)


@app.post("/draw/calendar")
def draw_calendar():
    calendar_job()
    scheduler.add_job(calendar_job, "cron", hour=0, minute=10, id="job", replace_existing=True)

    return {"ok": True}


@app.post("/draw/clear")
def draw_clear():
    epd = get_epd()
    epd.init()
    epd.Clear()
    epd.sleep()

    blank = Image.new("1", (800, 480), 1)
    save_preview(blank, blank)

    cancel_job()
    return {"ok": True}


@app.post("/draw/test")
def draw_test():
    run_demo()

    cancel_job()
    
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

    cancel_job()
    
    return {"ok": True}
