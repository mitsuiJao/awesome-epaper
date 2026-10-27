import urllib.parse

import requests

URL = "https://query1.finance.yahoo.com/v8/finance/chart/{}"
HEADERS = {"User-Agent": "Mozilla/5.0"}


def get_chart(symbol: str, interval: str = "5m", range_: str = "1d"):
    try:
        res = requests.get(
            URL.format(urllib.parse.quote(symbol, safe="")),
            params={"interval": interval, "range": range_},
            headers=HEADERS,
            timeout=15,
        )
        res.raise_for_status()
        result = res.json()["chart"]["result"][0]
        meta = result["meta"]
        quote = result["indicators"]["quote"][0]
        closes = quote["close"]
        points = list(zip(result["timestamp"], closes))
        valid = [p for p in points if p[1] is not None]
        candles = [
            (ts, o, h, l, c)
            for ts, o, h, l, c in zip(result["timestamp"], quote["open"], quote["high"], quote["low"], closes)
            if None not in (o, h, l, c)
        ]
        if not valid:
            print(f"{symbol}: データがありません。")
            return None

        regular = meta["currentTradingPeriod"]["regular"]
        return {
            "symbol": symbol,
            "price": meta["regularMarketPrice"],
            "prev_close": meta["chartPreviousClose"],
            "points": points,
            "candles": candles,
            "last_ts": valid[-1][0],
            "start": regular["start"],
            "end": regular["end"],
        }

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None


if __name__ == '__main__':
    print(get_chart("^N225"))
