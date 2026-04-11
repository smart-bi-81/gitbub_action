import os
import json
import feedparser
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# Settings
CHANNEL_ID = "UCSxjNbPriyBh9RNl_QNSAtw"
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
LAST_VIDEO_FILE = "last_video.json"

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_video_id(entry):
    # Try multiple ways to get the video ID
    # Method 1: yt_videoid attribute
    if hasattr(entry, 'yt_videoid'):
        return entry.yt_videoid
    # Method 2: from the id field (yt:video:VIDEOID)
    if 'id' in entry:
        yt_id = entry.id
        if 'yt:video:' in yt_id:
            return yt_id.split('yt:video:')[-1]
    # Method 3: from the link URL
    link = entry.get('link', '')
    if 'watch?v=' in link:
        return link.split('watch?v=')[-1]
    if '/shorts/' in link:
        return link.split('/shorts/')[-1]
    return None

def get_latest_long_video():
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
    feed = feedparser.parse(url)
    
    print(f"Total entries found: {len(feed.entries)}")
    
    for entry in feed.entries:
        link = entry.get('link', '')
        title = entry.get('title', '')
        video_id = extract_video_id(entry)
        
        print(f"Checking: {title} | link: {link} | id: {video_id}")
        
        # Skip Shorts
        if '/shorts/' in link:
            print(f"  -> Skipping (Short)")
            continue
        
        if not video_id:
            print(f"  -> Skipping (no video ID found)")
            continue
            
        print(f"  -> Selected!")
        return {
            "id": video_id,
            "title": title,
            "url": link
        }
    return None

def get_last_seen_video():
    if os.path.exists(LAST_VIDEO_FILE):
        with open(LAST_VIDEO_FILE, "r") as f:
            return json.load(f)
    return None

def save_last_seen_video(video):
    with open(LAST_VIDEO_FILE, "w") as f:
        json.dump(video, f)

def get_transcript(video_id):
    try:
        url = f"https://api.supadata.ai/v1/youtube/transcript"
        headers = {"x-api-key": os.environ["SUPADATA_API_KEY"]}
        params = {"videoId": video_id, "text": "true"}
        response = requests.get(url, headers=headers, params=params)
        data = response.json()
        print(f"Supadata response: {response.status_code}")
        if response.status_code == 200:
            content = data.get("content", "")
            print(f"Transcript length: {len(content)} chars")
            return content
        else:
            print(f"Supadata error: {data}")
            return None
    except Exception as e:
        print(f"Transcript error: {e}")
        return None

def summarize(title, transcript):
    prompt = f"""You are a financial assistant. Summarize the following video in Hebrew, clearly and concisely.

Title: {title}

Transcript:
{transcript[:6000]}

Write a summary with:
- Topic of the video
- Main points (3-5 bullets)
- Conclusions / recommendations if any
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    response = requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    })
    print(f"Telegram response: {response.status_code}")

def main():
    latest = get_latest_long_video()
    if not latest:
        print("No long videos found")
        return

    print(f"Latest long video: {latest['title']}")

    last_seen = get_last_seen_video()

    if last_seen and last_seen["id"] == latest["id"]:
        print("No new video")
        return

    print(f"New video detected!")

    transcript = get_transcript(latest["id"])

    if transcript:
        summary = summarize(latest["title"], transcript)
        message = f"🎬 *סרטון חדש מ-מיכה סטוקס*\n\n*{latest['title']}*\n{latest['url']}\n\n{summary}"
    else:
        message = f"🎬 *סרטון חדש מ-מיכה סטוקס*\n\n*{latest['title']}*\n{latest['url']}\n\n⚠️ Could not fetch transcript"

    send_telegram(message)
    save_last_seen_video(latest)
    print("Message sent!")

if __name__ == "__main__":
    main()
