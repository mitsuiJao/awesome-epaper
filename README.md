## 概要

Waveshare 7.5inch e-paper B（黒/白/赤）にGoogleカレンダーの予定を表示するプロジェクト。

Raspberry Pi（e-paper HATが物理結線されたマシン）上でFastAPIサーバを1プロセス動かし、スマホのブラウザで `/` を開くとダッシュボードが表示される。calendar/image/test/clearの4モードから選んで「draw!」を押すと、その場で描画→実機表示まで完結する。定期自動更新は今のところ無く、手動トリガーのみ。描画するたびに結果のプレビューPNGが `src/img/image.png` に同じファイル名で上書き保存される。

`src/` はそのままFastAPIアプリのルート（`--app-dir src`）。`waveshare_epd/` はサーバから見て単なる隣接パッケージとして直接importできる。

```
src/
├── waveshare_epd/        # Waveshare純正ドライバ（SPI/GPIO）
├── clear.py              # e-paperを白紙に戻す手動ユーティリティ
├── main.py               # FastAPIアプリ（/, /draw, /draw/clear, /draw/test, /draw/image, /calendar）
├── google_auth_setup.py  # 初回のみ手動実行するOAuth認証（SSHポートフォワード経由、token.json生成）
├── epd_7in5b_V2_test.py  # ハードウェア疎通確認用デモ
├── secret.py.example     # secret.pyのひな形（実体はgitignore対象）
├── static/index.html     # スマホ向けダッシュボード（mode選択 + draw!ボタン）
├── pic/                  # epd_7in5b_V2_test.pyが使うフォント/bmp
├── img/                  # プレビューPNGの書き出し先（毎回image.pngを上書き）
└── lib/                  # 描画エンジン・データ取得まわりの実装一式
    ├── draw.py              # 800x480の黒面/赤面キャンバスへの描画エンジン
    ├── draw_calendar.py     # カレンダー画面の組み立て
    ├── google_calendar.py   # Googleカレンダーからの予定取得
    ├── google_tasks.py      # Google Tasksからのタスク取得（表示側は未実装）
    ├── google_auth.py       # Calendar/Tasks共通のOAuth2認証情報ロード・更新・永続化
    ├── epd_backend.py       # EPD_MODEで実機/開発モックを切り替えるEPD生成
    ├── requestAPI.py        # 祝日API等の汎用GETヘルパー
    └── misakifont/          # 日本語ビットマップフォント
```


## env
必要に応じて以下のリポジトリからドライバー置き換えてください

https://github.com/waveshareteam/e-Paper/tree/master/RaspberryPi_JetsonNano/python/lib/waveshare_epd


画像サイズとかも多分変わっちゃうけど、変更してみて


## セットアップ（Raspberry Pi上）

### 1. Python仮想環境を作る

```bash
cd ~/epaper
python -m venv .venv
source .venv/bin/activate
```

### 2. 必要なPythonパッケージを入れる

```bash
pip install -r requirements.txt
```

`requirements.txt` は開発ホストでも実機（Raspberry Pi）でも共通の最小構成（FastAPI/画像処理/Google API等。OAuth認証で使う`google-auth-oauthlib`もここに含まれる）。この段階でも`main.py`はハードウェア無しで起動できる（後述の`EPD_MODE`参照）。

実機でe-paperに実際に描画するには、追加でハードウェア制御パッケージ（`spidev`/`gpiozero`/`lgpio`、および`gpiozero`の依存の`colorzero`）を入れる。`spidev`はCコンパイルが必要なので、先にビルド環境を入れておく。

```bash
sudo apt install -y python3-dev build-essential swig
pip install -r requirements-hardware.txt
```

（`python3-dev`が無いと`Python.h: No such file or directory`でビルドに失敗する）

#### 実機用と開発用の違い（EPD_MODE）

`main.py`は環境変数`EPD_MODE`でe-paperへの出力先を切り替える。FastAPIのエンドポイント・描画ロジック自体はどちらのモードでも完全に同じで、分岐するのは最後にハードウェアへ実際に描画するかどうかだけ。

- 未設定（デフォルト）＝実機モード。従来通りPi上の物理ディスプレイに描画する。`requirements-hardware.txt`のインストールと、以降のSPI/lgpioのセットアップ（手順3・4）が必要。
- `EPD_MODE=mock`＝開発モード。`waveshare_epd`（ハードウェア制御ドライバ）には一切触れず、`/draw`系エンドポイントを叩くたびに`img/image.png`へプレビュー保存されるだけになる。開発ホストでは`requirements-hardware.txt`もSPI/lgpioのセットアップも不要で、`requirements.txt`だけで動く。

```bash
cd src
EPD_MODE=mock uvicorn main:app --app-dir .
```

### 3. SPIを有効化する（実機のみ）

```bash
sudo raspi-config
```
Interface Options → SPI → Enable。有効化後は一度再起動しておくと確実。

```bash
sudo reboot
```

