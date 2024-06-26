import requests
import os
import time
from google.oauth2 import service_account
from googleapiclient.discovery import build
from xml.etree import ElementTree as ET
from googleapiclient.errors import HttpError

SCOPES = ['https://www.googleapis.com/auth/indexing']
VITRINA24KZ_CREDENTIALS = os.getenv('VITRINA24KZ_CREDENTIALS')
MEDVITRINA24KZ_CREDENTIALS = os.getenv('MEDVITRINA24KZ_CREDENTIALS')
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

def check_quota(service, domain):
    try:
        response = service.urlNotifications().getMetadata(url=f"https://{domain}").execute()
        return True
    except HttpError as e:
        if e.resp.status == 429:
            print(f"Quota exceeded for {domain}")
            return False
        else:
            print(f"Error checking quota for {domain}: {e}")
            return False

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
            print(f"Indexing URL: {url}")
            response = index_url(service, url)
            time.sleep(1)  # Задержка между запросами для предотвращения превышения квоты
            if response:
                indexed_links.append(url + "\n")
                indexed_count += 1
            else:
                failed_links.append(url + "\n")
                log_error('failed_links_errors.txt', url, 'Indexing failed')
    print(f"{domain} - отправлено {indexed_count} ссылок из {limit}.")
    return indexed_count

def process_domain(domain, credentials, links_to_index_file, indexed_links_file, failed_links_file, sitemap_url, limit):
    try:
        service = get_service(credentials, domain)
    except ValueError as e:
        print(f"Error: {e}")
        send_telegram_message(f"Indexing process for {domain} failed: {e}")
        return 0

    if not check_quota(service, domain):
        print(f"Quota exceeded for {domain}, skipping indexing.")
        send_telegram_message(f"Quota exceeded for {domain}, skipping indexing.")
        return 0

    indexed_links = load_links(indexed_links_file)
    failed_links = load_links(failed_links_file)
    links_to_index = load_links(links_to_index_file)

    if not links_to_index:
        links_to_index = fetch_sitemap_links(sitemap_url)
        save_links(links_to_index_file, links_to_index)

    print(f"Fetched {len(links_to_index)} links from {domain}")

    links_to_index = [url.strip() for url in links_to_index]

    indexed_count = process_links(
        service,
        links_to_index,
        indexed_links,
        failed_links,
        domain,
        limit
    )

    save_links(indexed_links_file, indexed_links)
    save_links(failed_links_file, failed_links)
    remaining_links = links_to_index[indexed_count:]
    save_links(links_to_index_file, remaining_links)

    return indexed_count

def main():
    print("Starting indexing process")

    vitrina_indexed_count = process_domain(
        "vitrina24.kz",
        VITRINA24KZ_CREDENTIALS,
        'links_to_index_vitrina.txt',
        'indexed_links_vitrina.txt',
        'failed_links_vitrina.txt',
        'https://vitrina24.kz/sitemap.xml',
        200
    )

    med_indexed_count = process_domain(
        "med.vitrina24.kz",
        MEDVITRINA24KZ_CREDENTIALS,
        'links_to_index_med.txt',
        'indexed_links_med.txt',
        'failed_links_med.txt',
        'https://med.vitrina24.kz/sitemap.xml',
        200
    )

    print(f"Indexing process completed, {vitrina_indexed_count + med_indexed_count} links indexed")

    # Отправка сообщения в Telegram
    message = (
        f"vitrina24.kz - отправлено {vitrina_indexed_count} ссылок из 200.\n"
        f"med.vitrina24.kz - отправлено {med_indexed_count} ссылок из 200."
    )
    send_telegram_message(message)

if __name__ == "__main__":
    main()
