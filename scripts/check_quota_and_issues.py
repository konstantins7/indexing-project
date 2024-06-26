import requests
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/indexing']
VITRINA24KZ_CREDENTIALS = os.getenv('VITRINA24KZ_CREDENTIALS')
MEDVITRINA24KZ_CREDENTIALS = os.getenv('MEDVITRINA24KZ_CREDENTIALS')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

def get_service(credentials_json):
    with open('temp_credentials.json', 'w') as f:
        f.write(credentials_json)
    credentials = service_account.Credentials.from_service_account_file(
        'temp_credentials.json', scopes=SCOPES)
    service = build('indexing', 'v3', credentials=credentials)
    os.remove('temp_credentials.json')
    return service

def check_quota(service):
    try:
        # Реализуйте вызов для проверки квоты, если такая возможность есть
        # Пример: response = service.usage().quota().execute()
        # Вернем True если квота превышена, False если все в порядке
        return False
    except Exception as e:
        print(f"Error checking quota: {e}")
        return True

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=data)
    return response

def main():
    vitrina_service = get_service(VITRINA24KZ_CREDENTIALS)
    med_service = get_service(MEDVITRINA24KZ_CREDENTIALS)

    if check_quota(vitrina_service) or check_quota(med_service):
        send_telegram_message("Quota exceeded or issue detected.")

    # Добавьте любую дополнительную логику для проверки проблем
    issues = []

    if issues:
        for issue in issues:
            send_telegram_message(f"Issue detected: {issue}")

if __name__ == "__main__":
    main()
