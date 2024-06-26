import requests
import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from xml.etree import ElementTree as ET

SCOPES = ['https://www.googleapis.com/auth/indexing']
VITRINA24KZ_CREDENTIALС = os.getenv('VITRINA24KZ_CREDENTIALС')
MEDVITRИНА24KZ_CREDENTIALС = os.getenv('MEDVITРИНА24KZ_CREDENTIALС')
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

def index_url(service, url):
    body = {
        "url": url,
        "type": "URL_UPDATED"
    }
    try:
        response = service.urlNotifications().publish(body=body).execute()
        print(f"Indexed {url}: {response}")
        return response
    except Exception as e:
        print(f"Error indexing {url}: {e}")
        return None

def check_indexed(service, url):
    try:
        response = service.urlNotifications().getMetadata(url=url).execute()
        if 'latestUpdate' in response:
            print(f"URL already indexed: {url}")
            return True
        else:
            print(f"URL not indexed: {url}")
            return False
    except Exception as e:
        print(f"Error checking index status for {url}: {e}")
        return False

def load_links(file_path):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            return file.readlines()
    return []

def save_links(file_path, links):
    with open(file_path, 'w') as file:
        file.writelines(links)

def fetch_sitemap_links(sitemap_url):
    try:
        response = requests.get(sitemap_url)
        if response.status_code == 200:
            root = ET.fromstring(response.content)
            links = []
            for elem in root:
                if elem.tag.endswith('sitemap'):
                    for loc in elem:
                        if loc.tag.endswith('loc'):
                            links += fetch_sitemap_links(loc.text)
                elif elem.tag.endswith('url'):
                    for loc in elem:
                        if loc.tag.endswith('loc'):
                            links.append(loc.text + "\n")
            print(f"Fetched {len(links)} links from {sitemap_url}")
            return links
        else:
            print(f"Failed to fetch sitemap from {sitemap_url}, status code: {response.status_code}")
    except Exception as e:
        print(f"Error fetching sitemap from {sitemap_url}: {e}")
    return []

def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=data)
    return response

def main():
    print("Starting indexing process")
    vitrina_service = get_service(VITRINA24KZ_CREDENTIALС)
    med_service = get_service(MEDVITРИНА24KZ_CREDENTIALС)

    indexed_links = load_links('indexed_links.txt')
    failed_links = load_links('failed_links.txt')
    links_to_index = load_links('links_to_index.txt')

    if not links_to_index:
        vitrina_links_to_index = fetch_sitemap_links('https://vitrina24.kz/sitemap.xml')
        med_links_to_index = fetch_sitemap_links('https://med.vitrina24.kz/sitemap.xml')
        links_to_index = vitrina_links_to_index + med_links_to_index
        save_links('links_to_index.txt', links_to_index)

    print(f"Fetched {len(links_to_index)} links to index")

    vitrina_indexed_count = 0
    med_indexed_count = 0
    total_indexed_count = 0

    links_to_index = [url.strip() for url in links_to_index]

    for url in links_to_index:
        if total_indexed_count >= 200:
            break
        if url not in indexed_links and url not in failed_links:
            print(f"Checking if URL is indexed: {url}")
            is_indexed = check_indexed(vitrina_service, url) or check_indexed(med_service, url)
            if not is_indexed:
                print(f"Indexing URL: {url}")
                if "vitrina24.kz" in url:
                    response = index_url(vitrina_service, url)
                    if response:
                        vitrina_indexed_count += 1
                elif "med.vitrina24.kz" in url:
                    response = index_url(med_service, url)
                    if response:
                        med_indexed_count += 1
                if response:
                    indexed_links.append(url + "\n")
                    total_indexed_count += 1
                else:
                    failed_links.append(url + "\n")
            else:
                indexed_links.append(url + "\n")

    save_links('indexed_links.txt', indexed_links)
    save_links('failed_links.txt', failed_links)

    print(f"Indexing process completed, {total_indexed_count} links indexed")

    # Отправка сообщения в Telegram
    message = (
        f"vitrina24.kz - отправлено {vitrina_indexed_count} ссылок из 200.\n"
        f"med.vitrina24.kz - отправлено {med_indexed_count} ссылок из 200."
    )
    send_telegram_message(message)

    # Удаление обработанных ссылок из списка для индексирования
    remaining_links = links_to_index[total_indexed_count:]
    save_links('links_to_index.txt', remaining_links)

if __name__ == "__main__":
    main()
