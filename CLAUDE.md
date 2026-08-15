# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is a single repository. Everything lives under `src/`, and it all runs on one machine: a Raspberry Pi with a Waveshare 7.5" B (black/white/red) e-paper HAT wired to it over SPI/GPIO.

- **`src/waveshare_epd/`** — vendored Waveshare driver for the display (`epd7in5b_V2.py` + `epdconfig.py`), talking SPI/GPIO via a `RaspberryPi` config class. This is the known-good, working driver — do not modify it. It stays directly under `src/` because it's a shared module imported by both `src/server/main.py` and `src/server/epd_7in5b_V2_test.py`.
- **`src/server/epd_7in5b_V2_test.py`** — Waveshare's stock hardware smoke-test demo (draws sample text/shapes, then a bmp, then clears). Used to verify the HAT is wired correctly. Do not modify it. It resolves `waveshare_epd` via `sys.path[0]` (its own directory, `src/server/`) plus `PYTHONPATH=src` at run time, since the driver lives one level up — see README for the exact command.
- **`src/server/pic/`** — fonts/bitmaps used only by `epd_7in5b_V2_test.py`.
- **`src/clear.py`** — one-shot manual utility that clears the panel (`epd.init()` → `epd.Clear()` → `epd.sleep()`).
- **`src/server/`** — a FastAPI app that renders a calendar view and drives the physical display, in a single process, in the same request handler. There is no separate client/server split and no bitmap transfer over HTTP — rendering and display live in the same Python process because the app runs directly on the Pi that owns the hardware. `GET /` serves a small dashboard (`static/index.html`) with four modes (calendar/image/test/clear); each draw action saves a preview PNG to `src/server/img/image.png`, overwritten on every call. Only entry points (`main.py`, `google_auth_setup.py`, `epd_7in5b_V2_test.py`) and config (`secret.py`/`secret.py.example`) sit directly under `src/server/`; the rendering engine and data-fetch modules live in `src/server/lib/` (an explicit package — `src/server/lib/__init__.py` exists, and modules inside it import each other with relative imports, e.g. `from . import google_auth`). `src/server/lib` is importable because `src/server` itself is always on `sys.path` — either via uvicorn's `--app-dir src/server`, or because `google_auth_setup.py` is run directly from within `src/server/` (making it `sys.path[0]`).

Weather rendering is not implemented (it was dropped; only the calendar view exists).

## Commands

Run from the repository root, with a venv set up per `README.md` (installs both the FastAPI/Google-API deps and the hardware deps — `spidev`/`gpiozero`/`lgpio` — from a single `requirements.txt`, since server and hardware control share one environment):

```shell
uvicorn main:app --app-dir src/server   # add --port to change from the default 8000
```

Requires `src/server/secret.py` (copy from `src/server/secret.py.example` and fill in real values) and the GCP OAuth client-secret JSON it points to — both gitignored, must be created manually. Also requires a one-time interactive `src/server/google_auth_setup.py` run to produce `src/server/token.json` (OAuth device-flow consent; see README.md) before Calendar/Tasks calls will work.

Hardware smoke test (no automated test suite exists in this repo):

```shell
PYTHONPATH=src python src/server/epd_7in5b_V2_test.py
```

## Architecture

### `src/server/main.py` — FastAPI endpoints

