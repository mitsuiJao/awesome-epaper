# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is a single repository. Everything lives under `src/`, and it all runs on one machine: a Raspberry Pi with a Waveshare 7.5" B (black/white/red) e-paper HAT wired to it over SPI/GPIO.

- **`src/waveshare_epd/`** — vendored Waveshare driver for the display (`epd7in5b_V2.py` + `epdconfig.py`), talking SPI/GPIO via a `RaspberryPi` config class. This is the known-good, working driver — do not modify it.
- **`src/epd_7in5b_V2_test.py`** — Waveshare's stock hardware smoke-test demo (draws sample text/shapes, then a bmp, then clears). Used to verify the HAT is wired correctly. Do not modify it.
- **`src/pic/`** — fonts/bitmaps used only by `epd_7in5b_V2_test.py`.
- **`src/clear.py`** — one-shot manual utility that clears the panel (`epd.init()` → `epd.Clear()` → `epd.sleep()`).
- **`src/server/`** — a FastAPI app that renders a calendar view and drives the physical display, in a single process, in the same request handler. There is no separate client/server split and no bitmap transfer over HTTP — rendering and display live in the same Python process because the app runs directly on the Pi that owns the hardware.

Weather rendering is not implemented (it was dropped; only the calendar view exists).

## Commands

Run from the repository root, with a venv set up per `README.md` (installs both the FastAPI/Google-API deps and the hardware deps — `spidev`/`gpiozero`/`lgpio` — from a single `requirements.txt`, since server and hardware control share one environment):

```shell
uvicorn main:app --app-dir src/server   # add --port to change from the default 8000
```

Requires `src/server/secret.py` (copy from `src/server/secret.py.example` and fill in real values) and the GCP service-account JSON it points to — both gitignored, must be created manually. See `README.md`.

Hardware smoke test (no automated test suite exists in this repo):

```shell
cd src && python epd_7in5b_V2_test.py
```

## Architecture

### `src/server/main.py` — FastAPI endpoints

- **`GET /`** — minimal HTML control page for phone use, with a link to `/draw`.
- **`GET /draw`** — the main entry point: builds `DrawCalendar()`, renders, then instantiates `waveshare_epd.epd7in5b_V2.EPD()` directly and pushes the result to the physical display (`epd.init()` → `epd.display(epd.getbuffer(...), epd.getbuffer(...))` → `epd.sleep()`). Defined as a sync `def` (not `async def`) since the SPI calls are blocking; FastAPI runs sync handlers in a thread pool. There is no scheduled/automatic redraw — refresh is manual only, triggered by hitting this endpoint (e.g. from a phone).
- **`GET /calendar`** — debug/preview endpoint: returns the rendered black-plane + red-plane bitmap bytes (`black_bytes + red_bytes`) as `application/octet-stream`, and writes a preview PNG to `src/server/img/image.png`. Does not touch the hardware.

### Render pipeline

- **`src/server/draw.py` (`Draw`)** is the shared rendering engine. It holds two 800×480 1-bit PIL canvases (`blackimage`/`redimage`) and exposes `text()`, `line()`, `img_pil()`/`img_path()`, and `to_bytes()`/`_save()`. `text()` is a custom bitmap-font renderer: ASCII characters come from the `fontdata` table (8×8 glyphs), non-ASCII (Japanese) characters are rendered via `misakifont/`. All higher-level drawing goes through this class. `GET /draw` uses `blackimage`/`redimage` directly (via `epd.getbuffer()`) rather than `to_bytes()`, since there's no wire transfer to round-trip through.
- **`src/server/draw_calendar.py` (`DrawCalendar`)** composes the calendar view: current month grid (weekends/holidays in red, via the `holidays-jp` API through `requestAPI.request_API`), today's date, and upcoming Google Calendar events (via `google_calendar.py`).
- **`src/server/google_calendar.py`** pulls events from a Google Calendar via a service-account. It imports `GOOGLE_SERVICEACCOUNTFILE`/`GOOGLE_CALENDAERID` from a local, untracked `secret.py` (not in the repo — must be created manually from `secret.py.example`, alongside the GCP service-account JSON it points to).
- **`src/server/requestAPI.py`** has a generic `request_API()` GET helper, used for the holidays-jp API.
- **`src/server/misakifont/`** is a vendored bitmap-font library for Japanese glyphs, used by `Draw.text()`.

## Notes for future changes

- `src/waveshare_epd/` and `src/epd_7in5b_V2_test.py` are treated as a known-good reference implementation — if the display stops working, diff against these rather than guessing at the driver/SPI layer.
- Because everything is one process, changing the byte layout `Draw` produces has no cross-repo contract to keep in sync (unlike the old client/server split) — `GET /draw` and `GET /calendar` can diverge freely as long as both still call into the same `Draw` canvases correctly.
