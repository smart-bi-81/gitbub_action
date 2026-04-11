import os
import json
import feedparser
import requests
from youtube_transcript_api import YouTubeTranscriptApi
from openai import OpenAI

# הגדרות
CHANNEL_ID = "UCxxxxxxxxxxxxxxxx"  # נמלא אחרי שנשלוף
TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
LAST_VIDEO_FILE = "last_video.json"

client = OpenAI(api_key=OPENAI_API_KEY)

def get_latest_video():
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL_ID}"
    feed = feedparser.parse(url)
    if feed.entries:
        latest = feed.entries[0]
        return {
            "id": latest.yt_videoid,
            "title": latest.title,
            "url": f"https://www.youtube.com/watch?v={latest.yt_videoid}"
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
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=["he", "iw"])
        return " ".join([t["text"] for t in transcript])
    except Exception as e:
        print(f"שגיאה בתמלול: {e}")
        return None

def summarize(title, transcript):
    prompt = f"""אתה עוזר פיננסי. סכם את הסרטון הבא בעברית בצורה ברורה וקצרה.

כותרת: {title}

תמליל:
{transcript[:6000]}

כתוב סיכום עם:
- נושא הסרטון
- הנקודות העיקריות (3-5 נקודות)
- מסקנות / המלצות אם יש
"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    return response.choices[0].message.content

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    })

def main():
    latest = get_latest_video()
    if not latest:
        print("לא נמצאו סרטונים")
        return

    last_seen = get_last_seen_video()
    
    if last_seen and last_seen["id"] == latest["id"]:
        print("אין סרטון חדש")
        return

    print(f"סרטון חדש: {latest['title']}")
    
    transcript = get_transcript(latest["id"])
    
    if transcript:
        summary = summarize(latest["title"], transcript)
        message = f"🎬 *סרטון חדש מ-מיכה סטוקס*\n\n*{latest['title']}*\n{latest['url']}\n\n{summary}"
    else:
        message = f"🎬 *סרטון חדש מ-מיכה סטוקס*\n\n*{latest['title']}*\n{latest['url']}\n\n⚠️ לא הצלחתי לשלוף תמלול"
    
    send_telegram(message)
    save_last_seen_video(latest)
    print("הודעה נשלחה!")

if __name__ == "__main__":
    main()
