import requests
import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from xml.etree import ElementTree as ET

SCOPES = ['https://www.googleapis.com/auth/indexing']
VITRINA24KZ_CREDENTIALС = os.getenv('VITRINA24KZ82FD975FBBE4')
MEDVITRINA24KZ_CREDENTIALС = os.getenv('MEDVITRINA24KZ61856B49EC6E')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')

def get_service(credentials_json, service_name):
    if not credentials_json:
        raise ValueError(f"Missing credentials for {service_name}")
    print(f"Loading credentials for {service_name}: {credentials_json[:30]}...")  # Отладочная информация
    with open(f'temp_credentials_{service_name}.json', 'w') as f:
        f.write(credentials_json)
    credentials = service_account.Credentials.from_service_account_file(
        f'temp_credentials_{service_name}.json', scopes=SCOPES)
    service = build('indexing', 'v3', credentials=credentials)
    os.remove(f'temp_credentials_{service_name}.json')
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
            print(f"Loaded links from {file_path}")
            return file.readlines()
    print(f"No links found in {file_path}")
    return []

def save_links(file_path, links):
    with open(file_path, 'w') as file:
        file.writelines(links)
    print(f"Saved links to {file_path}")

def fetch_sitemap_links(sitemap_url):
    print(f"Fetching sitemap links from {sitemap_url}")
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
    print(f"Sending Telegram message: {message}")
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message
    }
    response = requests.post(url, data=data)
    print(f"Telegram response: {response.json()}")
    return response

def log_error(file_path, url, error_message):
    with open(file_path, 'a') as f:
        f.write(f"{url}: {error_message}\n")
    print(f"Logged error for {url}: {error_message}")

def process_links(service, links_to_index, indexed_links, failed_links, domain, limit):
    indexed_count = 0
    for url in links_to_index:
        if indexed_count >= limit:
            break
        if url not in indexed_links and url not in failed_links:
            print(f"Checking if URL is indexed: {url}")
            is_indexed = check_indexed(service, url)
            time.sleep(1)  # Задержка между запросами для предотвращения превышения квоты
            if not is_indexed:
                print(f"Indexing URL: {url}")
                response = index_url(service, url)
                time.sleep(1)  # Задержка между запросами для предотвращения превышения квоты
                if response:
                    indexed_links.append(url + "\n")
                    indexed_count += 1
                else:
                    failed_links.append(url + "\n")
                    log_error('failed_links_errors.txt', url, 'Indexing failed')
            else:
                indexed_links.append(url + "\n")
    print(f"{domain} - отправлено {indexed_count} ссылок из {limit}.")
    return indexed_count

def main():
    print("Starting indexing process")
    try:
        vitrina_service = get_service(VITRINA24KZ_CREDENTIALС, 'vitrina24.kz')
        med_service = get_service(MEDVITRINA24KZ_CREDENTIALС, 'med.vitrina24.kz')
    except ValueError as e:
        print(f"Error: {e}")
        send_telegram_message(f"Indexing process failed: {e}")
        return

    indexed_links_vitrina = load_links('indexed_links_vitrina.txt')
    indexed_links_med = load_links('indexed_links_med.txt')
    failed_links_vitrina = load_links('failed_links_vitrina.txt')
    failed_links_med = load_links('failed_links_med.txt')
    links_to_index_vitrina = load_links('links_to_index_vitrina.txt')
    links_to_index_med = load_links('links_to_index_med.txt')

    if not links_to_index_vitrina:
        links_to_index_vitrina = fetch_sitemap_links('https://vitrina24.kz/sitemap.xml')
        save_links('links_to_index_vitrina.txt', links_to_index_vitrina)

    if not links_to_index_med:
        links_to_index_med = fetch_sitemap_links('https://med.vitrina24.kz/sitemap.xml')
        save_links('links_to_index_med.txt', links_to_index_med)

    print(f"Fetched {len(links_to_index_vitrina)} links from vitrina24.kz")
    print(f"Fetched {len(links_to_index_med)} links from med.vitrina24.kz")

    links_to_index_vitrina = [url.strip() for url in links_to_index_vitrina]
    links_to_index_med = [url.strip() for url in links_to_index_med]

    vitrina_indexed_count = process_links(
        vitrina_service,
        links_to_index_vitrina,
        indexed_links_vitrina,
        failed_links_vitrina,
        "vitrina24.kz",
        200
    )

    med_indexed_count = process_links(
        med_service,
        links_to_index_med,
        indexed_links_med,
        failed_links_med,
        "med.vitrina24.kz",
        200
    )

    save_links('indexed_links_vitrina.txt', indexed_links_vitrina)
    save_links('failed_links_vitrina.txt', failed_links_vitrina)
    save_links('indexed_links_med.txt', indexed_links_med)
    save_links('failed_links_med.txt', failed_links_med)

    print(f"Indexing process completed, {vitrina_indexed_count + med_indexed_count} links indexed")

    # Отправка сообщения в Telegram
    message = (
        f"vitrina24.kz - отправлено {vitrina_indexed_count} ссылок из 200.\n"
        f"med.vitrina24.kz - отправлено {med_indexed_count} ссылок из 200."
    )
    send_telegram_message(message)

    # Удаление обработанных ссылок из списка для индексирования
    remaining_links_vitrina = links_to_index_vitrina[vitrina_indexed_count:]
    remaining_links_med = links_to_index_med[med_indexed_count:]
    save_links('links_to_index_vitrina.txt', remaining_links_vitrina)
    save_links('links_to_index_med.txt', remaining_links_med)

if __name__ == "__main__":
    main()
