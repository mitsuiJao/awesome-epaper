from googleapiclient.discovery import build

from . import google_auth

SCOPES = ['https://www.googleapis.com/auth/tasks.readonly']


def get_tasks(tasklist_id: str = '@default', max_results: int = 20):
    creds = google_auth.get_credentials(SCOPES)
    service = build('tasks', 'v1', credentials=creds)
    try:
        tasks_result = service.tasks().list(
            tasklist=tasklist_id, showCompleted=False, maxResults=max_results
        ).execute()
        items = tasks_result.get('items', [])
        if not items:
            print('タスクが見つかりませんでした。')
        return items
    except Exception as e:
        print(f"エラーが発生しました: {e}")
        return None


if __name__ == '__main__':
    print(get_tasks())
