from flask import Flask, render_template, request, jsonify
import anthropic
import os
import json
import random

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

# Mesaj veritabanını yükle
def load_messages():
    try:
        with open("messages.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except:
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


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json()
    password = data.get("password", "").strip().lower().replace(" ", "")
    
    # "09 Tannaz" boşluksuz küçük harf = "09tannaz"
    if password == "09tannaz":
        return jsonify({"success": True})
    return jsonify({"success": False})


@app.route("/get_message", methods=["GET"])
def get_message():
    try:
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
        lines = response_text.split('\n')

        tr_msg = ""
        fa_msg = ""
        anlam = ""

        for line in lines:
            if line.startswith("TR:"):
                tr_msg = line.replace("TR:", "").strip()
            elif line.startswith("FA:"):
                fa_msg = line.replace("FA:", "").strip()
            elif line.startswith("ANLAM:"):
                anlam = line.replace("ANLAM:", "").strip()

        return jsonify({
            "success": True,
            "tr": tr_msg,
            "fa": fa_msg,
            "anlam": anlam
        })

    except Exception as e:
        tr_msg = random.choice(MESSAGE_DB["turkish"])["text"] if MESSAGE_DB["turkish"] else ""
        fa_item = random.choice(MESSAGE_DB["farsi"]) if MESSAGE_DB["farsi"] else {}
        return jsonify({
            "success": True,
            "tr": tr_msg,
            "fa": fa_item.get("text", ""),
            "anlam": fa_item.get("meaning", "")
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
