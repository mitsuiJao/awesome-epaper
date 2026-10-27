import math
from datetime import datetime
from zoneinfo import ZoneInfo

from .draw import Draw
from . import yahoo_chart

JST = ZoneInfo("Asia/Tokyo")

MAIN_SYMBOL = ("NIKKEI 225", "^N225")
# (ラベル, シンボル, 現在値の小数桁数)
SUB_SYMBOLS = [
    ("TOPIX", "1306.T", 1),
    ("USD/JPY", "JPY=X", 2),
    ("S&P 500", "^GSPC", 0),
]
# 東証の昼休み(11:30-12:30)。寄り付きからの経過秒
LUNCH = (150 * 60, 210 * 60)
SESSION_SECONDS = 390 * 60
# 上昇(プラス)を赤、下落(マイナス)を黒で描く。Falseにすると逆(上昇=黒、下落=赤)
UP_IS_RED = True


class DrawMarket():
    HEADER_H = 72
    X1, X2, Y1, Y2 = 16, 704, 84, 320
    SUB_TOP = 344
    HATCH = 4
    CANDLE_HALF = 3
    PAD = 8

    def __init__(self):
        self.draw = Draw()
        self.now = datetime.now(JST)
        self.main = yahoo_chart.get_chart(MAIN_SYMBOL[1])
        if self.main is None:
            raise RuntimeError("日経225のデータを取得できませんでした")
        self.subs = [(label, dec, yahoo_chart.get_chart(symbol)) for label, symbol, dec in SUB_SYMBOLS]
        self.data_ts = self.main["last_ts"]

    def generate(self):
        self.draw_header()
        self.draw_main_chart()
        self.draw_subs()

    def trend_color(self, up):
        return self.draw.RED if up == UP_IS_RED else self.draw.BLACK

    @staticmethod
    def hhmm(ts):
        return datetime.fromtimestamp(ts, JST).strftime("%H:%M")

    def is_live(self):
        now = self.now.timestamp()
        return self.main["start"] <= now <= self.main["end"] and now - self.data_ts < 1800

    def draw_header(self):
        d = self.draw
        c = self.main
        diff = c["price"] - c["prev_close"]
        pct = diff / c["prev_close"] * 100

        d.rect(0, 0, d.WIDTH - 1, self.HEADER_H - 1, fill=True)
        d.text(MAIN_SYMBOL[0], 16, 8, 2, invert=True)
        d.text(f"{c['price']:,.0f}", 16, 28, 5, invert=True)

        # 黒帯の上の赤は、細い文字だと沈むので面で使う。赤は先に下地を白抜きしてから塗る(黒と赤のプレーンを重ねない)
        if self.is_live():
            d.clear_rect(196, 5, 268, 25)
            d.rect(196, 5, 268, 25, d.RED, fill=True)
        d.text("LIVE" if self.is_live() else "CLOSED", 200, 8, 2, invert=True)

        # ▲/▼は上昇/下落の配色の面(赤なら赤、黒なら黒帯に合わせて白)。差額と%は白抜き
        triangle = [(308, 28), (290, 60), (326, 60)] if diff >= 0 else [(290, 28), (326, 28), (308, 60)]
        d.polygon(triangle, invert=True)
        if self.trend_color(diff >= 0) == d.RED:
            d.polygon(triangle, color=d.RED)
        d.text(f"{diff:+,.1f}", 342, 22, 3, invert=True)
        d.text(f"{pct:+.2f}%", 342, 50, 2, invert=True)

        for y, s in ((12, f"DATA {self.hhmm(self.data_ts)}"), (36, f"UPD {self.now.strftime('%H:%M')}")):
            d.text(s, d.WIDTH - 16 - len(s) * 16, y, 2, invert=True)

    def draw_main_chart(self):
        d = self.draw
        c = self.main
        d.rect(self.X1, self.Y1, self.X2, self.Y2)

        candles = c["candles"]
        # 端のローソク足が外枠に重ならないよう、時間軸は左右に余白を取る
        px, py = self.make_scale(c, [v for _, _, h, l, _ in candles for v in (h, l)],
                                 self.X1 + self.PAD, self.Y1, self.X2 - self.PAD, self.Y2)
        yp = round(py(c["prev_close"]))
        d.dashed_line(self.X1, yp, self.X2, yp)
        self.draw_candles(candles, px, py)

        # 時間軸(目盛りは1時間ごと)と昼休み
        for t in range(0, c["end"] - c["start"] + 1, 3600):
            x = round(px(c["start"] + t))
            hour = str(datetime.fromtimestamp(c["start"] + t, JST).hour)
            d.line(x, self.Y2, x, self.Y2 + 4)
            d.text(hour, x - len(hour) * 4, self.Y2 + 8, 1)
        if c["end"] - c["start"] == SESSION_SECONDS:
            xa, xb = (round(px(c["start"] + s)) for s in LUNCH)
            d.dashed_line(xa, self.Y1, xa, self.Y2, 2, 4)
            d.dashed_line(xb, self.Y1, xb, self.Y2, 2, 4)
            d.text("LUNCH", (xa + xb) // 2 - 20, self.Y1 + 6, 1)

        # 高値・安値・現在値・前日終値のラベル(右軸)
        high = max(h for _, _, h, _, _ in candles)
        low = min(l for _, _, _, l, _ in candles)
        close = candles[-1][4]
        labels = sorted([
            [py(high), f"H {high:,.0f}", d.BLACK],
            [py(low), f"L {low:,.0f}", d.BLACK],
            [py(close), f"C {close:,.0f}", self.trend_color(close >= c["prev_close"])],
            [py(c["prev_close"]), f"P {c['prev_close']:,.0f}", d.BLACK],
        ])
        for i in range(1, len(labels)):
            labels[i][0] = max(labels[i][0], labels[i - 1][0] + 11)
        for y, s, color in labels:
            d.text(s, self.X2 + 8, round(y) - 4, 1, color)

    def draw_candles(self, candles, px, py):
        """陽線(終値>=始値)・陰線とも塗りつぶし。色は上昇/下落の配色に従う。"""
        d = self.draw
        for ts, o, h, l, c in candles:
            x = round(px(ts))
            top, bottom = sorted((round(py(o)), round(py(c))))
            bottom = max(bottom, top + 1)
            color = self.trend_color(c >= o)
            d.line(x, round(py(h)), x, round(py(l)), 1, color)
            d.rect(x - self.CANDLE_HALF, top, x + self.CANDLE_HALF, bottom, color, fill=True)

    def make_scale(self, chart, values, x1, y1, x2, y2):
        """時刻→x、値→yの変換関数を返す。値の範囲には前日終値を含める。"""
        prev = chart["prev_close"]
        lo, hi = min(values + [prev]), max(values + [prev])
        pad = (hi - lo) * 0.08 or 1
        lo, hi = lo - pad, hi + pad
        span = chart["end"] - chart["start"]

        def px(ts):
            return x1 + min(max((ts - chart["start"]) / span, 0), 1) * (x2 - x1)

        def py(v):
            return y2 - (v - lo) / (hi - lo) * (y2 - y1)

        return px, py

    def draw_subs(self):
        d = self.draw
        gap = 12
        w = (d.WIDTH - 32 - gap * (len(self.subs) - 1)) // len(self.subs)
        bottom = d.HEIGHT - 8
        for i, (label, dec, chart) in enumerate(self.subs):
            x = 16 + i * (w + gap)
            d.rect(x, self.SUB_TOP, x + w, bottom)
            d.text(label, x + 8, self.SUB_TOP + 8, 2)
            if chart is None:
                d.text("--", x + 8, self.SUB_TOP + 34, 3)
                continue

            diff = chart["price"] - chart["prev_close"]
            pct = diff / chart["prev_close"] * 100
            s = f"{pct:+.2f}%"
            d.text(s, x + w - 8 - len(s) * 16, self.SUB_TOP + 8, 2, self.trend_color(diff >= 0))
            d.text(f"{chart['price']:,.{dec}f}", x + 8, self.SUB_TOP + 34, 3)
            self.plot(chart, x + 8, self.SUB_TOP + 64, x + w - 8, bottom - 8, width=1, hatch=False)

    def plot(self, chart, x1, y1, x2, y2, width, hatch):
        """chartの折れ線を枠(x1,y1)-(x2,y2)に描く。前日終値より上/下で上昇/下落の配色に切り替える。"""
        d = self.draw
        prev = chart["prev_close"]
        px, py = self.make_scale(chart, [v for _, v in chart["points"] if v is not None], x1, y1, x2, y2)
        yp = round(py(prev))
        d.dashed_line(x1, yp, x2, yp)

        last = None
        for ts, v in chart["points"]:
            if v is None:
                last = None
                continue
            cur = (px(ts), py(v), v)
            if last is not None:
                self.segment(last, cur, prev, yp, width, hatch)
            last = cur
        return px, py

    def segment(self, a, b, prev, yp, width, hatch):
        """a,bは(x, y, 値)。前日終値をまたぐ場合は交点で分割して色を切り替える。"""
        if (a[2] - prev) * (b[2] - prev) < 0:
            t = (prev - a[2]) / (b[2] - a[2])
            mid = (a[0] + t * (b[0] - a[0]), yp, prev)
            self.segment(a, mid, prev, yp, width, hatch)
            self.segment(mid, b, prev, yp, width, hatch)
            return

        d = self.draw
        color = self.trend_color((a[2] + b[2]) / 2 >= prev)
        d.line(round(a[0]), round(a[1]), round(b[0]), round(b[1]), width, color)
        if not hatch or b[0] <= a[0]:
            return
        for x in range(math.ceil(a[0] / self.HATCH) * self.HATCH, math.ceil(b[0]), self.HATCH):
            if a[0] <= x < b[0]:
                y = a[1] + (b[1] - a[1]) * (x - a[0]) / (b[0] - a[0])
                d.line(x, yp, x, round(y), 1, color)


if __name__ == "__main__":
    m = DrawMarket()
    m.generate()
    m.draw._save("img/image.png")
