# Little Surprise — Midnight Angel

A small private digital gift built around a black-heart, rose-gold angel and subtle carbon-fiber visual language.

The experience is intentionally quiet: a password-protected entrance, a sealed digital letter, a short scene-by-scene story, and one fresh Turkish + Farsi note generated for the moment.

## V2 experience

- Midnight black / rose-gold visual system
- Subtle carbon-fiber texture
- Animated sealed-letter reveal
- Six-step mobile-first story flow
- Turkish + Farsi presentation
- Protected AI message endpoint
- Offline/fallback message database
- Reduced-motion support
- QR-code generator
- No-store and basic privacy/security headers

## Project structure

```txt
little-surprise/
├── app.py
├── requirements.txt
├── Procfile
├── README.md
├── LICENSE
├── PRIVACY.md
├── .gitignore
├── .env.example
├── templates/
│   └── index.html
├── data/
│   └── messages.json
└── scripts/
    └── generate_qr.py
```

## Environment variables

Set these on Render:

```txt
ANTHROPIC_API_KEY=your_api_key_here
SITE_PASSWORD=choose_a_private_site_password
SECRET_KEY=generate_a_long_random_secret
MODEL_NAME=claude-sonnet-4-6
COOKIE_SECURE=true
```

`MODEL_NAME` is optional.

`SECRET_KEY` should be a long random value so Flask sessions remain valid across Gunicorn workers and restarts.

For local HTTP development only, set:

```txt
COOKIE_SECURE=false
```

`ACCESS_PASSWORD` remains accepted temporarily for compatibility, but `SITE_PASSWORD` is the preferred variable.

## Deploy on Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT --workers 2
```

## Generate the QR code

```bash
python scripts/generate_qr.py https://your-render-url.onrender.com
```

By default this creates `tannaz_qr.png`.

## Privacy note

This is a personal gift. Do not commit real passwords, API keys or private media to the repository. Keep secrets in Render environment variables.
