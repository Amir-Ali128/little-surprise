from flask import Flask, render_template, request, jsonify
import anthropic
import os
import json
import random
from pathlib import Path

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

BASE_DIR = Path(__file__).resolve().parent
MESSAGES_FILE = BASE_DIR / "data" / "messages.json"


def load_messages():
    try:
        with MESSAGES_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)
        print(
            f"MESAJLAR YÜKLENDİ: "
            f"{len(data.get('turkish', []))} Türkçe, "
            f"{len(data.get('farsi', []))} Farsça"
        )
        return data
    except Exception as e:
        print(f"MESAJ DOSYASI HATASI: {e}")
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

Format olarak tam olarak şunu kullan, başka hiçbir şey yazma:
TR: [türkçe mesaj]
FA: [farsça mesaj]
ANLAM: [farsça mesajın türkçe anlamı]"""


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json() or {}
    password = data.get("password", "").strip().lower().replace(" ", "")
    expected_password = os.environ.get("SITE_PASSWORD", "").strip().lower().replace(" ", "")
    return jsonify({"success": bool(expected_password) and password == expected_password})


def get_fallback_message():
    turkish_messages = MESSAGE_DB.get("turkish", [])
    farsi_messages = MESSAGE_DB.get("farsi", [])

    if not turkish_messages or not farsi_messages:
        return jsonify({
            "success": False,
            "error": "Mesaj veritabanı yüklenemedi."
        }), 500

    tr_item = random.choice(turkish_messages)
    fa_item = random.choice(farsi_messages)

    return jsonify({
        "success": True,
        "tr": tr_item.get("text", ""),
        "fa": fa_item.get("text", ""),
        "anlam": fa_item.get("meaning", ""),
        "source": "fallback"
    })


@app.route("/get_message", methods=["GET"])
def get_message():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    print(f"API KEY VAR MI: {bool(api_key)}")

    try:
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY bulunamadı")

        message = client.messages.create(
            model="claude-sonnet-4-6",
            max_tokens=300,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Yeni ve özgün bir mesaj yaz. Daha önce yazdıklarından farklı olsun."
                }
            ]
        )

        response_text = message.content[0].text.strip()
        print(f"API CEVABI: {response_text}")

        tr_msg = ""
        fa_msg = ""
        anlam = ""

        for line in response_text.splitlines():
            line = line.strip()
            if line.startswith("TR:"):
                tr_msg = line.removeprefix("TR:").strip()
            elif line.startswith("FA:"):
                fa_msg = line.removeprefix("FA:").strip()
            elif line.startswith("ANLAM:"):
                anlam = line.removeprefix("ANLAM:").strip()

        if not tr_msg or not fa_msg or not anlam:
            raise ValueError("API cevabı beklenen formatta değil")

        print(f"PARSED: TR={tr_msg}, FA={fa_msg}")
        return jsonify({
            "success": True,
            "tr": tr_msg,
            "fa": fa_msg,
            "anlam": anlam,
            "source": "api"
        })

    except Exception as e:
        print(f"API HATASI / FALLBACK: {e}")
        return get_fallback_message()


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
