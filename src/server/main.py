import os
import sys
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, Response
from draw_calendar import DrawCalendar
from waveshare_epd import epd7in5b_V2


app = FastAPI()
media_type = "application/octet-stream"

INDEX_HTML = """
<!doctype html>
<html lang="ja">
<head><meta charset="utf-8"><title>e-paper calendar</title></head>
<body>
<h1>e-paper calendar</h1>
<p><a href="/draw">今すぐ描画</a></p>
</body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def index():
    return INDEX_HTML


@app.get("/calendar")
async def calendar():
    c = DrawCalendar()
    black_bytes, red_bytes = c.generate()
    c.draw._save("img/image.png")

    return Response(content=black_bytes + red_bytes, media_type=media_type)


@app.get("/draw", response_class=HTMLResponse)
def draw():
    c = DrawCalendar()
    c.generate()

    epd = epd7in5b_V2.EPD()
    epd.init()
    epd.display(epd.getbuffer(c.draw.blackimage), epd.getbuffer(c.draw.redimage))
    epd.sleep()

    return "<p>描画しました。 <a href=\"/\">戻る</a></p>"
