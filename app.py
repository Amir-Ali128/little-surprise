from flask import Flask, render_template, request, jsonify
import anthropic
import os
import json
import random

app = Flask(__name__)

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))

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
    if password == "09tannaz":
        return jsonify({"success": True})
    return jsonify({"success": False})


@app.route("/get_message", methods=["GET"])
def get_message():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    print(f"API KEY VAR MI: {bool(api_key)}")
    
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
        print(f"API CEVABI: {response_text}")
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

        print(f"PARSED: TR={tr_msg}, FA={fa_msg}")
        return jsonify({
            "success": True,
            "tr": tr_msg,
            "fa": fa_msg,
            "anlam": anlam,
            "source": "api"
        })

    except Exception as e:
        print(f"API HATASI: {str(e)}")
        tr_msg = random.choice(MESSAGE_DB["turkish"])["text"] if MESSAGE_DB["turkish"] else ""
        fa_item = random.choice(MESSAGE_DB["farsi"]) if MESSAGE_DB["farsi"] else {}
        return jsonify({
            "success": True,
            "tr": tr_msg,
            "fa": fa_item.get("text", ""),
            "anlam": fa_item.get("meaning", ""),
            "source": "fallback"
        })


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
