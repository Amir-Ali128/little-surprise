# Little Surprise — Midnight Angel

A private, mobile-first digital gift built around a black / rose-gold / carbon-fiber visual language.

The experience is intentionally small and personal:

1. A password-protected entrance
2. A sealed digital envelope
3. A four-part letter revealed one step at a time
4. A final Turkish + Farsi message generated for that moment
5. Curated local fallback messages if the AI provider is unavailable

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
SITE_PASSWORD=your_private_password
FLASK_SECRET_KEY=a_long_random_secret
MODEL_NAME=claude-sonnet-4-6
```

`MODEL_NAME` is optional.

For backward compatibility, `ACCESS_PASSWORD` is also accepted if `SITE_PASSWORD` is not present. New deployments should use `SITE_PASSWORD`.

Do not commit real passwords or API keys to the repository.

## Deploy on Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Generate the physical QR code

```bash
python scripts/generate_qr.py https://your-render-url.onrender.com
```

This creates `tannaz_qr.png` by default.

## V2 notes

Midnight Angel removes the rotating pastel themes in favor of one consistent visual identity: near-black, rose gold, soft champagne highlights, and a deliberately subtle carbon-fiber texture.

The message endpoint is session-protected. A successful password verification creates the session required to request the final generated message.