### 4. lgpioを入れる（GPIO制御用・実機のみ）

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
python src/epd_7in5b_V2_test.py
```

（`waveshare_epd` は `src/` 直下の隣接パッケージなので、スクリプト自身のディレクトリ（`sys.path[0]`）から素直にimportできる。`PYTHONPATH`の指定は不要。）

`PinFactoryFallback`の警告が出ず、`Drawing on the Horizontal image`〜`Goto Sleep`まで進めば成功。

### 6. Google Calendar / Tasks 連携の準備

Google TasksはサービスアカウントではAPIを叩けない（個人アカウント向けAPIのため、ドメイン全体の委任が使えない）ため、OAuth2のユーザー本人同意フローで認証情報を得る方式にしている。カレンダーとタスクは同じ`token.json`（1つの認証情報）を共有する。

`tasks.readonly`のようなセンシティブスコープは、OAuth2のDevice Authorization Grant（デバイス認可フロー、いわゆる「どの端末でもOKなURL+コード入力」方式）では`invalid_scope`エラーになり取得できない（Google側の制限）。そのため`google-auth-oauthlib`の`InstalledAppFlow`（`run_local_server()`）を使い、SSHのローカルポートフォワード経由でPi上で直接ブラウザ同意を完了させる方式にしている。

#### 6-1. GCP側の準備

1. GCP ConsoleでCalendar APIとTasks APIの両方を有効化する。
2. 「認証情報を作成」→「OAuthクライアントID」→種類は**デスクトップ アプリ**を選択して作成する（`InstalledAppFlow`のループバックリダイレクト`http://localhost:<port>/...`に対応する種類）。
3. 発行されたクライアントシークレットJSONをダウンロードし、`src/`に配置する（ファイル名は任意、下記`secret.py`で指定）。

#### 6-2. secret.pyの準備

```bash
cd ~/epaper/src
cp secret.py.example secret.py
```

`secret.py` を編集し、`GOOGLE_OAUTH_CLIENT_SECRET_FILE`（ダウンロードしたJSONのファイル名）と `GOOGLE_CALENDAERID`（カレンダーID）を実際の値に書き換える。`secret.py`・クライアントシークレットJSON・後述の`token.json`はいずれも`.gitignore`済み。

#### 6-3. 初回認証（手動・1回だけ）

RaspberryPiはヘッドレスでブラウザが無いため、SSHのローカルポートフォワードで手元の端末のブラウザとPi上のリスナーをつなぐ。**デバイス認可フローと違い、SSHポートフォワードを張った端末のブラウザでないと認証できない**（任意の端末では不可）。

1. 手元の端末（Piと直接SSH接続する端末）から、ローカルポートフォワード付きでPiにSSH接続する。ポート番号は`google_auth_setup.py`側の`port=43211`と一致させる。

   ```bash
   ssh -L 43211:localhost:43211 pi@<Piのアドレス>
   ```

2. そのSSHセッション内（＝Pi上）で認証スクリプトを実行する。

   ```bash
   cd ~/epaper
   source .venv/bin/activate
   cd src
   python google_auth_setup.py
   ```

3. コンソールに表示されるURLを、**手順1でポートフォワードを張った手元の端末のブラウザ**で開き、Googleの同意画面を完了する。ブラウザは`http://localhost:43211/...`にリダイレクトされ、SSHトンネル経由でPi上のリスナーに届く。スクリプトが自動的に検知し、`src/lib/token.json`を生成して終了する。以降のサーバ起動時はこのファイルから自動的に（必要ならリフレッシュして）認証情報を読み込む。ブラウザ操作は不要になる。

`token.json`の中身が失効・取り消しされた場合（`RuntimeError`がログに出る）は、`google_auth_setup.py`を再実行すれば良い。

### 7. サーバを起動する

```bash
cd ~/epaper
source .venv/bin/activate
uvicorn main:app --app-dir src

EPD_MODE=mock uvicorn main:app --app-dir src
```

`--port` オプションでポート番号を指定できる（デフォルト8000）。スマホから同一LAN内のPiにアクセスし `http://<Piのアドレス>:8000/` を開いて「今すぐ描画」を押すと更新される。`EPD_MODE`は実機では未設定のままでよい（デフォルトが実機モード）。

systemdに登録して起動時に自動実行させると便利。`Environment=EPD_MODE=real`をunitファイルに明示しておくと、実機での起動であることが分かりやすい（省略しても既定値なので動作は変わらない）。

## エンドポイント

- `GET /` — スマホ向けダッシュボード（`src/static/index.html`）。calendar/image/test/clearの4モードを選んで「draw!」を押すと、選択中モードに応じたエンドポイントをJSで叩く。
- `GET /draw` — カレンダーを再描画し、そのまま実機のe-paperに表示する。
- `POST /draw/clear` — e-paperを白紙にクリアする（`src/clear.py`と同じ処理）。
- `POST /draw/test` — グリッド + サンプルテキストのテストパターンを実機に表示する（`src/epd_7in5b_V2_test.py`とは別実装）。
- `POST /draw/image` — アップロードされた画像（`multipart/form-data`、フィールド名`file`）を800x480に切り抜き・リサイズして実機に表示する。
- `GET /calendar` — 描画結果を黒面/赤面のバイト列として返す（デバッグ・プレビュー用、実機表示はしない）。

`/draw`系エンドポイントはいずれも呼ぶたびに `src/img/image.png` にプレビュー画像を同じファイル名で上書き保存する。
