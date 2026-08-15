import datetime
from googleapiclient.discovery import build
from secret import GOOGLE_CALENDAERID
from . import google_auth

CALENDAR_ID = GOOGLE_CALENDAERID
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']


def get_calendar_events(calendar_id: str = CALENDAR_ID):
    creds = google_auth.get_credentials(SCOPES)

    # APIサービスを構築
    service = build('calendar', 'v3', credentials=creds)

    try:
        # 現在から4週間後までのイベントを取得
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        time_max = (datetime.datetime.utcnow() + datetime.timedelta(weeks=4)).isoformat() + 'Z'

        events_result = service.events().list(
            calendarId=calendar_id,
            timeMin=now,
            timeMax=time_max,
            singleEvents=True,
            orderBy='startTime',
            maxResults=5
        ).execute()

        events = events_result.get('items', [])

        if not events:
            print('イベントが見つかりませんでした。')

        return events

    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None

if __name__ == '__main__':
    print(get_calendar_events())
