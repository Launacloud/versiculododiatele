import os
import json
import requests
import feedparser
from bs4 import BeautifulSoup

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
RSS_FEED_URL = os.getenv('RSS_FEED_URL')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

# Check if environment variables are set
if not TELEGRAM_BOT_TOKEN or not RSS_FEED_URL or not CHAT_ID:
    raise ValueError("Please set TELEGRAM_BOT_TOKEN, RSS_FEED_URL, and TELEGRAM_CHAT_ID environment variables.")

# Cache file path
CACHE_FILE_PATH = 'feed_cache.json'

# Flag to bypass etag/modified caching (Set to False for production)
BYPASS_CACHE_CHECK = False  # Change to True to disable caching

# Function to load cache from file
def load_cache():
    if os.path.exists(CACHE_FILE_PATH):
        try:
            with open(CACHE_FILE_PATH, 'r') as file:
                cache = json.load(file)
                print(f"✅ Cache loaded: {cache}")
                return cache
        except json.JSONDecodeError:
            print("⚠️ Invalid JSON in cache file. Resetting cache.")
    return {"etag": "", "modified": "", "last_entry_id": ""}

# Function to save cache to file
def save_cache(cache):
    with open(CACHE_FILE_PATH, 'w') as file:
        json.dump(cache, file, indent=4)
    print(f"✅ Cache saved: {cache}")

# Function to send a message to Telegram
def send_telegram_message(message):
    MAX_MESSAGE_LENGTH = 4096  # Telegram max message length

    if len(message) > MAX_MESSAGE_LENGTH:
        print("⚠️ Message too long, splitting...")
        for i in range(0, len(message), MAX_MESSAGE_LENGTH):
            send_telegram_message(message[i:i+MAX_MESSAGE_LENGTH])
        return

    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        'chat_id': CHAT_ID,
        'text': message,
        'parse_mode': 'HTML',
        'disable_web_page_preview': 'false'
    }
    
    response = requests.post(url, data=payload)
    if response.status_code != 200:
        print(f"❌ Telegram Error: {response.text}")
        raise Exception(f"Error sending message: {response.text}")

# Function to check and process the RSS feed
def check_feed():
    cache = load_cache()
    headers = {}

    # Only use etag and last-modified headers if bypass is OFF
    if not BYPASS_CACHE_CHECK:
        if cache.get("etag"):
            headers['If-None-Match'] = cache["etag"]
        if cache.get("modified"):
            headers['If-Modified-Since'] = cache["modified"]

    print(f"📡 Fetching feed: {RSS_FEED_URL}")
    print(f"📤 Sent Headers: {headers}")

    response = requests.get(RSS_FEED_URL, headers=headers, allow_redirects=True)

    # If feed is not modified, stop processing
    if response.status_code == 304:
        print("✅ Feed not modified, stopping.")
        return

    # Debugging: Print headers received
    print(f"📥 Response Headers: {response.headers}")

    feed = feedparser.parse(response.content)

    # Save new etag and last-modified values
    cache["etag"] = response.headers.get("etag", "")
    cache["modified"] = response.headers.get("last-modified", "")

    new_entries = []
    for entry in feed.entries:
        entry_id = entry.get('id', entry.get('link')).strip()
        print(f"🔍 Checking entry ID: {entry_id}")

        # Stop processing if we reach an already processed entry
        if entry_id == cache["last_entry_id"]:
            print(f"⏹️ Entry ID {entry_id} matches last processed entry. Stopping script.")
            break

        new_entries.append(entry)

    if not new_entries:
        print("ℹ️ No new entries found.")
        return

    for entry in reversed(new_entries):  # Process in chronological order
        entry_id = entry.get('id', entry.get('link')).strip()

        title = entry.title
        link = entry.get('link', entry.get('url'))
        description = entry.get('content_html', entry.get('description'))

        # Clean description
        if description:
            soup = BeautifulSoup(description, 'html.parser')
            allowed_tags = ['b', 'i', 'a']
            for tag in soup.find_all():
                if tag.name not in allowed_tags:
                    tag.decompose()
            description_text = soup.prettify()
        else:
            description_text = "No description available."

        message = f"<b>{title}</b>\n<a href='{link}'>{link}</a>\n\n{description_text}"

        try:
            print(f"📨 Sending: {message[:100]}...")  # Show only first 100 chars
            send_telegram_message(message)
            cache[entry_id] = True
        except Exception as e:
            print(f"❌ Error sending message: {e}")

    # Update last processed entry ID
    if new_entries:
        cache["last_entry_id"] = new_entries[-1].get('id', new_entries[-1].get('link')).strip()
        save_cache(cache)

# Main function
def main():
    try:
        check_feed()
    except Exception as e:
        print(f"🚨 Unexpected error: {e}")

if __name__ == "__main__":
    main()
0
