import os

from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials

TOKEN_FILE = os.path.join(os.path.dirname(__file__), "token.json")

SCOPES = [
    "https://www.googleapis.com/auth/calendar.readonly",
    "https://www.googleapis.com/auth/tasks.readonly",
]

_SETUP_HINT = "google_auth_setup.py を実行して認証をやり直してください。"


def get_credentials(scopes: list[str]) -> Credentials:
    if not os.path.exists(TOKEN_FILE):
        raise RuntimeError(f"token.json が見つかりません。{_SETUP_HINT}")

    creds = Credentials.from_authorized_user_file(TOKEN_FILE, scopes)

    if not creds.valid:
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except RefreshError as e:
                raise RuntimeError(f"トークンの更新に失敗しました。{_SETUP_HINT}") from e
            save_credentials(creds)
        else:
            raise RuntimeError(f"有効な認証情報がありません。{_SETUP_HINT}")

    return creds


def save_credentials(creds: Credentials) -> None:
    with open(TOKEN_FILE, "w") as f:
        f.write(creds.to_json())
