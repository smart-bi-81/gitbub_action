import os
import json
import feedparser
import requests
from openai import OpenAI

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
TELEGRAM_CHAT_ID = os.environ["TELEGRAM_CHAT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_API_KEY = os.environ["SUPABASE_API_KEY"]
SUPADATA_API_KEY = os.environ["SUPADATA_API_KEY"]
LAST_SEEN_FILE = "last_seen_v2.json"

client = OpenAI(api_key=OPENAI_API_KEY)

CHANNELS = {
    "UCSxjNbPriyBh9RNl_QNSAtw": "Micha Stocks",
    "UCFp1vaKzpfvoGai0vE5VJ0w": "Guy in a Cube",
    "UC-n1UNdkbph0zdxA3r9Xupg": "Code Cave",
    "UCwywdccdYsNS_Cs6tS0U_dg": "TrashTech",
    "UC2ojq-nuP8ceeHqiroeKhBA": "Nate Herk",
    "UCVK7hhmVl2fzgeIrYPi1qSA": "EladAmraniAI",
    "UCcc21gBGNJwZM_eDEByeN-Q": "SQLBI",
    "UC4xudd2ZKjw-OdzR72UY74w": "YUV AI",
    "UCawZsQWqfGSbCI5yjkdVkTA": "Matthew Berman",
    "UCHF2DBAUHYG5jImGlcioybQ": "AWS Israel",
    "UCJ7UhloHSA4wAqPzyi6TOkw": "Curbal",
    "UCtevzRsHEKhs-RK8pAqwSyQ": "Leon van Zyl",
    "UCJtUOos_MwJa_Ewii-R3cJA": "Leila Gharani",
    "UChpleBmo18P08aKCIgti38g": "Matt Wolfe",
    "UCQ8KVze5WeCpQrF-U_ntBVw": "Mike Pekka",
    "UCBr1IoxBAF9RDPdTzb6459g": "Volo Builds",
    "UCQJGtq3tlrK_c2JCAxGuVzg": "Odet Maimoni",
    "UCLgwwlJ6xgxN9qt75Kgw4Ng": "Umbral",
    "UCAEOtPgh29aXEt31O17Wfjg": "CodeWithYu",
    "UCZjRcM1ukeciMZ7_fvzsezQ": "Coding Is Fun",
    "UC-h-wArcxJC8zBOD-UxfCOg": "BI Elite",
    "UCirQ4lFS5IgJZPQiyhE5Myw": "hayaData",
}

def load_last_seen():
    if os.path.exists(LAST_SEEN_FILE):
        with open(LAST_SEEN_FILE, "r") as f:
            return json.load(f)
    return {}

def save_last_seen(data):
    with open(LAST_SEEN_FILE, "w") as f:
        json.dump(data, f)

def get_latest_long_video(channel_id):
    url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
    feed = feedparser.parse(url)
    for entry in feed.entries:
        link = entry.get("link", "")
        if "/shorts/" in link:
            continue
        video_id = None
        if "id" in entry and "yt:video:" in entry.id:
            video_id = entry.id.split("yt:video:")[-1]
        elif "watch?v=" in link:
            video_id = link.split("watch?v=")[-1]
        if video_id:
            return {
                "id": video_id,
                "title": entry.get("title", ""),
                "url": link,
                "description": entry.get("summary", "")[:500]
            }
    return None

def classify_video(title, description):
    prompt = f"""Classify this YouTube video into exactly one category:
- "market": if about stocks, finance, trading, investment, stock market
- "technology": if about tech, tools, software, AI, programming, data, BI

Reply with a single word only: market OR technology

Title: {title}
Description: {description}"""
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": prompt}]
    )
    result = response.choices[0].message.content.strip().lower()
    return result if result in ["market", "technology"] else "technology"

def save_to_supabase(video, channel_name, prompt_type):
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json",
        "Prefer": "resolution=ignore-duplicates"
    }
    data = {
        "video_id": video["id"],
        "channel_name": channel_name,
        "video_title": video["title"],
        "video_url": video["url"],
        "prompt_type": prompt_type,
        "published_date": "now()"
    }
    response = requests.post(
        f"{SUPABASE_URL}/rest/v1/youtube_videos",
        headers=headers,
        json=data
    )
    print(f"Supabase insert: {response.status_code}")

def get_transcript(video_id):
    try:
        response = requests.get(
            "https://api.supadata.ai/v1/youtube/transcript",
            headers={"x-api-key": SUPADATA_API_KEY},
            params={"videoId": video_id, "text": "true"}
        )
        data = response.json()
        if response.status_code == 200:
            return data.get("content", "")
        print(f"Supadata error: {data}")
        return None
    except Exception as e:
        print(f"Transcript error: {e}")
        return None

def load_prompt(prompt_type):
    filename = f"prompt_{prompt_type}.txt"
    with open(filename, "r") as f:
        return f.read()

def summarize(title, transcript, prompt_type):
    system_prompt = load_prompt(prompt_type)
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Title: {title}\n\nTranscript:\n{transcript[:6000]}"}
        ]
    )
    return response.choices[0].message.content

def update_supabase(video_id, transcript, summary):
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }
    requests.patch(
        f"{SUPABASE_URL}/rest/v1/youtube_videos?video_id=eq.{video_id}",
        headers=headers,
        json={
            "transcript_text": transcript,
            "summary_text": summary,
            "transcribed_at": "now()"
        }
    )

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    requests.post(url, json={
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    })

def main():
    last_seen = load_last_seen()
    new_last_seen = dict(last_seen)

    for channel_id, channel_name in CHANNELS.items():
        print(f"Checking {channel_name}...")
        video = get_latest_long_video(channel_id)
        if not video:
            print(f"  No video found")
            continue

        last_id = last_seen.get(channel_id)
        if last_id == video["id"]:
            print(f"  No new video")
            continue

        print(f"  New video: {video['title']}")
        prompt_type = classify_video(video["title"], video["description"])
        print(f"  Classified as: {prompt_type}")

        save_to_supabase(video, channel_name, prompt_type)

        if channel_id == "UCSxjNbPriyBh9RNl_QNSAtw":
            print(f"  Auto-transcribing Micha Stocks video...")
            transcript = get_transcript(video["id"])
            if transcript:
                summary = summarize(video["title"], transcript, prompt_type)
                update_supabase(video["id"], transcript, summary)
                message = (
                    f"📺 *Micha Stocks* — סיכום אוטומטי\n\n"
                    f"*{video['title']}*\n"
                    f"{video['url']}\n\n"
                    f"📝 *סיכום:*\n{summary}"
                )
            else:
                message = (
                    f"📺 *Micha Stocks*\n\n"
                    f"*{video['title']}*\n"
                    f"{video['url']}\n\n"
                    f"⚠️ Could not fetch transcript"
                )
        else:
            message = (
                f"📺 *{channel_name}*\n\n"
                f"*{video['title']}*\n"
                f"{video['url']}\n\n"
                f"🏷 Category: `{prompt_type}`\n"
                f"🆔 video\\_id: `{video['id']}`\n\n"
                f"Reply with video ID to get a summary"
            )

        send_telegram(message)
        new_last_seen[channel_id] = video["id"]

    save_last_seen(new_last_seen)
    print("Done!")

if __name__ == "__main__":
    main()
