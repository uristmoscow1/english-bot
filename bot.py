import os
import random
import json
import datetime
import requests
from flask import Flask, request
from gtts import gTTS
from io import BytesIO

TOKEN = os.getenv("TOKEN")
ADMIN_TG_ID = os.getenv("ADMIN_TG_ID", "").split(",")
app = Flask(__name__)

# ----------  DATA  ----------
WORDS = [
    {"en": "apple", "ru": "яблоко", "ex": "An apple a day keeps the doctor away."},
    {"en": "bridge", "ru": "мост", "ex": "We walked across the old bridge."},
    {"en": "journey", "ru": "путешествие", "ex": "Life is a long journey."},
    {"en": "freedom", "ru": "свобода", "ex": "Freedom is priceless."},
    {"en": "knowledge", "ru": "знания", "ex": "Knowledge is power."}
]

# ----------  STORAGE  ----------
STATS = {}  # chat_id -> {"words": 0, "streak": 0}

# ----------  HELPERS  ----------
def send(chat_id, text, **kwargs):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    payload.update(kwargs)
    requests.post(url, json=payload, timeout=5)

def send_voice(chat_id, word):
    tts = gTTS(word, lang='en')
    buf = BytesIO()
    tts.write_to_fp(buf)
    buf.seek(0)
    url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
    requests.post(url, data={"chat_id": chat_id}, files={"voice": buf.read()}, timeout=5)

# ----------  ROUTES  ----------
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data:
            return "ok", 200

        # callback_query
        if "callback_query" in data:
            q = data["callback_query"]
            chat = q["message"]["chat"]["id"]
            answer = q["data"]
            reply = "✅ Правильно!" if answer.startswith("right_") else "❌ Попробуй ещё раз!"
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                json={"callback_query_id": q["id"], "text": reply, "show_alert": True},
                timeout=5
            )
            return "ok", 200

        # обычное сообщение
        msg = data.get("message", {})
        text = msg.get("text", "").strip()
        chat = msg.get("chat", {}).get("id")
        if not text or not chat:
            return "ok", 200

        if text == "/start":
            send(chat, "🎯 Привет! /word /quiz /pron /stats /daily")
        elif text == "/word":
            w = random.choice(WORDS)
            send(chat, f"*{w['en']}* — _{w['ru']}_\n📌 {w['ex']}")
            send_voice(chat, w['en'])
        elif text.startswith("/pron"):
            word = text.split()[-1] if len(text.split()) > 1 else "hello"
            send_voice(chat, word)
            send(chat, f"🔊 {word}")
        elif text == "/quiz":
            w = random.choice(WORDS)
            others = [v for v in WORDS if v != w]
            opts = [w] + random.sample(others, 2)
            random.shuffle(opts)
            keyboard = json.dumps({
                "inline_keyboard": [
                    [{"text": v["ru"], "callback_data": f"{'right' if v == w else 'wrong'}_{w['en']}"}]
                    for v in opts
                ]
            })
            send(chat, f"Как перевести *{w['en']}*?", reply_markup=keyboard)
        elif text == "/stats":
            s = STATS.get(chat, {"words": 0, "streak": 0})
            send(chat, f"📊 Слов: *{s['words']}* | 🔥 Дней: *{s['streak']}*")
        elif text == "/daily":
            w = WORDS[datetime.datetime.utcnow().weekday() % len(WORDS)]
            send(chat, f"📅 Слово дня: *{w['en']}* — _{w['ru']}_")
        else:
            send(chat, f"Принято: {text}")

        return "ok", 200
    except Exception:
        return "ok", 200

@app.route("/")
def index():
    return "English Bot is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
