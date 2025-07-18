import os, random, requests
from flask import Flask, request

TOKEN = os.getenv("TOKEN")
app = Flask(__name__)

words = {"apple": "яблоко", "bridge": "мост", "journey": "путешествие"}

@app.route("/", methods=["POST"])
def webhook():
    data = request.get_json()
    text = (data["message"].get("text") or "").strip()
    chat = data["message"]["chat"]["id"]

    if text == "/start":
        answer = "Привет! Бот работает. /word – новое слово, /quiz – тест."
    elif text == "/word":
        w, tr = random.choice(list(words.items()))
        answer = f"*{w}* — {tr}"
    elif text.startswith("/pron"):
        word = text.split()[-1]
        answer = f"Произношение: /{word}/"
    elif text == "/quiz":
        w, tr = random.choice(list(words.items()))
        answer = f"Как перевести *{w}*?"
    else:
        answer = f"Принято: {text}"

    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    requests.post(url, json={"chat_id": chat, "text": answer, "parse_mode": "Markdown"})
    return "ok", 200

@app.route("/")
def index():
    return "English Bot is running", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 10000)))
