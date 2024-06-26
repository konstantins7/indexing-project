import requests
import json
import os

# Настройка аутентификации для Google API
from google.oauth2 import service_account
from googleapiclient.discovery import build

SCOPES = ['https://www.googleapis.com/auth/indexing']
VITRINA24KZ_CREDENTIALS = os.getenv('VITRINA24KZ_CREDENTIALS')
MEDVITRINA24KZ_CREDENTIALS = os.getenv('MEDVITRINA24KZ_CREDENTIALS')

def get_service(credentials_file):
    credentials = service_account.Credentials.from_service_account_file(
        credentials_file, scopes=SCOPES)
    service = build('indexing', 'v3', credentials=credentials)
    return service

def index_url(service, url):
    body = {
        "url": url,
        "type": "URL_UPDATED"
    }
    try:
        response = service.urlNotifications().publish(body=body).execute()
        return response
    except Exception as e:
        print(f"Error indexing {url}: {e}")
        return None

def load_links(file_path):
    with open(file_path, 'r') as file:
        return file.readlines()

def save_links(file_path, links):
    with open(file_path, 'w') as file:
        file.writelines(links)

def main():
    vitrina_service = get_service(VITRINA24KZ_CREDENTIALS)
    med_service = get_service(MEDVITRINA24KZ_CREDENTIALS)

    indexed_links = load_links('indexed_links.txt')
    failed_links = load_links('failed_links.txt')

    links_to_index = []  # Добавьте логику для получения ссылок из sitemap

    indexed_count = 0
    for url in links_to_index:
        if indexed_count >= 200:
            break
        response = index_url(vitrina_service, url) or index_url(med_service, url)
        if response:
            indexed_links.append(url + "\n")
            indexed_count += 1
        else:
            failed_links.append(url + "\n")

    save_links('indexed_links.txt', indexed_links)
    save_links('failed_links.txt', failed_links)

if __name__ == "__main__":
    main()
