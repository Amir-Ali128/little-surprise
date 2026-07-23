from flask import Flask, render_template, request, jsonify
import anthropic
import os
import json
import random
import re
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


def build_theme(name, bg, text, gold, gold_light, muted, rose, lavender):
    rgb = tuple(int(gold.lstrip("#")[i:i + 2], 16) for i in (0, 2, 4))
    rgb_text = ",".join(map(str, rgb))

    return {
        "name": name,
        "bg": bg,
        "text": text,
        "gold": gold,
        "goldLight": gold_light,
        "muted": muted,
        "rose": rose,
        "lavender": lavender,
        "farsi": f"rgba({rgb_text},0.08)",
        "line": f"linear-gradient(to bottom, transparent, rgba({rgb_text},0.28), transparent)",
        "divider": f"linear-gradient(90deg, transparent, {gold}, transparent)",
        "angelGlow": (
            f"radial-gradient(circle, rgba({rgb_text},0.18) 0%, "
            f"rgba({rgb_text},0.08) 50%, transparent 70%)"
        ),
        "featherOp": "0.10",
        "starColors": [gold, rose, lavender, text, gold_light],
        "btnBorder": f"rgba({rgb_text},0.45)",
        "inputBorder": f"rgba({rgb_text},0.35)"
    }


PASTEL_THEMES = [
    build_theme("lavanta", "#f6f2ff", "#4c4666", "#b79ced", "#d8c8f5", "#8f87a6", "#d8bfd8", "#c7b8ea"),
    build_theme("pudra", "#fff5f7", "#5a4b4f", "#e8b4c8", "#f6d3df", "#a58b94", "#e9afc2", "#dcc8e8"),
    build_theme("mint", "#f2fff8", "#42544b", "#9ed8c1", "#cfefe2", "#7a9c8e", "#bfdccf", "#d7f2e5"),
    build_theme("bebek mavisi", "#f3faff", "#42566b", "#a7d3f3", "#d3ebfa", "#8098a8", "#c8dcec", "#c8dfff"),
    build_theme("şeftali", "#fff7f1", "#5b4b41", "#f4c49a", "#fbe2ca", "#a78e7c", "#f0c7af", "#e8d7c8"),
    build_theme("vanilya", "#fffdf4", "#5a533f", "#e9d79b", "#f8efcb", "#a69b76", "#eadbb7", "#e8dfc8"),
    build_theme("adaçayı", "#f5faf3", "#495545", "#b7d4a8", "#daecd1", "#86967d", "#d4dfc8", "#dcead4"),
    build_theme("lila", "#fbf6ff", "#514563", "#c5a8f2", "#e1d0fa", "#8f84a5", "#d9c2ec", "#cdb7f4"),
    build_theme("bulut", "#fafbfc", "#4d545c", "#c7ced8", "#e5e9ee", "#8a9096", "#dadde2", "#d7dee8"),
    build_theme("gül kurusu", "#fff7f8", "#5b464c", "#d9a5b3", "#f0cdd6", "#9a7f86", "#dfafba", "#e8cbd4")
]

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
    html = render_template("index.html")
    themes_json = json.dumps(PASTEL_THEMES, ensure_ascii=False)

    html = re.sub(
        r"const themes\s*=\s*\[.*?\];",
        f"const themes = {themes_json};",
        html,
        count=1,
        flags=re.DOTALL
    )
    html = html.replace("}, 20000);", "}, 30000);")
    return html


@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json() or {}
    password = data.get("password", "").strip().lower().replace(" ", "")
    expected_password = os.environ.get("SITE_PASSWORD", "09tannaz").strip().lower().replace(" ", "")
    return jsonify({"success": password == expected_password})


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
