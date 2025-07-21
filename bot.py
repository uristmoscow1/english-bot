"""
English Bot Pro  (Redis + OpenAI + Streak + Leaderboard)
"""
import os
import json
import random
import datetime
import logging
import redis
import requests
from flask import Flask, request
from gtts import gTTS
from io import BytesIO
from openai import OpenAI

# ---------- CONFIG ----------
TOKEN       = os.getenv("TOKEN")
REDIS_URL   = os.getenv("REDIS_URL")  # обязательно
OPENAI_KEY  = os.getenv("OPENAI_KEY") # опционально
logging.basicConfig(level=logging.INFO)

r = redis.from_url(REDIS_URL, decode_responses=True)
client = OpenAI(api_key=OPENAI_KEY) if OPENAI_KEY else None
app = Flask(__name__)

# ---------- VOCABULARY ----------
WORDS = {
    "business": [
        {"en": "invoice",  "ru": "счёт",      "ex": "Please send the invoice before Friday."},
        {"en": "deadline", "ru": "крайний срок", "ex": "The deadline is tomorrow."}
    ],
    "travel": [
        {"en": "luggage",  "ru": "багаж",     "ex": "My luggage is overweight."},
        {"en": "itinerary","ru": "маршрут",   "ex": "Here is our itinerary for Paris."}
    ],
    "general": [
        {"en": "apple",    "ru": "яблоко",    "ex": "An apple a day keeps the doctor away."},
        {"en": "bridge",   "ru": "мост",      "ex": "We walked across the old bridge."}
    ]
}

# ---------- HELPERS ----------
def send(chat, text, **kw):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat, "text": text, "parse_mode": "Markdown", **kw}, timeout=5)

def send_voice(chat, word):
    tts = gTTS(word, lang='en')
    buf = BytesIO(); tts.write_to_fp(buf); buf.seek(0)
    url = f"https://api.telegram.org/bot{TOKEN}/sendVoice"
    requests.post(url, data={"chat_id": chat}, files={"voice": buf.read()}, timeout=5)

# ---------- REDIS UTILS ----------
def inc_words(chat): r.incr(f"words:{chat}")
def streak(chat):
    today = datetime.datetime.utcnow().date().isoformat()
    key = f"streak:{chat}"
    last = r.get(key)
    if last == today:
        return
    if last == str(datetime.datetime.utcnow().date() - datetime.timedelta(days=1)):
        r.incr(f"days:{chat}")
    else:
        r.set(f"days:{chat}", 1)
    r.set(key, today)

# ---------- AI LEVEL ----------
def detect_level(chat, text):
    if not client: return "N/A"
    prompt = f"Оцени уровень английского по фразе: {text}. Ответ: A0,A1,A2,B1,B2,C1."
    res = client.chat.completions.create(
        model="gpt-3.5-turbo", messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content.strip()

# ---------- ROUTES ----------
@app.route("/", methods=["POST"])
def webhook():
    try:
        data = request.get_json()
        if not data: return "ok", 200

        # callback_query
        if "callback_query" in data:
            q = data["callback_query"]
            chat = q["message"]["chat"]["id"]
            answer = q["data"]
            reply = "✅ Правильно!" if answer.startswith("right_") else "❌ Попробуй ещё раз!"
            requests.post(
                f"https://api.telegram.org/bot{TOKEN}/answerCallbackQuery",
                json={"callback_query_id": q["id"], "text": reply, "show_alert": True}, timeout=5
            )
            return "ok", 200

        msg = data.get("message", {})
        text = (msg.get("text") or "").strip()
        chat = msg.get("chat", {}).get("id")
        if not chat: return "ok", 200

        streak(chat)  # увеличиваем дни подряд

        if text == "/start":
            send(chat, "🎯 Привет! /word /quiz /pron /stats /daily /level /topic /night")
        elif text.startswith("/level"):
            example = text.split(maxsplit=1)[1] if len(text.split()) > 1 else "Hello"
            level = detect_level(chat, example)
            send(chat, f"Ваш уровень: *{level}*")
        elif text.startswith("/topic"):
            topic = text.split()[1] if len(text.split()) > 1 else "general"
            words = WORDS.get(topic, WORDS["general"])
            w = random.choice(words)
            send(chat, f"*{w['en']}* — _{w['ru']}_\n📌 {w['ex']}")
            send_voice(chat, w['en'])
            inc_words(chat)
        elif text == "/quiz":
            topic = random.choice(list(WORDS.keys()))
            w = random.choice(WORDS[topic])
            others = [v for v in WORDS[topic] if v != w]
            opts = [w] + random.sample(others, 2)
            random.shuffle(opts)
            kb = json.dumps({
                "inline_keyboard": [
                    [{"text": v["ru"], "callback_data": f"{'right' if v == w else 'wrong'}_{w['en']}"}]
                    for v in opts
                ]
            })
            send(chat, f"Как перевести *{w['en']}*?", reply_markup=kb)
        elif text.startswith("/pron"):
            word = text.split()[-1] if len(text.split()) > 1 else "hello"
            send_voice(chat, word)
            send(chat, f"🔊 {word}")
        elif text == "/stats":
            words = r.get(f"words:{chat}") or 0
            days  = r.get(f"days:{chat}") or 0
            top   = r.zrevrange("leaderboard", 0, 9, withscores=True)
            msg = f"📊 Слов: *{words}* | 🔥 Дней: *{days}*"
            if top:
                msg += "\n🏆 ТОП-10:"
                for i, (u, s) in enumerate(top):
                    msg += f"\n{i+1}. {u} — {int(s)}"
            send(chat, msg)
        elif text == "/daily":
            w = WORDS["general"][datetime.datetime.utcnow().weekday() % len(WORDS["general"])]
            send(chat, f"📅 Слово дня: *{w['en']}* — _{w['ru']}_")
            send_voice(chat, w['en'])
            inc_words(chat)
        elif text == "/night":
            r.setex(f"night:{chat}", 3600 * 12, 1)
            send(chat, "🌙 Уведомления отключены до 08:00.")
        else:
            send(chat, f"Принято: {text}")
        return "ok", 200
    except Exception as e:
        logging.exception(e)
        return "ok", 200

@app.route("/")
def index():
    return "English Bot Pro is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
