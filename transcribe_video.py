import os
import re
import requests
from openai import OpenAI

TELEGRAM_BOT_TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
CHAT_ID = os.environ["CHAT_ID"]
OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_API_KEY = os.environ["SUPABASE_API_KEY"]
SUPADATA_API_KEY = os.environ["SUPADATA_API_KEY"]
VIDEO_ID = os.environ["VIDEO_ID"]

client = OpenAI(api_key=OPENAI_API_KEY)

def extract_video_id(text):
    match = re.search(r'video_id:\s*([a-zA-Z0-9_-]+)', text)
    if match:
        return match.group(1)
    return None

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

def get_prompt_type(video_id):
    headers = {
        "apikey": SUPABASE_API_KEY,
        "Authorization": f"Bearer {SUPABASE_API_KEY}",
        "Content-Type": "application/json"
    }
    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/youtube_videos?video_id=eq.{video_id}&select=prompt_type,video_title",
        headers=headers
    )
    data = response.json()
    if data:
        return data[0].get("prompt_type", "technology"), data[0].get("video_title", "")
    return "technology", ""

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
        "chat_id": CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    })

def main():
    print(f"Message received: {MESSAGE_TEXT}")

    video_id = VIDEO_ID

    print(f"Video ID: {video_id}")
    send_telegram(f"⏳ Fetching transcript for `{video_id}`...")

    transcript = get_transcript(video_id)
    if not transcript:
        send_telegram("❌ Could not fetch transcript.")
        return

    prompt_type, title = get_prompt_type(video_id)
    print(f"Prompt type: {prompt_type}, Title: {title}")

    summary = summarize(title, transcript, prompt_type)
    update_supabase(video_id, transcript, summary)

    message = f"🎬 *{title}*\n\n📝 *Summary:*\n{summary}"
    send_telegram(message)
    print("Done!")

if __name__ == "__main__":
    main()
