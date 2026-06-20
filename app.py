from pathlib import Path
import json
import os
import random

import anthropic
from flask import Flask, jsonify, render_template, request


BASE_DIR = Path(__file__).resolve().parent
MESSAGE_PATH = BASE_DIR / "data" / "messages.json"

app = Flask(__name__)

ACCESS_PASSWORD = os.getenv("ACCESS_PASSWORD", "").strip()
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME", "claude-sonnet-4-6")

client = (
    anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    if ANTHROPIC_API_KEY
    else None
)


def load_messages():
    """Load fallback messages from data/messages.json."""
    try:
        with MESSAGE_PATH.open("r", encoding="utf-8") as file:
            data = json.load(file)

        return {
            "turkish": data.get("turkish", []),
            "farsi": data.get("farsi", []),
        }
    except (FileNotFoundError, json.JSONDecodeError):
        return {"turkish": [], "farsi": []}


MESSAGE_DB = load_messages()

SYSTEM_PROMPT = """Sen Türkçe ve Farsça bilen, şiirsel ama abartısız yazan bir yazarsın.
Senden kısa, anlamlı ve samimi mesajlar üretmeni istiyorum.

Kurallar:
- Türkçe başla, Farsça bitir
- Aşırı romantik olma, ama içten ol
- Türkçe kısım 1-2 cümle
- Farsça kısım 1 cümle + parantez içinde Türkçe anlamı
- Her seferinde farklı, özgün bir mesaj yaz
- Mesajlar doğal ve samimi olsun, şiirsel ama yapay değil
- Aşağıdaki mesaj tonunu ve stilini örnek al ama aynısını yazma:
  * "Bazı insanlar hayatına girer, fark etmeden her şeyi değiştirir."
  * "Sen bir şarkısın, aklımdan çıkmayan."
  * "فرشته‌ای که نمی‌دانست فرشته است"

Format olarak tam olarak şunu kullan, başka hiçbir şey yazma:
TR: [türkçe mesaj]
FA: [farsça mesaj]
ANLAM: [farsça mesajın türkçe anlamı]"""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"status": "ok"})


@app.route("/verify", methods=["POST"])
def verify():
    if not ACCESS_PASSWORD:
        return jsonify({
            "success": False,
            "error": "Access password is not configured."
        }), 500

    data = request.get_json(silent=True) or {}
    password = data.get("password", "").strip()

    return jsonify({"success": password == ACCESS_PASSWORD})


def fallback_message():
    """Return a local fallback message if the API is unavailable."""
    turkish_items = MESSAGE_DB.get("turkish", [])
    farsi_items = MESSAGE_DB.get("farsi", [])

    tr_msg = random.choice(turkish_items).get("text", "") if turkish_items else ""
    fa_item = random.choice(farsi_items) if farsi_items else {}

    return {
        "success": True,
        "tr": tr_msg,
        "fa": fa_item.get("text", ""),
        "anlam": fa_item.get("meaning", ""),
        "source": "fallback",
    }


@app.route("/get_message", methods=["GET"])
def get_message():
    if client is None:
        return jsonify(fallback_message())

    try:
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Yeni ve özgün bir mesaj yaz. Daha önce yazdıklarından farklı olsun.",
                }
            ],
        )

        response_text = message.content[0].text.strip()
        lines = response_text.splitlines()

        tr_msg = ""
        fa_msg = ""
        anlam = ""

        for line in lines:
            if line.startswith("TR:"):
                tr_msg = line.replace("TR:", "", 1).strip()
            elif line.startswith("FA:"):
                fa_msg = line.replace("FA:", "", 1).strip()
            elif line.startswith("ANLAM:"):
                anlam = line.replace("ANLAM:", "", 1).strip()

        if not tr_msg and not fa_msg:
            return jsonify(fallback_message())

        return jsonify({
            "success": True,
            "tr": tr_msg,
            "fa": fa_msg,
            "anlam": anlam,
            "source": "api",
        })

    except Exception:
        return jsonify(fallback_message())


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
