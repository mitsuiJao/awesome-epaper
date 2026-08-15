## 概要

Waveshare 7.5inch e-paper B（黒/白/赤）にGoogleカレンダーの予定を表示するプロジェクト。

Raspberry Pi（e-paper HATが物理結線されたマシン）上でFastAPIサーバを1プロセス動かし、スマホのブラウザで `/` を開くとダッシュボードが表示される。calendar/image/test/clearの4モードから選んで「draw!」を押すと、その場で描画→実機表示まで完結する。定期自動更新は今のところ無く、手動トリガーのみ。描画するたびに結果のプレビューPNGが `src/server/img/image.png` に同じファイル名で上書き保存される。

```
src/
├── waveshare_epd/        # Waveshare純正ドライバ（SPI/GPIO）
├── clear.py              # e-paperを白紙に戻す手動ユーティリティ
└── server/
    ├── main.py            # FastAPIアプリ（/, /draw, /draw/clear, /draw/test, /draw/image, /calendar）
    ├── static/index.html  # スマホ向けダッシュボード（mode選択 + draw!ボタン）
    ├── epd_7in5b_V2_test.py  # ハードウェア疎通確認用デモ
    ├── pic/                   # 上記デモが使うフォント/bmp
    ├── draw.py            # 800x480の黒面/赤面キャンバスへの描画エンジン
    ├── draw_calendar.py   # カレンダー画面の組み立て
    ├── google_calendar.py # Googleカレンダーからの予定取得
    ├── requestAPI.py      # 祝日API等の汎用GETヘルパー
    ├── misakifont/        # 日本語ビットマップフォント
    └── img/                # プレビューPNGの書き出し先（毎回image.pngを上書き）
```

## セットアップ（Raspberry Pi上）

### 1. Python仮想環境を作る

```bash
cd ~/epaper
python -m venv .venv
source .venv/bin/activate
```

### 2. 必要なPythonパッケージを入れる

`spidev`はCコンパイルが必要なので、先にビルド環境を入れておく。

```bash
sudo apt install -y python3-dev build-essential swig
pip install -r requirements.txt
```

（`python3-dev`が無いと`Python.h: No such file or directory`でビルドに失敗する）

### 3. SPIを有効化する

```bash
sudo raspi-config
```
Interface Options → SPI → Enable。有効化後は一度再起動しておくと確実。

```bash
sudo reboot
```

### 4. lgpioを入れる（GPIO制御用）

`gpiozero`はデフォルトだとlgpio/RPi.GPIO/pigpioのどれかを探しにいくが、どれも無いと不安定な`NativeFactory`にフォールバックしてGPIOアクセスに失敗する。lgpioを入れて解消する。

`liblgpio`本体（Cライブラリ）はpip版だけでは入らないので、ソースからビルド。

```bash
cd ~
git clone https://github.com/joan2937/lg.git
cd lg
make
sudo make install
sudo ldconfig
```
※インストールログの最後にPython3用セットアップ（PY_LGPIO/PY_RGPIO）が`setuptools`不足で失敗すると出るが、`requirements.txt`側でvenvに入れているので無視してよい。

### 5. ハードウェア疎通確認

```bash
cd ~/epaper
PYTHONPATH=src python src/server/epd_7in5b_V2_test.py
```

（`waveshare_epd` は `src/` 直下の共有ドライバなので、`src/server/`から見ると一つ上の階層になる。`PYTHONPATH=src` でそれを解決している。）

`PinFactoryFallback`の警告が出ず、`Drawing on the Horizontal image`〜`Goto Sleep`まで進めば成功。

### 6. Googleカレンダー連携の準備

GCPでサービスアカウントを作成し、認証情報JSONを `src/server/` に配置する。次に:

```bash
cd ~/epaper/src/server
cp secret.py.example secret.py
```

`secret.py` を編集し、`GOOGLE_SERVICEACCOUNTFILE`（JSONファイル名）と `GOOGLE_CALENDAERID`（カレンダーID）を実際の値に書き換える。`secret.py` とサービスアカウントJSONは`.gitignore`済み。

### 7. サーバを起動する

```bash
cd ~/epaper
source .venv/bin/activate
uvicorn main:app --app-dir src/server
```

`--port` オプションでポート番号を指定できる（デフォルト8000）。スマホから同一LAN内のPiにアクセスし `http://<Piのアドレス>:8000/` を開いて「今すぐ描画」を押すと更新される。

systemdに登録して起動時に自動実行させると便利。

## エンドポイント

- `GET /` — スマホ向けダッシュボード（`src/server/static/index.html`）。calendar/image/test/clearの4モードを選んで「draw!」を押すと、選択中モードに応じたエンドポイントをJSで叩く。
- `GET /draw` — カレンダーを再描画し、そのまま実機のe-paperに表示する。
- `POST /draw/clear` — e-paperを白紙にクリアする（`src/clear.py`と同じ処理）。
- `POST /draw/test` — グリッド + サンプルテキストのテストパターンを実機に表示する（`src/server/epd_7in5b_V2_test.py`とは別実装）。
- `POST /draw/image` — アップロードされた画像（`multipart/form-data`、フィールド名`file`）を800x480に切り抜き・リサイズして実機に表示する。
- `GET /calendar` — 描画結果を黒面/赤面のバイト列として返す（デバッグ・プレビュー用、実機表示はしない）。

`/draw`系エンドポイントはいずれも呼ぶたびに `src/server/img/image.png` にプレビュー画像を同じファイル名で上書き保存する。