- **`GET /`** — serves `static/index.html`, a dashboard with a mode radio group (calendar/image/test/clear) and a "draw!" button. The page's JS calls the matching endpoint below based on the selected mode.
- **`GET /draw`** — calendar mode: builds `DrawCalendar()`, renders, then pushes to the physical display via the shared `push_to_epd()` helper (`epd.init()` → `epd.display(epd.getbuffer(...), epd.getbuffer(...))` → `epd.sleep()`). Defined as a sync `def` (not `async def`) since the SPI calls are blocking; FastAPI runs sync handlers in a thread pool.
- **`POST /draw/clear`** — clears the panel (same sequence as `src/clear.py`).
- **`POST /draw/test`** — builds a simple grid + text test pattern via the `Draw` class and pushes it through `push_to_epd()`. A separate implementation from `src/server/epd_7in5b_V2_test.py`, which stays untouched.
- **`POST /draw/image`** — accepts a `multipart/form-data` upload (`file` field), crops/resizes it to 800x480 with `PIL.ImageOps.fit`, and pushes it (red plane left blank) through `push_to_epd()`. `EPD.getbuffer()` does the black/white dithering itself via `Image.convert('1')`.
- **`push_to_epd(blackimage, redimage)`** — shared helper used by all four draw actions above: saves a preview PNG (`save_preview()`) then does the `epd.init()`/`epd.display()`/`epd.sleep()` sequence. There is no scheduled/automatic redraw — refresh is manual only, triggered from the dashboard.
- **`save_preview(blackimage, redimage)`** — merges the black/red planes into an RGB image and overwrites `src/server/img/image.png` (path anchored to `os.path.dirname(__file__)`, independent of the process's CWD). Called on every `/draw*` action and by `GET /calendar`.
- **`GET /calendar`** — debug/preview endpoint: returns the rendered black-plane + red-plane bitmap bytes (`black_bytes + red_bytes`) as `application/octet-stream`. Does not touch the hardware.

### Render pipeline

- **`src/server/lib/draw.py` (`Draw`)** is the shared rendering engine. It holds two 800×480 1-bit PIL canvases (`blackimage`/`redimage`) and exposes `text()`, `line()`, `img_pil()`/`img_path()`, and `to_bytes()`/`_save()`. `text()` is a custom bitmap-font renderer: ASCII characters come from the `fontdata` table (8×8 glyphs), non-ASCII (Japanese) characters are rendered via `lib/misakifont/`. All higher-level drawing goes through this class. `GET /draw` uses `blackimage`/`redimage` directly (via `epd.getbuffer()`) rather than `to_bytes()`, since there's no wire transfer to round-trip through.
- **`src/server/lib/draw_calendar.py` (`DrawCalendar`)** composes the calendar view: current month grid (weekends/holidays in red, via the `holidays-jp` API through `requestAPI.request_API`), today's date, and upcoming Google Calendar events (via `google_calendar.py`).
- **`src/server/lib/google_calendar.py`** pulls events from a Google Calendar via shared OAuth2 credentials (see below). It imports `GOOGLE_CALENDAERID` from a local, untracked `secret.py` (not in the repo — must be created manually from `secret.py.example`).
- **`src/server/lib/google_tasks.py`** pulls tasks from the user's default Google Tasks list via the same shared OAuth2 credentials. Fetch-only — nothing in the render pipeline consumes it yet (no e-paper display of tasks implemented).
- **`src/server/lib/google_auth.py`** is the shared OAuth2 credential loader used by both `google_calendar.py` and `google_tasks.py` at request time: it reads/refreshes `src/server/token.json` (gitignored) and never launches an interactive flow itself — it raises `RuntimeError` telling the caller to run `google_auth_setup.py` if no usable token exists. `src/server/google_auth_setup.py` (top-level, not in `lib/`, since it's a manually-run entry point) is the one-shot script that performs the actual OAuth device-flow consent (prints a URL + code the user approves from any browser, no SSH port-forwarding needed) and writes the initial `token.json`.
- **`src/server/lib/requestAPI.py`** has a generic `request_API()` GET helper, used for the holidays-jp API.
- **`src/server/lib/misakifont/`** is a vendored bitmap-font library for Japanese glyphs, used by `Draw.text()`.

## Notes for future changes

- `src/waveshare_epd/` and `src/server/epd_7in5b_V2_test.py` are treated as a known-good reference implementation — if the display stops working, diff against these rather than guessing at the driver/SPI layer.
- Because everything is one process, changing the byte layout `Draw` produces has no cross-repo contract to keep in sync (unlike the old client/server split) — `GET /draw` and `GET /calendar` can diverge freely as long as both still call into the same `Draw` canvases correctly.
