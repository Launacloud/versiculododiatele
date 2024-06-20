import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
RSS_FEED_URL = os.getenv('RSS_FEED_URL')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Cache file path
CACHE_FILE_PATH = 'feed_cache.json'

# Function to load cache from the file
def load_cache():
    if os.path.exists(CACHE_FILE_PATH):
        with open(CACHE_FILE_PATH, 'r') as file:
            cache = json.load(file)
            print(f"Cache loaded from file: {CACHE_FILE_PATH}")
            return cache
    else:
        print("No cache file found. Starting with an empty cache.")
        return {}

# Function to save cache to the file
def save_cache(cache):
    with open(CACHE_FILE_PATH, 'w') as file:
        json.dump(cache, file, indent=4)
    print(f"Cache saved to file: {CACHE_FILE_PATH}")

# Function to send a message to a Telegram chat
def send_telegram_message(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'false'  # Enable link previews
    }
    response = requests.post(url, data=payload)
    print(f"Response status code: {response.status_code}")
    print(f"Response text: {response.text}")
    if response.status_code != 200:
        raise Exception(f"Error sending message: {response.text}")

# Function to fetch RSS feed with conditional requests
def fetch_rss_feed(etag=None, modified=None):
    headers = {}
    if etag:
        headers['If-None-Match'] = etag
    if modified:
        headers['If-Modified-Since'] = modified
    
    response = requests.get(RSS_FEED_URL, headers=headers)
    response.raise_for_status()
    
    feed = feedparser.parse(response.content)
    feed.status = response.status_code
    
    # Extract etag and last-modified from the response headers
    feed.etag = response.headers.get('ETag')
    feed.modified = response.headers.get('Last-Modified')
    
    return feed

# Function to send RSS feed items to Telegram
def send_rss_to_telegram():
    cache = load_cache()
    etag = cache.get('etag')
    modified = cache.get('modified')
    last_entry_id = cache.get('last_entry_id', None)  # Initialize last_entry_id if not present
    
    print("Previous etag:", etag)
    print("Previous modified:", modified)

    print(f"Loading feed with etag: {etag} and modified: {modified}")
    feed = fetch_rss_feed(etag=etag, modified=modified)

    if feed.status == 304:
        print("No new entries.")
        return

    print(f"New etag: {feed.etag}")
    print(f"New modified: {feed.modified}")

    # Update cache with new etag and modified values if they exist in the feed
    if feed.etag:
        cache['etag'] = feed.etag
    if feed.modified:
        cache['modified'] = feed.modified

    new_entries = []
    for entry in reversed(feed.entries):  # Process entries in reverse order
        entry_id = entry.get('id', entry.get('link')).strip()
        print(f"Processing entry with id: {entry_id}")
        if last_entry_id and entry_id == last_entry_id:
            print(f"Found the last processed entry with id: {entry_id}. Stopping further collection.")
            break
        new_entries.append(entry)

    if not new_entries:
        print("No new entries to process.")
        return

    for entry in reversed(new_entries):  # Send new entries in correct order
        entry_id = entry.get('id', entry.get('link')).strip()
        title = entry.title
        link = entry.get('link', entry.get('url'))
        description = entry.get('content_html', entry.get('description'))

        if description:
            soup = BeautifulSoup(description, 'html.parser')
            supported_tags = ['b', 'i', 'a']
            for tag in soup.find_all():
                if tag.name not in supported_tags:
                    tag.decompose()
            description_text = soup.prettify()
        else:
            description_text = "No description available."

        message = f"<b>{title}</b>\n<a href='{link}'>{link}</a>\n\n{description_text}"
        send_telegram_message(message)

        cache['last_entry_id'] = entry_id

    save_cache(cache)

# Main function
def main():
    send_rss_to_telegram()

if __name__ == "__main__":
    main()
