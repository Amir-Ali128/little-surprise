from flask import Flask, render_template, request, jsonify, session
import anthropic
import hashlib
import hmac
import json
import os
import random
import time

app = Flask(__name__)

SITE_PASSWORD = (
    os.environ.get("SITE_PASSWORD")
    or os.environ.get("ACCESS_PASSWORD")
    or ""
).strip()

secret_seed = os.environ.get("FLASK_SECRET_KEY")
if not secret_seed:
    secret_seed = hashlib.sha256(
        (SITE_PASSWORD + "|little-surprise-v2").encode("utf-8")
    ).hexdigest()

app.secret_key = secret_seed
app.config.update(
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE="Lax",
    SESSION_COOKIE_SECURE=os.environ.get("RENDER", "").lower() == "true",
)

MODEL_NAME = os.environ.get("MODEL_NAME", "claude-sonnet-4-6")
MESSAGE_COOLDOWN_SECONDS = 10

SYSTEM_PROMPT = """Sen Türkçe ve Farsça bilen, zarif ve doğal yazan bir yazarsın.
Bu metin özel bir dijital hediyenin son sahnesinde gösterilecek.

Ton:
- sıcak, sakin ve samimi
- şiirsel ama abartısız
- karşı taraftan hiçbir şey istemeyen, baskı yaratmayan
- klişe aşk ilanlarından uzak
- kısa ve doğal

Kurallar:
- Türkçe mesaj 1-2 kısa cümle olsun
- Farsça mesaj 1 kısa cümle olsun
- Farsça mesajın doğal Türkçe anlamını da ver
- "sonsuz", "kader", "sensiz yaşayamam" gibi ağır ifadeler kullanma
- Her seferinde özgün yaz

SADECE geçerli JSON döndür:
{"tr":"...","fa":"...","anlam":"..."}"""

FALLBACK_MESSAGES = [
    {
        "tr": "Bazı insanlar bir anı güzelleştirmek için fazla bir şey yapmaz; sadece orada olmaları yeter.",
        "fa": "بودنت بعضی لحظه‌ها را زیباتر می‌کند",
        "anlam": "Varlığın bazı anları daha güzel yapıyor.",
    },
    {
        "tr": "Bazen insanın aklında kalan şey büyük bir olay değil, küçük bir gülümsemedir.",
        "fa": "لبخندت از آن چیزهایی‌ست که در ذهن می‌ماند",
        "anlam": "Gülüşün akılda kalan şeylerden biri.",
    },
    {
        "tr": "Bu küçük sayfa sadece güzel bir anda karşına çıksın diye burada.",
        "fa": "این صفحه فقط برای یک لبخند کوچک ساخته شده",
        "anlam": "Bu sayfa yalnızca küçük bir gülümseme için yapıldı.",
    },
    {
        "tr": "Bazı şeyleri uzun uzun anlatmak gerekmiyor. İyi ki yollarımız bir yerde kesişmiş.",
        "fa": "خوشحالم که جایی در مسیر زندگی همدیگر را شناختیم",
        "anlam": "Hayat yolunda bir yerde birbirimizi tanıdığımıza seviniyorum.",
    },
    {
        "tr": "Bir gün bu sayfayı yeniden açarsan, umarım yine yüzünde küçük bir gülümseme olur.",
        "fa": "امیدوارم هر بار که این را می‌بینی لبخند بزنی",
        "anlam": "Umarım bunu her gördüğünde gülümsersin.",
    },
]


def normalize_password(value):
    return (value or "").strip().casefold().replace(" ", "")


def has_access():
    return session.get("gift_access") is True


def fallback_message():
    payload = random.choice(FALLBACK_MESSAGES).copy()
    payload.update({"success": True, "source": "fallback"})
    return payload


@app.after_request
def add_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cache-Control"] = "no-store"
    return response


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/verify", methods=["POST"])
def verify():
    if not SITE_PASSWORD:
        return jsonify({
            "success": False,
            "error": "site_not_configured",
        }), 503

    data = request.get_json(silent=True) or {}
    submitted = normalize_password(data.get("password"))
    expected = normalize_password(SITE_PASSWORD)

    success = bool(submitted) and hmac.compare_digest(submitted, expected)
    if success:
        session.clear()
        session["gift_access"] = True
        session["verified_at"] = int(time.time())

    return jsonify({"success": success})


@app.route("/get_message", methods=["GET"])
def get_message():
    if not has_access():
        return jsonify({
            "success": False,
            "error": "unauthorized",
        }), 401

    now = time.time()
    last_request = float(session.get("last_message_at", 0))
    retry_after = MESSAGE_COOLDOWN_SECONDS - (now - last_request)

    if retry_after > 0:
        return jsonify({
            "success": False,
            "error": "slow_down",
            "retry_after": max(1, int(retry_after) + 1),
        }), 429

    api_key = os.environ.get("ANTHROPIC_API_KEY")

    try:
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")

        client = anthropic.Anthropic(api_key=api_key)
        message = client.messages.create(
            model=MODEL_NAME,
            max_tokens=260,
            system=SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": "Bu ana özel, yeni ve özgün bir mesaj yaz.",
                }
            ],
        )

        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.strip("`")
            if raw.startswith("json"):
                raw = raw[4:].strip()

        payload = json.loads(raw)
        tr_msg = str(payload.get("tr", "")).strip()
        fa_msg = str(payload.get("fa", "")).strip()
        meaning = str(payload.get("anlam", "")).strip()

        if not tr_msg or not fa_msg or not meaning:
            raise ValueError("Incomplete model response")

        session["last_message_at"] = now
        return jsonify({
            "success": True,
            "tr": tr_msg[:320],
            "fa": fa_msg[:240],
            "anlam": meaning[:280],
            "source": "api",
        })

    except Exception as exc:
        app.logger.warning("AI message fallback used: %s", exc)
        session["last_message_at"] = now
        return jsonify(fallback_message())


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
