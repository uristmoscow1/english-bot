import os, random, json, datetime
import requests
from flask import Flask, request
from gtts import gTTS
from io import BytesIO

TOKEN = os.getenv("TOKEN")
ADMIN_TG_ID = os.getenv("ADMIN_TG_ID", "").split(",")
app = Flask(__name__)

# ------------------  DATA  ------------------
WORDS = [
    {"en": "apple", "ru": "яблоко", "ex": "An apple a day keeps the doctor away."},
    {"en": "bridge", "ru": "мост", "ex": "We walked across the old bridge."},
    {"en": "journey", "ru": "путешествие", "ex": "Life is a long journey."},
    {"en": "freedom", "ru": "свобода", "ex": "Freedom is priceless."},
    {"en": "knowledge", "ru": "знания", "ex": "Knowledge is power."}
]

# ------------------  STORAGE  ------------------
STATS = {}  # chat_id -> {"words": 0, "streak": 0}

# ------------------  HELPERS  ------------------
def send(chat_id, text, **kwargs):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    payload.update(kwargs)
    requests.post(url, json=payload)

def send_voice(chat_id, word):
    tts = gTTS(word, lang='en')
    buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0)
    url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
    requests.post(url, data={"chat_id": chat_id}, files={"voice": buf.read()})

# ------------------  ROUTES  ------------------
@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    msg = data.get("message", {})
    text = msg.get("text", "").strip()
    chat = msg.get("chat", {}).get("id")

    if not text: return "ok", 200

    # --- логика команд ---
    if text == "/start":
        send(chat, "🎯 Привет! Я помогу учить английский по 90 секунд в день.\n"
                   "• /word — новое слово с примером\n"
                   "• /quiz — 5-вопросный тест\n"
                   "• /pron word — произношение\n"
                   "• /stats — твоя статистика\n"
                   "• /daily — слово дня")

    elif text == "/word":
        w = random.choice(WORDS)
        send(chat, f"*{w['en']}* — _{w['ru']}_\n📌 {w['ex']}")
        send_voice(chat, w['en'])

    elif text.startswith("/pron"):
        word = text.split()[1] if len(text.split()) > 1 else "hello"
        send_voice(chat, word)
        send(chat, f"Произношение: *{word}*")

    elif text == "/quiz":
        w = random.choice(WORDS)
        keyboard = json.dumps({
            "inline_keyboard": [
                [{"text": w["ru"], "callback_data": f"right_{w['en']}"}] +
                [{"text": v["ru"], "callback_data": f"wrong_{w['en']}"}
                 for v in random.sample([v for v in WORDS if v != w], 2)]
            ]
        })
        send(chat, f"Как перевести *{w['en']}*?", reply_markup=keyboard)

    elif text == "/stats":
        s = STATS.get(chat, {"words": 0, "streak": 0})
        send(chat, f"📊 Слов выучено: *{s['words']}*\n🔥 Дней подряд: *{s['streak']}*")

    elif text == "/daily":
        today = datetime.datetime.utcnow().weekday()
        w = WORDS[today % len(WORDS)]
        send(chat, f"📅 Слово дня: *{w['en']}* — _{w['ru']}_\n📌 {w['ex']}")

    # --- обработка callback ---
    elif "callback_query" in data:
        q = data["callback_query"]
        chat = q["message"]["chat"]["id"]
        data_cd = q["data"]
        if data_cd.startswith("right_"):
            STATS[chat] = STATS.get(chat, {"words": 0, "streak": 0})
            STATS[chat]["words"] += 1
            send(chat, "✅ Правильно!")
        elif data_cd.startswith("wrong_"):
            send(chat, "❌ Попробуй ещё раз!")

    return "ok", 200

@app.route("/")
def index():
    return "English Bot is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
