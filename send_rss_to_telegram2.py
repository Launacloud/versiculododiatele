import os
import requests
import feedparser
import json
import time
from bs4 import BeautifulSoup

# Load environment variables
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
RSS_FEED_URL = os.getenv('RSS_FEED_URL')
CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')

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

# Function to send RSS feed items to Telegram
def send_rss_to_telegram():
    feed = feedparser.parse(RSS_FEED_URL)
    for entry in feed.entries:
        print(f"Feed item: {entry.title}")
    last_message_timestamp = 0  # Initialize with a default value
    # Check if there are any entries in the feed
    if feed.entries:
        # Convert the timestamp of the most recent entry to seconds since epoch
        last_message_timestamp = time.mktime(feed.entries[0].published_parsed)
    for entry in feed.entries:
        title = entry.title
        link = entry.get('link', entry.get('url'))  # Get link or url
        description = entry.get('content_html', entry.get('description'))  # Get content_html or description
        publish_date = time.mktime(entry.published_parsed)  # Convert published date to timestamp
        # Compare the publish date with the timestamp of the last message
        if publish_date > last_message_timestamp:
            # Use BeautifulSoup to extract text from HTML description and filter out unsupported tags
            soup = BeautifulSoup(description, 'html.parser')
            supported_tags = ['b', 'i', 'a']  # Supported tags: bold, italic, anchor
            # Filter out unsupported tags
            for tag in soup.find_all():
                if tag.name not in supported_tags:
                    tag.decompose()
            description_text = soup.get_text()
            message = f"<b>{title}</b>\n{link}\n\n{description_text}"
            send_telegram_message(message)
            print(f"Message sent: {title}")
        else:
            print(f"Message skipped (published date older than last message): {title}")

# Main function
def main():
    send_rss_to_telegram()

if __name__ == "__main__":
    main()
