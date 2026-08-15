# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository layout

This is a single repository. Everything lives under `src/`, and it all runs on one machine: a Raspberry Pi with a Waveshare 7.5" B (black/white/red) e-paper HAT wired to it over SPI/GPIO. `src/` is a flat FastAPI app root (there is no separate `server/` subdirectory — the app used to live one level deeper under `src/server/`, but that split added no value since everything in this repo runs as a single process on the Pi, so it was dissolved and its contents moved directly under `src/`); `waveshare_epd/` sits alongside it as a plain sibling package.

- **`src/waveshare_epd/`** — vendored Waveshare driver for the display (`epd7in5b_V2.py` + `epdconfig.py`), talking SPI/GPIO via a `RaspberryPi` config class. This is the known-good, working driver — do not modify it. It stays directly under `src/` because it's a shared module imported by both `src/lib/epd_backend.py` (lazily, only in real-hardware mode — see below) and `src/epd_7in5b_V2_test.py`; being a plain sibling of both under `src/`, it's importable without any `sys.path` manipulation once `src/` itself is on `sys.path` (via uvicorn's `--app-dir src`, or via `sys.path[0]` for direct script invocation).
- **`src/epd_7in5b_V2_test.py`** — Waveshare's stock hardware smoke-test demo (draws sample text/shapes, then a bmp, then clears). Used to verify the HAT is wired correctly. The demo body is wrapped in a `run_demo()` function so `main.py` can call it directly (see `POST /draw/test` below); the drawing sequence itself is unchanged and still treated as the known-good reference — only the entry point was changed to make it importable. The `waveshare_epd` import is lazy (inside `run_demo()`, not at module level) so importing this file never touches hardware detection unless `run_demo()` actually runs. Standalone invocation (`if __name__ == '__main__'`) resolves `waveshare_epd` via `sys.path[0]` (its own directory, `src/`, which directly contains `waveshare_epd/`) — no `PYTHONPATH` needed; see README for the exact command.
- **`src/pic/`** — fonts/bitmaps used only by `epd_7in5b_V2_test.py`.
- **`src/clear.py`** — one-shot manual utility that clears the panel (`epd.init()` → `epd.Clear()` → `epd.sleep()`).
- **`src/main.py`** — the FastAPI app that renders a calendar view and drives the physical display, in a single process, in the same request handler. There is no separate client/server split and no bitmap transfer over HTTP — rendering and display live in the same Python process because the app runs directly on the Pi that owns the hardware. `GET /` serves a small dashboard (`static/index.html`) with four modes (calendar/image/test/clear); each draw action saves a preview PNG to `src/img/image.png`, overwritten on every call. Only entry points (`main.py`, `google_auth_setup.py`, `epd_7in5b_V2_test.py`) and config (`secret.py`/`secret.py.example`) sit directly under `src/`; the rendering engine and data-fetch modules live in `src/lib/` (an explicit package — `src/lib/__init__.py` exists, and modules inside it import each other with relative imports, e.g. `from . import google_auth`). `src/lib` is importable because `src/` itself is always on `sys.path` — either via uvicorn's `--app-dir src`, or because `google_auth_setup.py` is run directly from within `src/` (making it `sys.path[0]`).

Weather rendering is not implemented (it was dropped; only the calendar view exists).

## Commands

Run from the repository root, with a venv set up per `README.md`. `requirements.txt` (FastAPI/Pillow/Google-API deps) is shared by dev hosts and the real device; `requirements-hardware.txt` (`spidev`/`gpiozero`/`lgpio`/`colorzero`) is only needed on the real Raspberry Pi, since it's only imported when `EPD_MODE` selects the real backend (see `lib/epd_backend.py` below):

```shell
uvicorn main:app --app-dir src   # add --port to change from the default 8000
# on a dev host without the display attached:
EPD_MODE=mock uvicorn main:app --app-dir src
```

Requires `src/secret.py` (copy from `src/secret.py.example` and fill in real values) and the GCP OAuth client-secret JSON it points to — both gitignored, must be created manually. Also requires a one-time interactive `src/google_auth_setup.py` run to produce `src/lib/token.json` (OAuth `InstalledAppFlow` consent via SSH port-forward; see README.md) before Calendar/Tasks calls will work.

Hardware smoke test (no automated test suite exists in this repo):

```shell
python src/epd_7in5b_V2_test.py
```

## Architecture

### `src/main.py` — FastAPI endpoints

- **`GET /`** — serves `static/index.html`, a dashboard with a mode radio group (calendar/image/test/clear) and a "draw!" button. The page's JS calls the matching endpoint below based on the selected mode.
- **`GET /draw`** — calendar mode: builds `DrawCalendar()`, renders, then pushes to the display via the shared `push_to_epd()` helper (`epd.init()` → `epd.display(epd.getbuffer(...), epd.getbuffer(...))` → `epd.sleep()`, where `epd` comes from `get_epd()`). Defined as a sync `def` (not `async def`) since the SPI calls are blocking; FastAPI runs sync handlers in a thread pool.
- **`POST /draw/clear`** — clears the panel (same sequence as `src/clear.py`), also via `get_epd()`.
- **`POST /draw/test`** — imports and calls `run_demo()` from `src/epd_7in5b_V2_test.py` directly, bypassing `push_to_epd()`/`get_epd()`/`EPD_MODE` entirely. It always talks to real hardware and does not update the preview PNG (the demo draws several intermediate frames itself, not a single black/red image pair). On a non-Pi host this endpoint fails with a 500 when hit, but the lazy import inside `run_demo()` means it doesn't affect server startup or any other endpoint in `EPD_MODE=mock`.
- **`POST /draw/image`** — accepts a `multipart/form-data` upload (`file` field), crops/resizes it to 800x480 with `PIL.ImageOps.fit`, dithers it to black/white itself via `Image.convert('1')` (Floyd–Steinberg, PIL's default), then pushes it (red plane left blank) through `push_to_epd()`. Converting before `push_to_epd()` (rather than leaving it to `EPD.getbuffer()`, which also calls `convert('1')` internally but is a no-op on an already-1-bit image) means the saved preview PNG reflects the actual dithered black/white result the hardware will show, not the original color photo — this also makes `EPD_MODE=mock` useful for iterating on dithering/crop behavior without real hardware.
- **`push_to_epd(blackimage, redimage)`** — shared helper used by all four draw actions above: saves a preview PNG (`save_preview()`) then does the `epd.init()`/`epd.display()`/`epd.sleep()` sequence against whatever `get_epd()` returns. There is no scheduled/automatic redraw — refresh is manual only, triggered from the dashboard.
- **`save_preview(blackimage, redimage)`** — merges the black/red planes into an RGB image and overwrites `src/img/image.png` (path anchored to `os.path.dirname(__file__)`, independent of the process's CWD; `IMG_DIR` is created with `os.makedirs(exist_ok=True)` if missing, since `img/` isn't tracked in git). Called on every `/draw*` action and by `GET /calendar`.
- **`GET /calendar`** — debug/preview endpoint: returns the rendered black-plane + red-plane bitmap bytes (`black_bytes + red_bytes`) as `application/octet-stream`. Does not touch the hardware.

### Render pipeline

- **`src/lib/draw.py` (`Draw`)** is the shared rendering engine. It holds two 800×480 1-bit PIL canvases (`blackimage`/`redimage`) and exposes `text()`, `line()`, `img_pil()`/`img_path()`, and `to_bytes()`/`_save()`. `text()` is a custom bitmap-font renderer: ASCII characters come from the `fontdata` table (8×8 glyphs), non-ASCII (Japanese) characters are rendered via `lib/misakifont/`. All higher-level drawing goes through this class. `GET /draw` uses `blackimage`/`redimage` directly (via `epd.getbuffer()`) rather than `to_bytes()`, since there's no wire transfer to round-trip through.
- **`src/lib/draw_calendar.py` (`DrawCalendar`)** composes the calendar view: current month grid (weekends/holidays in red, via the `holidays-jp` API through `requestAPI.request_API`), today's date, and upcoming Google Calendar events (via `google_calendar.py`).
- **`src/lib/google_calendar.py`** pulls events from a Google Calendar via shared OAuth2 credentials (see below). It imports `GOOGLE_CALENDAERID` from a local, untracked `secret.py` (not in the repo — must be created manually from `secret.py.example`).
- **`src/lib/google_tasks.py`** pulls tasks from the user's default Google Tasks list via the same shared OAuth2 credentials. Fetch-only — nothing in the render pipeline consumes it yet (no e-paper display of tasks implemented).
- **`src/lib/google_auth.py`** is the shared OAuth2 credential loader used by both `google_calendar.py` and `google_tasks.py` at request time: it reads/refreshes `src/lib/token.json` (gitignored) and never launches an interactive flow itself — it raises `RuntimeError` telling the caller to run `google_auth_setup.py` if no usable token exists. `src/google_auth_setup.py` (top-level, not in `lib/`, since it's a manually-run entry point) is the one-shot script that performs the actual OAuth consent via `google-auth-oauthlib`'s `InstalledAppFlow.run_local_server()` and writes the initial `token.json`. It must be run directly on the Pi over an SSH session with local port forwarding (`ssh -L 8080:localhost:8080 ...`) so the loopback redirect (`http://localhost:8080/...`) reaches the listener; this replaced an earlier Device Authorization Grant flow, which Google rejects for sensitive scopes like `tasks.readonly` (`invalid_scope`).
- **`src/lib/epd_backend.py`** — `get_epd()` selects the EPD implementation used by `main.py` based on the `EPD_MODE` env var: unset/`real` (default) lazily imports and returns `waveshare_epd.epd7in5b_V2.EPD()`; `mock` returns a no-op `MockEPD` (same `init()`/`getbuffer()`/`display()`/`Clear()`/`sleep()` interface) so `main.py` and its FastAPI endpoints run unchanged on a dev host — `save_preview()` still writes `img/image.png` either way, only the actual hardware push is skipped. The `waveshare_epd` import is lazy specifically so importing `main.py` never touches it (and never triggers `waveshare_epd/epdconfig.py`'s Raspberry-Pi detection) unless the real backend is actually selected.
- **`src/lib/requestAPI.py`** has a generic `request_API()` GET helper, used for the holidays-jp API.
- **`src/lib/misakifont/`** is a vendored bitmap-font library for Japanese glyphs, used by `Draw.text()`.

## Notes for future changes

- `src/waveshare_epd/` and the drawing sequence inside `epd_7in5b_V2_test.py`'s `run_demo()` are treated as a known-good reference implementation — if the display stops working, diff against these rather than guessing at the driver/SPI layer. `run_demo()` is now also live-called by `POST /draw/test`, so changes to it affect that endpoint directly.
- Because everything is one process, changing the byte layout `Draw` produces has no cross-repo contract to keep in sync (unlike the old client/server split) — `GET /draw` and `GET /calendar` can diverge freely as long as both still call into the same `Draw` canvases correctly.
