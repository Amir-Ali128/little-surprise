from flask import Flask, render_template, request, jsonify, session
import anthropic
import hashlib
import hmac
import json
import os
import random
import secrets
import time
from pathlib import Path

app = Flask(__name__)

secret_seed = (
    os.environ.get("SECRET_KEY")
    or os.environ.get("SITE_PASSWORD")
    or os.environ.get("ACCESS_PASSWORD")
    or secrets.token_hex(32)
)
app.secret_key = hashlib.sha256(secret_seed.encode("utf-8")).digest()
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("COOKIE_SECURE", "true").lower() == "true",
)

BASE_DIR = Path(__file__).resolve().parent
MESSAGES_FILE = BASE_DIR / "data" / "messages.json"
MODEL_NAME = os.environ.get("MODEL_NAME", "claude-sonnet-4-6")
VERIFY_WINDOW_SECONDS = 60
VERIFY_MAX_ATTEMPTS = 6
MESSAGE_COOLDOWN_SECONDS = 12

client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))


def load_messages():
    try:
        with MESSAGES_FILE.open("r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return {"turkish": [], "farsi": []}


MESSAGE_DB = load_messages()

SYSTEM_PROMPT = """Sen Türkçe ve Farsça bilen, zarif ve doğal yazan bir yazarsın.
Bu mesaj Tannaz için hazırlanmış küçük, kişisel bir dijital hediyenin parçasıdır.

Ton:
- sıcak, sakin, samimi
- şiirsel ama abartısız
- duygusal baskı yaratmayan
- büyük aşk ilanları veya sahiplenici ifadeler kullanmayan
- kısa ve doğal

Kurallar:
- Türkçe bölüm 1-2 kısa cümle olsun.
- Farsça bölüm tek cümle olsun.
- Farsça mesajın Türkçe anlamını ayrıca ver.
- Her üretimde farklı bir düşünce seç.
- "sonsuz", "kader", "sensiz yaşayamam", "benimsin" gibi ağır ifadeler kullanma.
- Emoji kullanma.

Yalnızca şu formatta cevap ver:
TR: [Türkçe mesaj]
FA: [Farsça mesaj]
ANLAM: [Farsça mesajın Türkçe anlamı]
"""


@app.after_request
def add_security_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/health")
def health():
    return jsonify({"ok": True})


def site_password():
    return (
        os.environ.get("SITE_PASSWORD")
        or os.environ.get("ACCESS_PASSWORD")
        or ""
    ).strip()


def verify_rate_limited():
    now = time.time()
    started_at = session.get("verify_window_started_at", now)
    attempts = session.get("verify_attempts", 0)

    if now - started_at > VERIFY_WINDOW_SECONDS:
        session["verify_window_started_at"] = now
        session["verify_attempts"] = 0
        return False

    return attempts >= VERIFY_MAX_ATTEMPTS


def register_verify_attempt():
    now = time.time()
    started_at = session.get("verify_window_started_at")

    if not started_at or now - started_at > VERIFY_WINDOW_SECONDS:
        session["verify_window_started_at"] = now
        session["verify_attempts"] = 1
    else:
        session["verify_attempts"] = session.get("verify_attempts", 0) + 1


@app.route("/verify", methods=["POST"])
def verify():
    expected = site_password()
    if not expected:
        return jsonify({
            "success": False,
            "error": "Site şifresi sunucuda ayarlanmamış."
        }), 503

    if verify_rate_limited():
        return jsonify({
            "success": False,
            "error": "Çok fazla deneme. Bir dakika sonra tekrar deneyebilirsin."
        }), 429

    data = request.get_json(silent=True) or {}
    supplied = str(data.get("password", "")).strip()
    register_verify_attempt()

    if hmac.compare_digest(supplied, expected):
        session.clear()
        session["verified"] = True
        session["verified_at"] = int(time.time())
        return jsonify({"success": True})

    return jsonify({"success": False, "error": "Şifre doğru değil."}), 401


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"success": True})


def fallback_payload():
    turkish_messages = MESSAGE_DB.get("turkish", [])
    farsi_messages = MESSAGE_DB.get("farsi", [])

    if not turkish_messages or not farsi_messages:
        return None

    tr_item = random.choice(turkish_messages)
    fa_item = random.choice(farsi_messages)

    return {
        "success": True,
        "tr": tr_item.get("text", ""),
        "fa": fa_item.get("text", ""),
        "anlam": fa_item.get("meaning", ""),
        "source": "fallback",
    }


def parse_ai_message(text):
    fields = {"TR": "", "FA": "", "ANLAM": ""}
    for raw_line in text.splitlines():
        line = raw_line.strip()
        for key in fields:
            prefix = key + ":"
            if line.startswith(prefix):
                fields[key] = line[len(prefix):].strip()

    if not all(fields.values()):
        raise ValueError("AI cevabı beklenen formatta değil.")

    return fields


@app.route("/get_message", methods=["GET"])
def get_message():
    if not session.get("verified"):
        return jsonify({"success": False, "error": "Yetkisiz erişim."}), 401

    now = time.time()
    last_message_at = session.get("last_message_at", 0)
    retry_after = MESSAGE_COOLDOWN_SECONDS - (now - last_message_at)

    if retry_after > 0:
        return jsonify({
            "success": False,
            "error": "Yeni not için biraz bekle.",
            "retry_after": max(1, int(retry_after)),
        }), 429

    session["last_message_at"] = now

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        payload = fallback_payload()
        if payload:
            return jsonify(payload)
        return jsonify({"success": False, "error": "Mesaj servisi hazır değil."}), 503

    try:
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=220,
            temperature=0.9,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": (
                        "Bu ziyaret için yeni ve özgün bir not yaz. "
                        "Öncekilerden farklı, sade ve sıcak olsun."
                    ),
                }
            ],
        )

        response_text = message.content[0].text.strip()
        parsed = parse_ai_message(response_text)

        return jsonify({
            "success": True,
            "tr": parsed["TR"],
            "fa": parsed["FA"],
            "anlam": parsed["ANLAM"],
            "source": "api",
        })

    except Exception:
        payload = fallback_payload()
        if payload:
            return jsonify(payload)
        return jsonify({"success": False, "error": "Mesaj şu anda hazırlanamadı."}), 503


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
