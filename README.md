# A Small Gift

This small project was made to bring a smile to someone special.

Some gifts do not fit inside a box.  
Some are hidden in a few lines of code, in tiny details, and in a little bit of effort.

This is one of them.

— Amir

---

## Project Structure

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

## Environment Variables

Set these variables on Render:

```txt
ANTHROPIC_API_KEY=your_api_key_here
ACCESS_PASSWORD=your_access_password_here
MODEL_NAME=claude-sonnet-4-6
```

`MODEL_NAME` is optional. If you do not set it, the app uses the default value in `app.py`.

## Deploy on Render

Build command:

```bash
pip install -r requirements.txt
```

Start command:

```bash
gunicorn app:app --bind 0.0.0.0:$PORT
```

## Generate QR Code

```bash
python scripts/generate_qr.py https://your-render-url.onrender.com
```

This creates a `tannaz_qr.png` file.
