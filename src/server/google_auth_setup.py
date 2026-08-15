import json
import os
import time

import requests
from google.oauth2.credentials import Credentials

from secret import GOOGLE_OAUTH_CLIENT_SECRET_FILE
from lib import google_auth

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"
CLIENT_SECRET_FILE = os.path.join(os.path.dirname(__file__), GOOGLE_OAUTH_CLIENT_SECRET_FILE)


def _load_client_info():
    with open(CLIENT_SECRET_FILE) as f:
        data = json.load(f)
    # ダウンロードしたJSONのトップレベルキー("installed"等)に依存せず先頭の値を読む
    info = next(iter(data.values()))
    return info["client_id"], info["client_secret"]


def main():
    client_id, client_secret = _load_client_info()
    scope = " ".join(google_auth.SCOPES)

    resp = requests.post(DEVICE_CODE_URL, data={"client_id": client_id, "scope": scope}).json()
    device_code = resp["device_code"]
    interval = resp.get("interval", 5)

    print("以下のURLをブラウザ（どの端末でもOK）で開き、コードを入力してください:")
    print(f"  URL : {resp['verification_url']}")
    print(f"  コード: {resp['user_code']}")

    expires_at = time.time() + resp.get("expires_in", 1800)
    while time.time() < expires_at:
        time.sleep(interval)
        token_resp = requests.post(TOKEN_URL, data={
            "client_id": client_id,
            "client_secret": client_secret,
            "device_code": device_code,
            "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
        }).json()

        if "error" in token_resp:
            if token_resp["error"] == "authorization_pending":
                continue
            if token_resp["error"] == "slow_down":
                interval += 5
                continue
            raise RuntimeError(f"認証に失敗しました: {token_resp}")

        creds = Credentials(
            token=token_resp["access_token"],
            refresh_token=token_resp.get("refresh_token"),
            token_uri=TOKEN_URL,
            client_id=client_id,
            client_secret=client_secret,
            scopes=google_auth.SCOPES,
        )
        google_auth.save_credentials(creds)
        print(f"認証情報を保存しました: {google_auth.TOKEN_FILE}")
        return

    raise RuntimeError("認証がタイムアウトしました。もう一度実行してください。")


if __name__ == "__main__":
    main()
