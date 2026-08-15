import os

from google_auth_oauthlib.flow import InstalledAppFlow

from secret import GOOGLE_OAUTH_CLIENT_SECRET_FILE
from lib import google_auth

CLIENT_SECRET_FILE = os.path.join(os.path.dirname(__file__), GOOGLE_OAUTH_CLIENT_SECRET_FILE)


def main():
    flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, scopes=google_auth.SCOPES)

    print("SSHポートフォワード先のブラウザで以下のURLを開いて認証してください:")
    creds = flow.run_local_server(port=43211, open_browser=False)

    google_auth.save_credentials(creds)
    print(f"認証情報を保存しました: {google_auth.TOKEN_FILE}")


if __name__ == "__main__":
    main()
