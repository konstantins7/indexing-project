import requests
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from xml.etree import ElementTree as ET

SCOPES = ['https://www.googleapis.com/auth/indexing']
VITRINA24KZ_CREDENTIALS = os.getenv('VITRINA24KZ_CREDENTIALS')
MEDVITRINA24KZ_CREDENTIALS = os.getenv('MEDVITRINA24KZ_CREDENTIALS')

def get_service(credentials_json):
    with open('temp_credentials.json', 'w') as f:
        f.write(credentials_json)
    credentials = service_account.Credentials.from_service_account_file(
        'temp_credentials.json', scopes=SCOPES)
    service = build('indexing', 'v3', credentials=credentials)
    os.remove('temp_credentials.json')
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
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.readlines()
    return []

def save_links(file_path, links):
    with open(file_path, 'w') as file:
        file.writelines(links)

def fetch_sitemap_links(sitemap_url):
    response = requests.get(sitemap_url)
    if response.status_code == 200:
        root = ET.fromstring(response.content)
        return [url.find('loc').text + "\n" for url in root.findall('.//url')]
    return []

def main():
    vitrina_service = get_service(VITRINA24KZ_CREDENTIALS)
    med_service = get_service(MEDVITRINA24KZ_CREDENTIALS)

    indexed_links = load_links('indexed_links.txt')
    failed_links = load_links('failed_links.txt')

    links_to_index = fetch_sitemap_links('https://vitrina24.kz/sitemap.xml')
    links_to_index += fetch_sitemap_links('https://med.vitrina24.kz/sitemap.xml')

    indexed_count = 0
    for url in links_to_index:
        if indexed_count >= 200:
            break
        if url not in indexed_links and url not in failed_links:
            response = index_url(vitrina_service, url.strip()) or index_url(med_service, url.strip())
            if response:
                indexed_links.append(url)
                indexed_count += 1
            else:
                failed_links.append(url)

    save_links('indexed_links.txt', indexed_links)
    save_links('failed_links.txt', failed_links)

if __name__ == "__main__":
    main()
