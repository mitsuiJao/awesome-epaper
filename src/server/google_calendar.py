import datetime
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from secret import GOOGLE_CALENDAERID, GOOGLE_SERVICEACCOUNTFILE

SERVICE_ACCOUNT_FILE = GOOGLE_SERVICEACCOUNTFILE
CALENDAR_ID = GOOGLE_CALENDAERID


def get_calendar_events(service_account_file: str, calendar_id: str):
    SCOPES = ['https://www.googleapis.com/auth/calendar.readonly']

    creds = Credentials.from_service_account_file(service_account_file, scopes=SCOPES)
    
    # APIサービスを構築
    service = build('calendar', 'v3', credentials=creds)

    try:
        # 現在から10日後までのイベントを取得
        now = datetime.datetime.utcnow().isoformat() + 'Z'  # 'Z' indicates UTC time
        time_max = (datetime.datetime.utcnow() + datetime.timedelta(weeks=4)).isoformat() + 'Z'

        # print('今後10日間のイベントを取得中...')
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
        else:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                end = event['end'].get('dateTime', event['end'].get('date'))
                # print(f"{start} - {end}: {event['summary']}")
            return events
                
    except Exception as e:
        print(f"エラーが発生しました: {e}")

if __name__ == '__main__':
    get_calendar_events(SERVICE_ACCOUNT_FILE, CALENDAR_ID)