"""
╔══════════════════════════════════════════════════════╗
║           ManoKart — Unified Flask Server            ║
║                                                      ║
║  Run:  python app.py                                 ║
║  URL:  http://localhost:5000                         ║
║                                                      ║
║  Routes:                                             ║
║    /                   → Hub home page               ║
║    /chatbot            → chatbot/chatbot.py UI       ║
║    /diary              → DiaryApp.jsx (ROOT folder)  ║
║    /music              → Mood Music page             ║
║    /voice              → Voice Journal page           ║
║    /games              → games/manokart_games_hub    ║
║    /games/<name>       → Individual game pages       ║
║    /api/chat           → Chatbot ML endpoint         ║
║    /api/entries/...    → Diary CRUD                  ║
║    /api/upload         → Photo upload                ║
║    /api/analyze        → AI mood analysis            ║
║    /api/analytics      → Mood statistics             ║
║    /api/export/pdf     → Export diary as PDF         ║
║    /api/music/recommend→ Music recommendations       ║
║    /api/voice/analyze  → Voice emotion detection     ║
╚══════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import uuid
import io
import pickle
import re
import urllib.request
import urllib.error
import functools
from datetime import datetime, date
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

from flask import (
    Flask, request, jsonify, session, redirect, url_for,
    send_file, send_from_directory, render_template_string
)
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer,
    Table, TableStyle, Image as RLImage, HRFlowable
)
from reportlab.lib.enums import TA_CENTER

# ──────────────────────────────────────────────────────────────
#  PATH SETUP
# ──────────────────────────────────────────────────────────────
BACKEND_DIR  = Path(__file__).parent
ROOT         = BACKEND_DIR.parent
GAMES_DIR    = ROOT / "games"
DATA_DIR     = ROOT / "data"
ML_DIR       = ROOT / "ml"
CHATBOT_DIR  = ROOT / "chatbot"
UPLOADS_DIR  = DATA_DIR / "uploads"
DIARY_FILE   = DATA_DIR / "diary.json"
DIARY_JSX    = ROOT / "DiaryApp.jsx"
TEMPLATES_DIR = BACKEND_DIR / "templates"

for d in [DATA_DIR, UPLOADS_DIR, GAMES_DIR, ML_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────
#  FLASK APP
# ──────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.secret_key = os.environ.get("FLASK_SECRET", "manokart-dev-secret-change-in-prod")

ANTHROPIC_API_KEY = ""
ALLOWED_IMG       = {"png", "jpg", "jpeg", "gif", "webp"}

# ──────────────────────────────────────────────────────────────
#  CORS
# ──────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    return response

@app.before_request
def handle_options():
    if request.method == "OPTIONS":
        from flask import make_response
        res = make_response("", 204)
        return res

# ──────────────────────────────────────────────────────────────
#  FIX 1 — _FixedUnpickler & NLTK Preprocessing
#  Defines the NLTK-enabled preprocess matching train_model.py
#  and maps pickled preprocess lookups to it.
# ──────────────────────────────────────────────────────────────
try:
    import nltk
    nltk.download("wordnet",   quiet=True)
    nltk.download("omw-1.4",  quiet=True)
    nltk.download("stopwords", quiet=True)
    from nltk.stem import WordNetLemmatizer
    from nltk.corpus import stopwords as _sw
    _LEMMATIZER = WordNetLemmatizer()
    _STOPWORDS  = set(_sw.words("english")) - {
        "no","not","never","very","too","i","me","my","myself",
        "can","can't","cannot","won't","don't","didn't","doesn't",
        "feel","feeling","felt","want","need","help"
    }
    _USE_NLTK = True
except Exception:
    _USE_NLTK = False

def preprocess(text: str) -> str:
    text = text.lower().strip()
    contractions = {
        "i'm":"i am","i've":"i have","i'd":"i would","i'll":"i will",
        "can't":"cannot","won't":"will not","don't":"do not",
        "doesn't":"does not","didn't":"did not","isn't":"is not",
        "aren't":"are not","wasn't":"was not","weren't":"were not",
        "haven't":"have not","hasn't":"has not","hadn't":"had not",
        "shouldn't":"should not","wouldn't":"would not","couldn't":"could not",
        "it's":"it is","that's":"that is","there's":"there is",
        "they're":"they are","we're":"we are",
    }
    for c, e in contractions.items():
        text = text.replace(c, e)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if _USE_NLTK:
        tokens = text.split()
        tokens = [_LEMMATIZER.lemmatize(t) for t in tokens if t not in _STOPWORDS]
        text   = " ".join(tokens)
    return text

class _FixedUnpickler(pickle.Unpickler):
    def find_class(self, module, name):
        if name == "preprocess":
            return preprocess
        if name in ("predict_intent", "predict_fn", "crisis_check", "crisis_check_fn"):
            return None
        try:
            return super().find_class(module, name)
        except Exception:
            if module == "__main__":
                return None
            raise

# ──────────────────────────────────────────────────────────────
#  ML MODEL
# ──────────────────────────────────────────────────────────────
_ml_bundle = None

def load_ml_model():
    global _ml_bundle
    if _ml_bundle is not None:
        return _ml_bundle

    search_paths = [
        CHATBOT_DIR / "manokart_model.pkl",
        ML_DIR      / "manokart_model.pkl",
    ]

    for model_path in search_paths:
        if model_path.exists():
            try:
                # FIX: use _FixedUnpickler first, fall back to plain pickle
                with open(model_path, "rb") as f:
                    try:
                        data = _FixedUnpickler(f).load()
                    except Exception:
                        f.seek(0)
                        data = pickle.load(f)

                if isinstance(data, dict):
                    # Accept both new ('ensemble') and old ('pipeline'/'model') formats
                    if "ensemble" in data or "pipeline" in data or "model" in data:
                        _ml_bundle = data
                        app.logger.info(f"✅ Loaded ML model from {model_path}")
                        return _ml_bundle
            except Exception as e:
                app.logger.warning(f"Failed to load model from {model_path}: {e}")
                continue

    app.logger.warning("⚠️  No ML model found — chatbot will use keyword replies only.")
    return None

# ──────────────────────────────────────────────────────────────
#  RECOMMENDATION MODELS (Random Forest & LSTM)
# ──────────────────────────────────────────────────────────────
_recommendation_rf = None
_mood_lstm = None

def load_recommendation_models():
    global _recommendation_rf, _mood_lstm
    if _recommendation_rf is not None and _mood_lstm is not None:
        return _recommendation_rf, _mood_lstm

    # Load Random Forest
    rf_path = CHATBOT_DIR / "recommendation_rf.pkl"
    if rf_path.exists():
        try:
            with open(rf_path, "rb") as f:
                _recommendation_rf = pickle.load(f)
            app.logger.info("✅ Loaded Random Forest activity recommender model.")
        except Exception as e:
            app.logger.warning(f"Failed to load RF recommender: {e}")

    # Load LSTM
    lstm_path = CHATBOT_DIR / "mood_lstm.pt"
    if lstm_path.exists():
        try:
            import torch
            import sys
            sys.path.append(str(CHATBOT_DIR))
            from recommendation_models import MoodLSTM
            model = MoodLSTM(input_size=1, hidden_size=16, num_layers=1, output_size=1)
            model.load_state_dict(torch.load(lstm_path, weights_only=True))
            model.eval()
            _mood_lstm = model
            app.logger.info("✅ Loaded PyTorch Mood LSTM model.")
        except Exception as e:
            app.logger.warning(f"Failed to load Mood LSTM: {e}")

    return _recommendation_rf, _mood_lstm

# ──────────────────────────────────────────────────────────────
#  DIARY HELPERS
# ──────────────────────────────────────────────────────────────
def load_diary() -> dict:
    if DIARY_FILE.exists():
        try:
            return json.loads(DIARY_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"entries": {}, "created": datetime.utcnow().isoformat()}


def save_diary(data: dict):
    DIARY_FILE.write_text(
        json.dumps(data, indent=2, default=str, ensure_ascii=False),
        encoding="utf-8"
    )


def allowed_file(filename: str) -> bool:
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_IMG


# ──────────────────────────────────────────────────────────────
#  GAME LIST
# ──────────────────────────────────────────────────────────────
GAME_META = {
    "manokart_body_breath_quest":   {"title": "Body & Breath Quest",  "emoji": "🧘", "desc": "Calm your nervous system with guided breathing"},
    "manokart_calm_grid_sudoku":    {"title": "Calm Grid Sudoku",     "emoji": "🔢", "desc": "A soothing number puzzle for a focused mind"},
    "manokart_color_your_world":    {"title": "Color Your World",     "emoji": "🎨", "desc": "Express your mood through colour"},
    "manokart_cozy_island_garden":  {"title": "Cozy Island Garden",   "emoji": "🌴", "desc": "Escape to a gentle island adventure"},
    "manokart_mood_blocks_tetris":  {"title": "Mood Blocks Tetris",   "emoji": "🟦", "desc": "Stack blocks and release tension"},
    "manokart_spirit_journey":      {"title": "Spirit Journey",       "emoji": "✨", "desc": "A mindful journey through nature"},
    "manokart_stress_relief_ocean": {"title": "Stress Relief Ocean",  "emoji": "🌊", "desc": "Breathe with the waves"},
}

def get_available_games() -> list:
    games = []
    for stem, meta in GAME_META.items():
        path = GAMES_DIR / f"{stem}.html"
        if path.exists():
            games.append({"slug": stem, "path": str(path), **meta})
    for path in sorted(GAMES_DIR.glob("manokart_*.html")):
        stem = path.stem
        if stem not in GAME_META and stem not in ("manokart_hub_home_screen", "manokart_games_hub"):
            games.append({
                "slug":  stem,
                "title": stem.replace("manokart_", "").replace("_", " ").title(),
                "emoji": "🎮",
                "desc":  "A ManoKart activity",
                "path":  str(path),
            })
    return games


# ══════════════════════════════════════════════════════════════
#  TEMPLATES
# ══════════════════════════════════════════════════════════════

HUB_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>ManoKart — Your Wellness Hub</title>
  <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display:ital@0;1&family=Outfit:wght@300;400;500;600&display=swap" rel="stylesheet"/>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    :root{
      --sage:#0F6E56;--sage-mid:#1D9E75;--sage-light:#5DCAA5;
      --sage-pale:#9FE1CB;--sage-ghost:#E1F5EE;
      --warm-white:#f9f8f4;--ink:#2C2C2A;--muted:#5F5E5A;--hint:#B4B2A9;
      --card-border:rgba(93,202,165,.18);
    }
    body{font-family:'Outfit',sans-serif;background:var(--warm-white);color:var(--ink);min-height:100vh;overflow-x:hidden}
    body::before{content:'';position:fixed;inset:0;z-index:0;background:radial-gradient(ellipse 70% 60% at 10% 0%,rgba(93,202,165,.13) 0%,transparent 70%),radial-gradient(ellipse 50% 40% at 90% 20%,rgba(253,244,248,.9) 0%,transparent 60%),radial-gradient(ellipse 60% 50% at 50% 100%,rgba(255,251,242,.8) 0%,transparent 60%);pointer-events:none}
    .orb{position:fixed;border-radius:50%;filter:blur(60px);opacity:.35;z-index:0;animation:drift 12s ease-in-out infinite alternate}
    .orb1{width:320px;height:320px;background:#9FE1CB;top:-80px;left:-80px;animation-delay:0s}
    .orb2{width:240px;height:240px;background:#f4c0d1;top:30%;right:-60px;animation-delay:-4s}
    .orb3{width:200px;height:200px;background:#fac775;bottom:10%;left:20%;animation-delay:-8s}
    @keyframes drift{0%{transform:translate(0,0) scale(1)}100%{transform:translate(30px,20px) scale(1.08)}}
    .page{position:relative;z-index:1;max-width:980px;margin:0 auto;padding:0 28px 80px}
    .topbar{display:flex;align-items:center;justify-content:space-between;padding:28px 0 0}
    .logo{font-family:'DM Serif Display',serif;font-size:1.5rem;color:var(--sage);letter-spacing:-.5px;display:flex;align-items:center;gap:10px;text-decoration:none}
    .nav-pill{display:flex;gap:8px}
    .nav-btn{padding:8px 18px;border-radius:99px;border:1.5px solid var(--card-border);background:rgba(255,255,255,.7);color:var(--muted);font-family:'Outfit',sans-serif;font-size:.85rem;font-weight:500;cursor:pointer;transition:all .2s;backdrop-filter:blur(8px);text-decoration:none;display:inline-block}
    .nav-btn:hover{background:var(--sage);color:white;border-color:var(--sage)}
    .hero{display:grid;grid-template-columns:1fr 1fr;gap:32px;align-items:center;padding:52px 0 16px}
    @media(max-width:640px){.hero{grid-template-columns:1fr}.profile-card{display:none}}
    .greeting-tag{display:inline-flex;align-items:center;gap:8px;background:rgba(159,225,203,.25);border:1px solid rgba(93,202,165,.3);border-radius:99px;padding:6px 16px;font-size:.8rem;color:var(--sage-mid);font-weight:500;margin-bottom:18px}
    .greeting-tag .dot{width:7px;height:7px;background:var(--sage-light);border-radius:50%;animation:pulse 2s infinite}
    @keyframes pulse{0%,100%{opacity:1;transform:scale(1)}50%{opacity:.5;transform:scale(.8)}}
    .hero h1{font-family:'DM Serif Display',serif;font-size:3.2rem;line-height:1.1;color:var(--ink);letter-spacing:-1.5px;margin-bottom:14px}
    .hero h1 em{color:var(--sage);font-style:italic}
    .hero-sub{font-size:1.05rem;color:var(--muted);line-height:1.65;font-weight:300;max-width:380px;margin-bottom:28px}
    .hero-cta{display:flex;gap:12px;flex-wrap:wrap}
    .btn-primary{padding:14px 28px;border-radius:99px;border:none;background:var(--sage);color:white;font-family:'Outfit',sans-serif;font-size:.95rem;font-weight:500;cursor:pointer;transition:all .2s;box-shadow:0 4px 20px rgba(15,110,86,.2);text-decoration:none;display:inline-block}
    .btn-primary:hover{background:var(--sage-mid);transform:translateY(-1px);box-shadow:0 8px 28px rgba(15,110,86,.28)}
    .btn-ghost{padding:14px 28px;border-radius:99px;border:1.5px solid var(--card-border);background:rgba(255,255,255,.6);color:var(--sage);font-family:'Outfit',sans-serif;font-size:.95rem;font-weight:500;cursor:pointer;transition:all .2s;backdrop-filter:blur(8px);text-decoration:none;display:inline-block}
    .btn-ghost:hover{border-color:var(--sage);background:var(--sage-ghost)}
    .profile-card{background:rgba(255,255,255,.75);border:1px solid var(--card-border);border-radius:28px;padding:28px;backdrop-filter:blur(12px);box-shadow:0 8px 40px rgba(93,202,165,.08)}
    .profile-top{display:flex;align-items:center;gap:16px;margin-bottom:20px;transition:opacity .15s}
    .profile-top:hover{opacity:0.85}
    .profile-top:hover .profile-join{color:var(--sage-mid);text-decoration:underline}
    .avatar{width:58px;height:58px;border-radius:50%;background:linear-gradient(135deg,#9FE1CB,#5DCAA5);display:flex;align-items:center;justify-content:center;font-family:'DM Serif Display',serif;font-size:1.4rem;color:white;flex-shrink:0}
    .profile-name{font-size:1.1rem;font-weight:600;color:var(--ink)}
    .profile-join{font-size:.78rem;color:var(--hint);margin-top:3px;transition:color .15s}
    .streak-badge{display:flex;align-items:center;gap:6px;background:rgba(255,183,77,.12);border:1px solid rgba(239,159,39,.3);border-radius:99px;padding:5px 12px;font-size:.78rem;font-weight:500;color:#854F0B;margin-top:8px;width:fit-content}
    .stats-row{display:grid;grid-template-columns:1fr 1fr 1fr;gap:10px;margin-bottom:18px}
    .stat-box{background:var(--warm-white);border-radius:14px;padding:12px;text-align:center;border:1px solid rgba(209,208,199,.4)}
    .stat-num{font-family:'DM Serif Display',serif;font-size:1.6rem;color:var(--sage);line-height:1}
    .stat-lbl{font-size:.72rem;color:var(--hint);margin-top:4px}
    .mood-check{font-size:.8rem;color:var(--muted);margin-bottom:8px;font-weight:500}
    .mood-row{display:flex;gap:8px}
    .mood-chip{flex:1;padding:8px 6px;border-radius:12px;border:1.5px solid var(--card-border);background:white;font-size:1.1rem;cursor:pointer;text-align:center;transition:all .18s}
    .mood-chip:hover,.mood-chip.active{border-color:var(--sage-light);background:var(--sage-ghost);transform:scale(1.08)}
    .section-head{display:flex;align-items:baseline;justify-content:space-between;margin:44px 0 18px}
    .section-head h2{font-family:'DM Serif Display',serif;font-size:1.55rem;color:var(--ink);letter-spacing:-.5px}
    .see-all{font-size:.82rem;color:var(--sage-light);cursor:pointer;font-weight:500;text-decoration:none}
    .see-all:hover{color:var(--sage)}
    .feature-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:16px}
    @media(max-width:480px){.feature-grid{grid-template-columns:1fr}}
    .feat-card{border-radius:24px;padding:28px 26px;position:relative;overflow:hidden;cursor:pointer;transition:transform .22s,box-shadow .22s;text-decoration:none;display:block;color:inherit}
    .feat-card:hover{transform:translateY(-4px);box-shadow:0 16px 48px rgba(0,0,0,.08)}
    .feat-card.diary{background:linear-gradient(135deg,#e8f8f2,#d4f0e6);border:1px solid rgba(93,202,165,.2)}
    .feat-card.chat{background:linear-gradient(135deg,#fbeaf0,#f4d4e4);border:1px solid rgba(212,83,126,.15)}
    .feat-card.music{background:linear-gradient(135deg,#ede9fe,#ddd6fe);border:1px solid rgba(124,58,237,.15)}
    .feat-card.voice{background:linear-gradient(135deg,#fef3c7,#fde68a);border:1px solid rgba(239,159,39,.2)}
    .feat-icon{font-size:2.2rem;margin-bottom:14px}
    .feat-card h3{font-size:1.1rem;font-weight:600;color:var(--ink);margin-bottom:6px}
    .feat-card p{font-size:.85rem;color:var(--muted);line-height:1.55;font-weight:300}
    .feat-card .feat-arrow{position:absolute;bottom:22px;right:22px;width:36px;height:36px;border-radius:50%;background:white;display:flex;align-items:center;justify-content:center;font-size:1rem;box-shadow:0 2px 12px rgba(0,0,0,.07);transition:transform .18s}
    .feat-card:hover .feat-arrow{transform:translate(2px,-2px)}
    .feat-tag{display:inline-flex;align-items:center;gap:5px;font-size:.72rem;font-weight:600;letter-spacing:.04em;text-transform:uppercase;padding:4px 10px;border-radius:99px;margin-bottom:10px}
    .feat-tag.new{background:rgba(15,110,86,.12);color:var(--sage)}
    .feat-tag.ai{background:rgba(212,83,126,.12);color:#993556}
    .feat-tag.music{background:rgba(124,58,237,.12);color:#7C3AED}
    .feat-tag.voice{background:rgba(239,159,39,.12);color:#B45309}
    .games-strip{display:flex;gap:14px;overflow-x:auto;padding-bottom:8px;scrollbar-width:none}
    .games-strip::-webkit-scrollbar{display:none}
    .game-card{flex-shrink:0;width:160px;background:rgba(255,255,255,.8);border:1px solid var(--card-border);border-radius:20px;padding:20px 16px;cursor:pointer;transition:all .2s;text-decoration:none;display:block;color:inherit;backdrop-filter:blur(6px)}
    .game-card:hover{transform:translateY(-3px);box-shadow:0 10px 32px rgba(93,202,165,.15);border-color:var(--sage-pale)}
    .g-icon{font-size:1.8rem;margin-bottom:10px}
    .game-card h4{font-size:.85rem;font-weight:600;color:var(--ink);margin-bottom:4px}
    .game-card p{font-size:.75rem;color:var(--hint);line-height:1.4}
    .quote-strip{background:linear-gradient(135deg,rgba(15,110,86,.06),rgba(93,202,165,.08));border:1px solid rgba(93,202,165,.15);border-radius:20px;padding:24px 28px;margin-top:20px;display:flex;align-items:center;gap:20px}
    .quote-mark{font-family:'DM Serif Display',serif;font-size:4rem;color:var(--sage-pale);line-height:1;flex-shrink:0;margin-top:-12px}
    .quote-text{font-family:'DM Serif Display',serif;font-size:1.05rem;color:var(--sage);font-style:italic;line-height:1.6}
    .quote-author{font-size:.78rem;color:var(--hint);margin-top:6px}
    footer{text-align:center;padding:40px 0 20px;font-size:.8rem;color:var(--hint)}
    footer span{color:var(--sage-light)}
    .fade-up{opacity:0;transform:translateY(24px);animation:fadeUp .6s ease forwards}
    @keyframes fadeUp{to{opacity:1;transform:translateY(0)}}
    .d1{animation-delay:.05s}.d2{animation-delay:.13s}.d3{animation-delay:.21s}.d4{animation-delay:.3s}.d5{animation-delay:.38s}
    .xp-nav{display:flex;align-items:center;gap:8px;background:rgba(255,255,255,.7);border:1.5px solid var(--card-border);border-radius:99px;padding:6px 14px;backdrop-filter:blur(8px)}
    .xp-nav .lv{font-size:.75rem;font-weight:600;color:var(--sage);white-space:nowrap}
    .xp-track{width:60px;height:5px;background:rgba(93,202,165,.2);border-radius:3px;overflow:hidden}
    .xp-fill{height:100%;background:var(--sage-light);border-radius:3px;transition:width .4s}
    .xp-nav .xp-num{font-size:.72rem;color:var(--hint);white-space:nowrap}
  </style>
</head>
<body>
<div class="orb orb1"></div>
<div class="orb orb2"></div>
<div class="orb orb3"></div>

<div class="page">
  <div class="topbar">
    <a href="/" class="logo">🌿 ManoKart</a>
    <nav class="nav-pill">
      <div class="xp-nav" id="xp-nav" style="display:none">
        <span class="lv" id="nav-lv">Lv 1</span>
        <div class="xp-track"><div class="xp-fill" id="nav-xp-fill" style="width:0%"></div></div>
        <span class="xp-num" id="nav-xp-num">0 XP</span>
      </div>
      <a href="/diary"   class="nav-btn">Diary</a>
      <a href="/chatbot" class="nav-btn">Chat</a>
      <a href="/music"   class="nav-btn">Music</a>
      <a href="/voice"   class="nav-btn">Voice</a>
      <a href="games/manokart_games_hub.html"   class="nav-btn">Games</a>
      <a href="/clinical" class="nav-btn">Check-in</a>
      <a href="/therapists" class="nav-btn">Therapists</a>
      <a href="/profile" class="nav-btn">Profile</a>
      <a href="#" class="nav-btn" onclick="fetch('/api/auth/logout',{method:'POST'}).then(()=>window.location.href='/auth')" style="border-color:rgba(212,83,126,.3);color:#993556">Logout</a>
    </nav>
  </div>

  <div class="hero">
    <div class="hero-left fade-up d1">
      <div class="greeting-tag"><span class="dot"></span> <span id="greeting">Good day</span>, friend</div>
      <h1>Your <em>gentle</em><br>space to<br>feel better</h1>
      <p class="hero-sub">Track your mood, journal your thoughts, and chat whenever you need a kind listener.</p>
      <div class="hero-cta">
        <a href="/diary"   class="btn-primary">Open My Diary</a>
        <a href="/chatbot" class="btn-ghost">Talk to ManoKart</a>
      </div>
    </div>

    <div class="profile-card fade-up d2">
      <div class="profile-top" onclick="window.location.href='/profile'" style="cursor:pointer" title="View Profile & Stats">
        <div class="avatar">🌿</div>
        <div>
          <div class="profile-name" id="profile-name">Welcome back 🌸</div>
          <div class="profile-join">View Profile & Stats →</div>
          <div class="streak-badge" id="streak-display">🌱 Loading...</div>
          <div class="streak-badge" style="margin-top:4px;background:rgba(93,202,165,.12);border-color:rgba(93,202,165,.3);color:var(--sage)" id="forecast-display">🔮 Forecast: Loading...</div>
        </div>
      </div>
      <div class="stats-row">
        <div class="stat-box">
          <div class="stat-num" id="stat-entries">—</div>
          <div class="stat-lbl">Entries</div>
        </div>
        <div class="stat-box">
          <div class="stat-num" id="stat-mood">—</div>
          <div class="stat-lbl">Avg Mood</div>
        </div>
        <div class="stat-box">
          <div class="stat-num" id="stat-streak">—</div>
          <div class="stat-lbl">Streak</div>
        </div>
      </div>
      <div class="mood-check">How are you feeling right now?</div>
      <div class="mood-row">
        <div class="mood-chip" onclick="pickMood(this,1)" title="Struggling">😔</div>
        <div class="mood-chip" onclick="pickMood(this,2)" title="Low">😐</div>
        <div class="mood-chip" onclick="pickMood(this,3)" title="Okay">🙂</div>
        <div class="mood-chip" onclick="pickMood(this,4)" title="Good">😊</div>
        <div class="mood-chip" onclick="pickMood(this,5)" title="Great">🌟</div>
      </div>
    </div>
  </div>

  <div class="section-head fade-up d3">
    <h2>Your Wellness Tools</h2>
  </div>
  <div class="feature-grid fade-up d3">
    <a class="feat-card diary" href="/diary">
      <div class="feat-tag new">✦ Featured</div>
      <div class="feat-icon">📖</div>
      <h3>My Diary</h3>
      <p>Write freely, track your mood journey, and receive gentle AI reflections crafted just for you.</p>
      <div class="feat-arrow">→</div>
    </a>
    <a class="feat-card chat" href="/chatbot">
      <div class="feat-tag ai">✦ AI Powered</div>
      <div class="feat-icon">💬</div>
      <h3>ManoKart Chat</h3>
      <p>Your always-available companion. Talk through anything — worries, wins, or just how your day went.</p>
      <div class="feat-arrow">→</div>
    </a>
    <a class="feat-card music" href="/music">
      <div class="feat-tag music">✦ New</div>
      <div class="feat-icon">🎵</div>
      <h3>Mood Music</h3>
      <p>Curated Spotify & YouTube playlists that match your mood — let music be your medicine.</p>
      <div class="feat-arrow">→</div>
    </a>
    <a class="feat-card voice" href="/voice">
      <div class="feat-tag voice">✦ New</div>
      <div class="feat-icon">🎙️</div>
      <h3>Voice Journal</h3>
      <p>Speak freely — we'll transcribe your words and gently detect your emotions from your voice.</p>
      <div class="feat-arrow">→</div>
    </a>
    <a class="feat-card clinical" href="/clinical" style="background:linear-gradient(135deg,#e1f5ee,#9fe1cb);border:1px solid rgba(93,202,165,.2)">
      <div class="feat-tag new" style="background:rgba(15,110,86,.12);color:var(--sage)">✦ Screening</div>
      <div class="feat-icon">📋</div>
      <h3>Clinical Screening</h3>
      <p>Evaluate your depression (PHQ-9) and anxiety (GAD-7) levels using standard clinical questionnaires.</p>
      <div class="feat-arrow">→</div>
    </a>
    <a class="feat-card therapists" href="/therapists" style="background:linear-gradient(135deg,#e0f2fe,#bae6fd);border:1px solid rgba(14,165,233,.15)">
      <div class="feat-tag new" style="background:rgba(14,165,233,.12);color:#0369a1">✦ Directory</div>
      <div class="feat-icon">🤝</div>
      <h3>Therapists</h3>
      <p>Find professional support. Browse, filter by specialty, and schedule appointments with licensed therapists.</p>
      <div class="feat-arrow">→</div>
    </a>
  </div>

  {% if games %}
  <div class="section-head fade-up d4">
    <h2>Wellness Games</h2>
    <a class="see-all" href="games/manokart_games_hub.html">See all →</a>
  </div>
  <div class="games-strip fade-up d4">
    {% for game in games %}
    <a class="game-card" href="games/{{ game.slug }}.html">
      <div class="g-icon">{{ game.emoji }}</div>
      <h4>{{ game.title }}</h4>
      <p>{{ game.desc }}</p>
    </a>
    {% endfor %}
  </div>
  {% endif %}

  <div class="quote-strip fade-up d5">
    <div class="quote-mark">"</div>
    <div>
      <div class="quote-text" id="quote-text">Almost everything will work again if you unplug it for a few minutes — including you.</div>
      <div class="quote-author" id="quote-author">— Anne Lamott</div>
    </div>
  </div>

  <footer>ManoKart &mdash; made with <span>🌿</span> for your wellbeing</footer>
</div>

<script src="/games/gameEngine.js"></script>
<script>
(function(){
  const h = new Date().getHours();
  document.getElementById('greeting').textContent = h < 12 ? 'Good morning' : h < 17 ? 'Good afternoon' : 'Good evening';
})();

function pickMood(el, score) {
  document.querySelectorAll('.mood-chip').forEach(c => c.classList.remove('active'));
  el.classList.add('active');
  const today = new Date().toISOString().split('T')[0];
  fetch('/api/entries/' + today, {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({mood: score})
  }).catch(() => {});
}

fetch('/api/analytics')
  .then(r => r.json())
  .then(d => {
    document.getElementById('stat-entries').textContent = d.total_entries || 0;
    document.getElementById('stat-mood').textContent    = d.avg_mood ? d.avg_mood.toFixed(1) : '—';
    document.getElementById('stat-streak').textContent  = d.streak || 0;
    document.getElementById('streak-display').textContent = d.streak > 0 ? '🔥 ' + d.streak + '-day streak' : '🌱 Start your streak!';
  })
  .catch(() => { document.getElementById('streak-display').textContent = '🌱 Start journaling!'; });

fetch('/api/mood/forecast')
  .then(r => r.json())
  .then(d => {
    document.getElementById('forecast-display').textContent = '🔮 Forecast tomorrow: ' + d.emoji + ' ' + d.mood_name;
  })
  .catch(() => {
    document.getElementById('forecast-display').style.display = 'none';
  });

fetch('/api/auth/me')
  .then(r => r.json())
  .then(d => {
    if (d.logged_in && d.user) {
      const first = (d.user.name || '').split(' ')[0];
      document.getElementById('profile-name').textContent = 'Hey, ' + first + ' 🌸';
      if (d.user.avatar) {
        document.querySelector('.profile-card .avatar').textContent = d.user.avatar;
      }
    }
  })
  .catch(() => {});

function updateXPNav() {
  try {
    var raw = localStorage.getItem('manokart_engine_v1');
    if (!raw) return;
    var data = JSON.parse(raw);
    if (!data || !data.totalXP) return;
    var xpPerLevel = 500;
    var level      = data.level || 1;
    var xpIn       = data.totalXP % xpPerLevel;
    var pct        = Math.round(xpIn / xpPerLevel * 100);
    document.getElementById('nav-lv').textContent       = 'Lv ' + level;
    document.getElementById('nav-xp-fill').style.width = pct + '%';
    document.getElementById('nav-xp-num').textContent   = data.totalXP + ' XP';
    document.getElementById('xp-nav').style.display    = 'flex';
  } catch(e) {}
}

updateXPNav();
window.addEventListener('gameEngineSynced', updateXPNav);

const quotes = [
  {t:"Almost everything will work again if you unplug it for a few minutes — including you.", a:"Anne Lamott"},
  {t:"You don't have to be positive all the time. It's perfectly okay to feel sad, angry, annoyed, frustrated, scared.", a:"Lori Deschene"},
  {t:"In the middle of difficulty lies opportunity.", a:"Albert Einstein"},
  {t:"Self-care is how you take your power back.", a:"Lalah Delia"},
  {t:"Be gentle with yourself. You are a child of the universe, no less than the trees and the stars.", a:"Max Ehrmann"},
  {t:"Every day begins with an act of courage and hope: getting out of bed.", a:"Mason Cooley"},
  {t:"You are enough just as you are.", a:"Meghan Markle"},
];
const q = quotes[new Date().getDate() % quotes.length];
document.getElementById('quote-text').textContent   = q.t;
document.getElementById('quote-author').textContent = '— ' + q.a;
</script>
</body>
</html>"""


DIARY_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>ManoKart — My Diary</title>
  <script src="/static/react.min.js"></script>
  <script src="/static/react-dom.min.js"></script>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{background:#f7fdf9;min-height:100vh}
    #root{min-height:100vh}
  </style>
</head>
<body>
  <div id="root"><div style="display:flex;align-items:center;justify-content:center;min-height:100vh;color:#5DCAA5;font-family:Georgia,serif">Loading your diary… 🌿</div></div>
  <script>
    const { useState, useEffect, useRef, useCallback } = React;
  </script>
  <script src="/static/DiaryApp.js"></script>
  <script>
    const root = ReactDOM.createRoot(document.getElementById('root'));
    root.render(React.createElement(MindfulDiary));
  </script>
</body>
</html>"""


CHATBOT_SHELL = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width,initial-scale=1"/>
  <title>ManoKart — Chat</title>
  <style>
    *{box-sizing:border-box;margin:0;padding:0}
    body{font-family:'Segoe UI',system-ui,sans-serif;background:linear-gradient(135deg,#f7fdf9,#fdf4f8);min-height:100vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:24px}
    .chat-wrap{width:100%;max-width:640px;background:white;border-radius:20px;border:.5px solid #E1F5EE;box-shadow:0 4px 32px rgba(93,202,165,.08);display:flex;flex-direction:column;height:80vh}
    .chat-header{padding:20px 24px;border-bottom:.5px solid #E1F5EE;display:flex;align-items:center;gap:12px}
    .chat-header h1{font-size:1.1rem;color:#0F6E56}
    .chat-header p{font-size:.8rem;color:#5DCAA5;font-style:italic}
    .messages{flex:1;overflow-y:auto;padding:20px;display:flex;flex-direction:column;gap:12px}
    .msg{max-width:80%;padding:12px 16px;border-radius:16px;font-size:.9rem;line-height:1.55}
    .msg.bot{background:#E1F5EE;color:#0F6E56;border-radius:4px 16px 16px 16px;align-self:flex-start}
    .msg.user{background:#0F6E56;color:white;border-radius:16px 4px 16px 16px;align-self:flex-end}
    .input-row{padding:16px 20px;border-top:.5px solid #E1F5EE;display:flex;gap:10px}
    .input-row input{flex:1;padding:10px 16px;border-radius:99px;border:1.5px solid #D3D1C7;font-size:.9rem;outline:none;font-family:inherit}
    .input-row input:focus{border-color:#5DCAA5}
    .input-row button{padding:10px 20px;border-radius:99px;border:none;background:#0F6E56;color:white;font-size:.9rem;cursor:pointer;font-family:inherit}
    .input-row button:hover{background:#5DCAA5}
    .back{display:inline-block;margin-bottom:16px;color:#5DCAA5;text-decoration:none;font-size:.9rem}
    .back:hover{color:#0F6E56}
    .typing{opacity:.5;font-style:italic}
  </style>
</head>
<body>
  <a href="/" class="back">← Back to hub</a>
  <div class="chat-wrap">
    <div class="chat-header">
      <div style="font-size:2rem">💬</div>
      <div>
        <h1>ManoKart Companion</h1>
        <p>I'm here to listen, always 🌿</p>
      </div>
    </div>
    <div class="messages" id="messages">
      <div class="msg bot">Hello 🌸 I'm your ManoKart companion. How are you feeling today?</div>
    </div>
    <div class="input-row">
      <input id="inp" type="text" placeholder="Share what's on your mind..." onkeydown="if(event.key==='Enter')send()"/>
      <button onclick="send()">Send</button>
    </div>
  </div>
  <script>
    const msgs = document.getElementById('messages');
    const inp  = document.getElementById('inp');
    function addMsg(text, role) {
      const d = document.createElement('div');
      d.className = 'msg ' + role;
      d.textContent = text;
      msgs.appendChild(d);
      msgs.scrollTop = msgs.scrollHeight;
      return d;
    }
    async function send() {
      const text = inp.value.trim();
      if (!text) return;
      inp.value = '';
      addMsg(text, 'user');
      const thinking = addMsg('Thinking...', 'bot typing');
      try {
        const res = await fetch('/api/chat', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message:text})});
        if (res.status === 401) {
          thinking.textContent = 'Session expired — redirecting to login...';
          thinking.classList.remove('typing');
          setTimeout(() => window.location.href = '/auth', 1500);
          return;
        }
        let data;
        try { data = await res.json(); } catch { data = {}; }
        if (data.reply) {
          thinking.textContent = data.reply;
        } else if (data.error) {
          thinking.textContent = data.error + ' 🌧️';
        } else {
          thinking.textContent = 'Something went wrong — please try again 🌧️';
        }
        thinking.classList.remove('typing');
      } catch(e) {
        thinking.textContent = 'Could not reach the server. Is it running? 🌿';
        thinking.classList.remove('typing');
      }
    }
  </script>
</body>
</html>"""


# ══════════════════════════════════════════════════════════════
#  AUTH HELPERS
# ══════════════════════════════════════════════════════════════

def login_required(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Login required"}), 401
            return redirect("/auth")
        return f(*args, **kwargs)
    return wrapper


def get_current_user_id():
    return session.get("user_id")


def get_user_role():
    if "role" not in session:
        if "user_id" in session:
            from db import get_user_by_id
            user = get_user_by_id(session["user_id"])
            if user:
                session["role"] = user.get("role", "user")
            else:
                session["role"] = "user"
        else:
            session["role"] = "user"
    return session["role"]


def user_only(f):
    @functools.wraps(f)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Login required"}), 401
            return redirect("/auth")
        if get_user_role() == "therapist":
            if request.path.startswith("/api/"):
                return jsonify({"error": "Access denied. User role required."}), 403
            return redirect("/")
        return f(*args, **kwargs)
    return wrapper


# ══════════════════════════════════════════════════════════════
#  AUTH ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/auth")
def auth_page():
    if "user_id" in session:
        return redirect("/")
    return send_from_directory(ROOT, "manokart-auth.html")


@app.route("/api/auth/signup", methods=["POST"])
def signup():
    from db import create_user, get_user_by_email
    body     = request.get_json(force=True)
    email    = body.get("email", "").strip().lower()
    username = body.get("username", "").strip() or email.split("@")[0]
    name     = body.get("full_name", "").strip() or body.get("first_name", "").strip()
    password = body.get("password", "")
    role     = body.get("role", "user").strip().lower()
    
    if role not in ("user", "therapist"):
        role = "user"

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400
    if get_user_by_email(email):
        return jsonify({"error": "An account with this email already exists"}), 409

    try:
        user = create_user(email, username, name, password, role)
        session["user_id"]   = user["id"]
        session["user_name"] = user["full_name"] or user["username"]
        session["role"]      = user.get("role", "user")
        return jsonify({"ok": True, "user": {"id": user["id"], "name": session["user_name"], "role": user.get("role", "user")}})
    except Exception as e:
        app.logger.error(f"Signup error: {e}")
        return jsonify({"error": "Could not create account. Username or email may be taken."}), 500


@app.route("/api/auth/login", methods=["POST"])
def login():
    from db import check_login
    body     = request.get_json(force=True)
    email    = body.get("email", "").strip().lower()
    password = body.get("password", "")

    if not email or not password:
        return jsonify({"error": "Email and password are required"}), 400

    user = check_login(email, password)
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"]   = user["id"]
    session["user_name"] = user["full_name"] or user["username"]
    session["role"]      = user.get("role", "user")
    return jsonify({"ok": True, "user": {"id": user["id"], "name": session["user_name"], "role": user.get("role", "user")}})


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/auth/me")
def auth_me():
    if "user_id" not in session:
        return jsonify({"logged_in": False}), 401
    from db import get_user_by_id, get_therapist_by_user_id
    user = get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return jsonify({"logged_in": False}), 401
        
    therapist_data = {}
    if user.get("role") == "therapist":
        t_profile = get_therapist_by_user_id(user["id"])
        if t_profile:
            therapist_data = {
                "title": t_profile["title"],
                "specialization": t_profile["specialization"],
                "experience": t_profile["experience"],
                "fees": t_profile["fees"],
                "location": t_profile["location"],
                "availability": t_profile["availability"],
                "bio": t_profile["bio"],
                "phone": t_profile["contact_phone"]
            }
            
    return jsonify({
        "logged_in": True,
        "user": {
            "id":     user["id"],
            "name":   user["full_name"] or user["username"],
            "username": user["username"],
            "email":  user["email"],
            "streak": user["wellness_streak"],
            "avatar": user["avatar_emoji"],
            "role":   user.get("role", "user"),
            "created": user["created_at"].isoformat() if user.get("created_at") else None,
            **therapist_data
        }
    })


# In-memory dictionary for development password reset tokens
RESET_TOKENS = {}


@app.route("/api/profile/update", methods=["POST"])
@login_required
def update_profile():
    from db import update_user_profile, save_therapist_profile, get_user_by_id
    uid = get_current_user_id()
    body = request.get_json(force=True)
    full_name = body.get("full_name", "").strip()
    username = body.get("username", "").strip()
    avatar_emoji = body.get("avatar_emoji", "🌿").strip()

    if not username:
        return jsonify({"error": "Username is required"}), 400

    user = get_user_by_id(uid)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        updated_user = update_user_profile(uid, full_name, username, avatar_emoji)
        if not updated_user:
            return jsonify({"error": "Failed to update profile"}), 500
        
        if user.get("role") == "therapist":
            title = body.get("title", "").strip()
            specialization = body.get("specialization", "").strip()
            experience = int(body.get("experience", 0) or 0)
            fees = int(body.get("fees", 0) or 0)
            location = body.get("location", "").strip()
            availability = body.get("availability", "").strip()
            bio = body.get("bio", "").strip()
            
            # Default email & phone
            email = user["email"]
            phone = body.get("phone", "").strip() or "N/A"
            
            save_therapist_profile(uid, full_name, title, specialization, experience, fees, location, availability, email, phone, bio)
            
        session["user_name"] = updated_user["full_name"] or updated_user["username"]
        
        therapist_data = {}
        if user.get("role") == "therapist":
            from db import get_therapist_by_user_id
            t_profile = get_therapist_by_user_id(uid)
            if t_profile:
                therapist_data = {
                    "title": t_profile["title"],
                    "specialization": t_profile["specialization"],
                    "experience": t_profile["experience"],
                    "fees": t_profile["fees"],
                    "location": t_profile["location"],
                    "availability": t_profile["availability"],
                    "bio": t_profile["bio"],
                    "phone": t_profile["contact_phone"]
                }
                
        return jsonify({
            "ok": True,
            "user": {
                "id":     updated_user["id"],
                "name":   updated_user["full_name"] or updated_user["username"],
                "username": updated_user["username"],
                "email":  updated_user["email"],
                "streak": updated_user["wellness_streak"],
                "avatar": updated_user["avatar_emoji"],
                "role":   updated_user.get("role", "user"),
                **therapist_data
            }
        })
    except Exception as e:
        app.logger.error(f"Profile update error: {e}")
        return jsonify({"error": "Username may already be taken or fields are invalid."}), 500


@app.route("/api/profile/change-password", methods=["POST"])
@login_required
def change_password():
    from db import get_user_by_id, update_user_password
    from werkzeug.security import check_password_hash
    uid = get_current_user_id()
    body = request.get_json(force=True)
    current_pass = body.get("current_password", "")
    new_pass = body.get("new_password", "")

    if not current_pass or not new_pass:
        return jsonify({"error": "Both current and new passwords are required"}), 400
    if len(new_pass) < 6:
        return jsonify({"error": "New password must be at least 6 characters"}), 400

    user = get_user_by_id(uid)
    if not user or not check_password_hash(user["hashed_password"], current_pass):
        return jsonify({"error": "Invalid current password"}), 401

    try:
        update_user_password(uid, new_pass)
        return jsonify({"ok": True, "msg": "Password updated successfully"})
    except Exception as e:
        app.logger.error(f"Change password error: {e}")
        return jsonify({"error": "Failed to update password."}), 500


@app.route("/api/auth/forgot-password", methods=["POST"])
def forgot_password():
    from db import get_user_by_email
    body = request.get_json(force=True)
    email = body.get("email", "").strip().lower()

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "No account found with this email"}), 404

    token = uuid.uuid4().hex
    RESET_TOKENS[token] = email

    recovery_url = f"/auth/reset-password?token={token}"

    return jsonify({
        "ok": True,
        "token": token,
        "recovery_url": recovery_url,
        "msg": "Password reset link generated successfully"
    })


@app.route("/api/auth/reset-password", methods=["POST"])
def reset_password():
    from db import get_user_by_email, update_user_password
    body = request.get_json(force=True)
    token = body.get("token", "").strip()
    new_pass = body.get("new_password", "")

    if not token or not new_pass:
        return jsonify({"error": "Token and new password are required"}), 400
    if len(new_pass) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    email = RESET_TOKENS.get(token)
    if not email:
        return jsonify({"error": "Invalid or expired password reset token"}), 400

    user = get_user_by_email(email)
    if not user:
        return jsonify({"error": "User not found"}), 404

    try:
        update_user_password(user["id"], new_pass)
        RESET_TOKENS.pop(token, None)
        return jsonify({"ok": True, "msg": "Password reset successfully. You can now sign in."})
    except Exception as e:
        app.logger.error(f"Reset password error: {e}")
        return jsonify({"error": "Failed to reset password."}), 500


@app.route("/api/progress", methods=["GET"])
@user_only
def get_progress():
    from db import get_user_progress
    uid = get_current_user_id()
    progress = get_user_progress(uid)
    return jsonify({"ok": True, "progress": progress})


@app.route("/api/progress", methods=["POST"])
@user_only
def save_progress():
    from db import save_user_progress
    uid = get_current_user_id()
    body = request.get_json(force=True)
    progress = body.get("progress")
    if not progress:
        return jsonify({"error": "Progress data is required"}), 400
    
    progress_json = json.dumps(progress)
    save_user_progress(uid, progress_json)
    return jsonify({"ok": True})


@app.route("/api/assessments", methods=["POST"])
@user_only
def submit_assessment():
    from db import save_assessment
    uid = get_current_user_id()
    body = request.get_json(force=True)
    test_type = body.get("type", "").strip().upper()
    answers = body.get("answers", [])
    
    if test_type not in ("PHQ9", "GAD7"):
        return jsonify({"error": "Invalid assessment type. Must be PHQ9 or GAD7."}), 400
        
    if not isinstance(answers, list) or not all(isinstance(x, int) and 0 <= x <= 3 for x in answers):
        return jsonify({"error": "Answers must be an array of integers between 0 and 3."}), 400
        
    if test_type == "PHQ9" and len(answers) != 9:
        return jsonify({"error": "PHQ-9 requires exactly 9 answers."}), 400
    if test_type == "GAD7" and len(answers) != 7:
        return jsonify({"error": "GAD-7 requires exactly 7 answers."}), 400
        
    score = sum(answers)
    
    if test_type == "PHQ9":
        if score <= 4:
            severity = "Minimal"
        elif score <= 9:
            severity = "Mild"
        elif score <= 14:
            severity = "Moderate"
        elif score <= 19:
            severity = "Moderately Severe"
        else:
            severity = "Severe"
    else: # GAD7
        if score <= 4:
            severity = "Minimal"
        elif score <= 9:
            severity = "Mild"
        elif score <= 14:
            severity = "Moderate"
        else:
            severity = "Severe"
            
    answers_json = json.dumps(answers)
    
    try:
        aid = save_assessment(uid, test_type, score, severity, answers_json)
        return jsonify({
            "ok": True,
            "assessment": {
                "id": aid,
                "type": test_type,
                "score": score,
                "severity": severity,
                "taken_at": datetime.now().isoformat()
            }
        })
    except Exception as e:
        app.logger.error(f"Error saving assessment: {e}")
        return jsonify({"error": "Failed to save assessment results."}), 500


@app.route("/api/assessments", methods=["GET"])
@user_only
def get_assessments_history():
    from db import get_user_assessments
    uid = get_current_user_id()
    try:
        history = get_user_assessments(uid)
        return jsonify({"ok": True, "assessments": history})
    except Exception as e:
        app.logger.error(f"Error fetching assessments: {e}")
        return jsonify({"error": "Failed to retrieve assessments history."}), 500


# ══════════════════════════════════════════════════════════════
#  PAGE ROUTES
# ══════════════════════════════════════════════════════════════

@app.route("/")
@login_required
def hub_home():
    if get_user_role() == "therapist":
        return send_from_directory(TEMPLATES_DIR, "therapist_dashboard.html")
    return render_template_string(HUB_TEMPLATE, games=get_available_games())


@app.route("/games")
@user_only
def list_games_redirect():
    return redirect("/games/")


@app.route("/games/")
@user_only
def list_games():
    hub = GAMES_DIR / "manokart_games_hub.html"
    if hub.exists():
        return send_from_directory(GAMES_DIR, "manokart_games_hub.html")
    return render_template_string(HUB_TEMPLATE, games=get_available_games())


@app.route("/games/<game_slug>")
@user_only
def serve_game(game_slug):
    if game_slug in ("gameEngine_test_dashboard",):
        return redirect("/games/")
    for ext in (".js", ".css"):
        asset = game_slug + ext if not game_slug.endswith(ext) else game_slug
        asset_path = GAMES_DIR / asset
        if asset_path.exists():
            return send_from_directory(GAMES_DIR, asset)
    filename = game_slug if game_slug.endswith(".html") else f"{game_slug}.html"
    path = GAMES_DIR / filename
    if path.exists():
        return send_from_directory(GAMES_DIR, filename)
    return jsonify({"error": f"Game '{game_slug}' not found"}), 404


@app.route("/chatbot")
@user_only
def chatbot_page():
    for name in ["chatbot.html", "index.html", "manokart_chatbot.html"]:
        f = CHATBOT_DIR / name
        if f.exists():
            return send_from_directory(CHATBOT_DIR, name)
    return render_template_string(CHATBOT_SHELL)


@app.route("/diary")
@user_only
def diary_page():
    return render_template_string(DIARY_SHELL)


@app.route("/music")
@user_only
def music_page():
    return send_from_directory(TEMPLATES_DIR, "music.html")


@app.route("/voice")
@user_only
def voice_page():
    return send_from_directory(TEMPLATES_DIR, "voice.html")


@app.route("/profile")
@user_only
def profile_page():
    return send_from_directory(TEMPLATES_DIR, "profile.html")


@app.route("/therapists")
@user_only
def therapists_page():
    return send_from_directory(TEMPLATES_DIR, "therapists.html")


@app.route("/clinical")
@user_only
def clinical_page():
    return send_from_directory(TEMPLATES_DIR, "clinical.html")


@app.route("/auth/reset-password")
def reset_password_page():
    return send_from_directory(ROOT, "manokart-auth.html")



@app.route("/static/<path:filename>")
def static_files(filename):
    for search_dir in [ROOT, DATA_DIR, CHATBOT_DIR, GAMES_DIR, BACKEND_DIR / "static"]:
        filepath = search_dir / filename
        if filepath.exists():
            mimetype = None
            if filename.endswith('.jsx') or filename.endswith('.js'):
                mimetype = 'application/javascript'
            return send_from_directory(search_dir, filename, mimetype=mimetype)
    return jsonify({"error": "File not found"}), 404


@app.route("/api/photos/<filename>")
def serve_photo(filename):
    return send_from_directory(UPLOADS_DIR, filename)


# ══════════════════════════════════════════════════════════════
#  CHATBOT API
# ══════════════════════════════════════════════════════════════

_chat_sessions: dict = {}

def _mood_number_to_name(mood):
    # 1=Joyful, 2=Happy, 3=Calm, 4=Sad, 5=Anxious
    names = {1: "Joyful", 2: "Happy", 3: "Calm", 4: "Sad", 5: "Anxious"}
    try:
        return names.get(int(mood), "Neutral")
    except Exception:
        return "Neutral"

def _mood_score_to_name(score):
    try:
        val = round(float(score))
        return _mood_number_to_name(val)
    except Exception:
        return "Neutral"

def _get_game_recommendation_by_mood(uid):
    # Fetch database helpers
    from db import get_diary_entries, get_analytics, get_user_assessments
    from datetime import datetime
    import sys
    sys.path.append(str(CHATBOT_DIR))
    from recommendation_models import format_recommendation_features

    # Default fallback game
    default_game = {"slug": "manokart_calm_grid_sudoku", "title": "Calm Grid Sudoku", "emoji": "🔢", "desc": "A soothing number puzzle designed to cultivate focus and clarity"}

    games_db = {
        "manokart_body_breath_quest": {"slug": "manokart_body_breath_quest", "title": "Body & Breath Quest", "emoji": "🧘", "desc": "Calm your racing thoughts with guided breathing patterns"},
        "manokart_cozy_island_garden": {"slug": "manokart_cozy_island_garden", "title": "Cozy Island Garden", "emoji": "🌴", "desc": "Take a gentle escape to grow flowers and nurture a virtual island"},
        "manokart_stress_relief_ocean": {"slug": "manokart_stress_relief_ocean", "title": "Stress Relief Ocean", "emoji": "🌊", "desc": "Synchronize your breathing with peaceful ocean waves"},
        "manokart_mood_blocks_tetris": {"slug": "manokart_mood_blocks_tetris", "title": "Mood Blocks Tetris", "emoji": "🟦", "desc": "Focus your mind and stack shapes to release built-up frustration"},
        "manokart_calm_grid_sudoku": {"slug": "manokart_calm_grid_sudoku", "title": "Calm Grid Sudoku", "emoji": "🔢", "desc": "A soothing number puzzle designed to cultivate focus and clarity"},
        "manokart_color_your_world": {"slug": "manokart_color_your_world", "title": "Color Your World", "emoji": "🎨", "desc": "Paint beautiful canvases to express and celebrate your positive mood"},
        "manokart_spirit_journey": {"slug": "manokart_spirit_journey", "title": "Spirit Journey", "emoji": "✨", "desc": "Embark on a peaceful journey to ground yourself in natural settings"}
    }

    try:
        # Load user context
        entries_map = get_diary_entries(uid)
        sorted_entries = sorted(entries_map.values(), key=lambda e: e.get("date", ""), reverse=True)
        
        # Current mood
        current_mood = 3.0
        latest_tags = []
        if sorted_entries:
            latest = sorted_entries[0]
            if latest.get("mood") is not None:
                current_mood = float(latest["mood"])
            latest_tags = latest.get("tags", [])

        # Average mood
        analytics_data = get_analytics(uid)
        avg_mood = analytics_data.get("avg_mood")
        if avg_mood is None:
            avg_mood = current_mood

        # Clinical scores
        assessments = get_user_assessments(uid)
        phq9_score = 0.0
        gad7_score = 0.0
        for ass in assessments:
            if ass.get("type") == "PHQ-9" and phq9_score == 0.0:
                phq9_score = float(ass.get("score", 0.0))
            elif ass.get("type") == "GAD-7" and gad7_score == 0.0:
                gad7_score = float(ass.get("score", 0.0))

        # Timing
        hour = float(datetime.now().hour)

        # Build feature vector
        feats = format_recommendation_features(current_mood, avg_mood, phq9_score, gad7_score, hour, latest_tags)

        # Query Random Forest
        rf_bundle, _ = load_recommendation_models()
        if rf_bundle is not None:
            model = rf_bundle["model"]
            pred_slug = model.predict([feats])[0]
            return games_db.get(pred_slug, default_game)
    except Exception as e:
        app.logger.warning(f"Random Forest recommendation failed: {e}")
        
    return default_game

@app.route("/api/chat", methods=["POST"])
@user_only
def chat():
    import random
    import re
    from datetime import datetime, date

    body       = request.get_json(force=True)
    user_msg   = body.get("message", "").strip()
    session_id = body.get("session_id", "default")
    uid        = get_current_user_id()

    if not user_msg:
        return jsonify({"reply": "I didn't catch that — could you say it again? 🌿"})

    # ── DB: try to persist chat, but don't crash if MySQL is down ──
    session_pk = None
    try:
        from db import get_or_create_chat_session, save_chat_message, get_chat_history
        session_pk = get_or_create_chat_session(uid, session_id)
        save_chat_message(session_pk, "user", user_msg)
        history = get_chat_history(session_pk, limit=10)
    except Exception as e:
        app.logger.warning(f"DB unavailable for chat history: {e}")
        history = []

    def _try_save_reply(reply_text):
        """Best-effort save of assistant reply to DB."""
        if session_pk is not None:
            try:
                from db import save_chat_message as _save
                _save(session_pk, "assistant", reply_text)
            except Exception:
                pass

    # ── Step 1: Crisis Override (Regex Safety Check) ──
    crisis_keywords = [
        r"\b(want|wish|going)\s+to\s+(die|kill\s+myself|end\s+(it|my\s+life|everything))\b",
        r"\b(suicid(e|al)|self.harm|self.hurt|cutting\s+myself|hurt\s+myself)\b",
        r"\b(no\s+reason\s+to\s+live|don.t\s+want\s+to\s+(live|be\s+alive|exist))\b",
        r"\b(better\s+off\s+dead|world\s+better\s+without\s+me)\b",
        r"\b(plan(ning)?\s+to\s+(kill|end|hurt))\b",
        r"\b(i\s+want\s+to\s+die|i\s+want\s+to\s+disappear|i\s+want\s+it\s+to\s+stop)\b",
    ]
    is_crisis = False
    for pat in crisis_keywords:
        if re.search(pat, user_msg.lower()):
            is_crisis = True
            break
    if is_crisis:
        reply = (
            "⚠️ *** IMPORTANT SAFETY NOTICE ***\n"
            "I'm very concerned about you right now. Please know that you are not alone and there is support available. "
            "Please reach out immediately to speak with a trained professional who can help:\n"
            "• iCALL (India): 9152987821\n"
            "• Vandrevala Foundation: 1860-2662-345 (24/7)\n"
            "• NIMHANS Helpline: 080-46110007\n"
            "• Emergency Services: 112\n\n"
            "Are you safe right now? Please consider contacting a trusted loved one or checking in with emergency services."
        )
        _try_save_reply(reply)
        return jsonify({"reply": reply, "source": "crisis_override", "tag": "suicidal", "crisis": True})

    # ── Step 2: Greeting Guard & Proactive Diary Check ──
    _GREETING_PATTERN = re.compile(
        r"^(hi+|hello+|hey+|hiya|howdy|what['\s]s\s*up|whats\s*up|yo|greetings|"
        r"good\s*(morning|evening|afternoon|night|day))(?:\s+there)?[\.\!]*$",
        re.IGNORECASE
    )
    _GREETING_REPLIES = [
        "Hello! 🌸 I'm really glad you're here. Whatever you're carrying right now, you don't have to carry it alone. How are you feeling today?",
        "Hi there! Welcome. This is a safe space for you. What's on your mind?",
        "Hey! I'm here and listening. How has your day been?",
        "Hello. This is a safe, non-judgmental space. What's going on for you today?",
    ]

    if _GREETING_PATTERN.match(user_msg):
        proactive_text = ""
        try:
            from db import get_diary_entries
            entries_map = get_diary_entries(uid)
            sorted_entries = sorted(entries_map.values(), key=lambda e: e.get("date", ""), reverse=True)
            if sorted_entries:
                latest = sorted_entries[0]
                entry_date_str = latest.get("date", "")
                entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d").date()
                days_diff = (date.today() - entry_date).days
                if days_diff <= 1:
                    mood_num = latest.get("mood")
                    mood_name = _mood_number_to_name(mood_num)
                    if mood_num in (4, 5):
                        tags = ", ".join([f"#{t}" for t in latest.get("tags", [])[:3]])
                        tags_str = f" tagged with {tags}" if tags else ""
                        time_word = "today" if days_diff == 0 else "yesterday"
                        proactive_text = f"\n\nI noticed you logged a diary entry {time_word} feeling **{mood_name}**{tags_str}. How are you doing right now? I'm here if you want to share or talk about it. 🌿"
        except Exception as e:
            app.logger.warning(f"Proactive check error: {e}")

        reply = random.choice(_GREETING_REPLIES) + proactive_text
        _try_save_reply(reply)
        return jsonify({"reply": reply, "source": "greeting_guard", "tag": "greeting"})

    # ── Step 3: "I'm fine" Positive State Guard ──
    _IM_FINE_PATTERN = re.compile(
        r"^(i am fine|i am okay|i am good|i am alright|i'm fine|i'm okay|"
        r"i'm good|i'm alright|i feel fine|i feel okay|i feel good|"
        r"i feel alright|doing fine|doing okay|doing well|feeling okay|"
        r"feeling fine|feeling good|feeling better|i am doing fine|"
        r"i am doing okay|i am doing good|all good|all okay|"
        r"not bad|i am not bad|pretty good|pretty okay)[\.\!]*$",
        re.IGNORECASE
    )
    _IM_FINE_REPLIES = [
        "Great to hear you're doing okay! 🌿 Is there anything on your mind you'd like to talk through, or just checking in?",
        "That's good! Sometimes just touching base with yourself is enough. Anything you'd like to share or explore today?",
        "Glad to hear it! 🌸 I'm here whenever you want to talk — what's on your mind?",
    ]

    if _IM_FINE_PATTERN.match(user_msg):
        reply = random.choice(_IM_FINE_REPLIES)
        _try_save_reply(reply)
        return jsonify({"reply": reply, "source": "im_fine_guard", "tag": "positive_state"})

    # ── Step 4: Negation Guard ──
    _NEGATION_EMOTION_PATTERN = re.compile(
        r"\b(not|no|never|isn['\s]t|aren['\s]t|wasn['\s]t|weren['\s]t|"
        r"don['\s]t|doesn['\s]t|didn['\s]t|cannot|can['\s]t|won['\s]t|"
        r"am not|i am not|i do not|do not|i feel not)\b"
        r"(?:\s+\w+){0,3}\s+"  # up to 3 words gap between negation and emotion
        r"\b(anxious|anxiety|nervous|worried|panic|scared|fearful|"
        r"sad|depressed|depression|hopeless|miserable|empty|worthless|"
        r"stressed|stress|overwhelmed|burned out|exhausted|drained|"
        r"angry|anger|rage|furious|mad|irritated|frustrated|"
        r"lonely|loneliness|isolated|alone|abandoned|"
        r"bad|terrible|awful|horrible|broken|lost|numb)\b",
        re.IGNORECASE
    )
    _NEGATION_REPLIES = [
        "That's really good to hear! 🌸 It's always nice when things feel a bit lighter. What's on your mind today?",
        "Glad you're feeling okay! Sometimes even just checking in with yourself matters. Is there anything you'd like to talk about?",
        "That's wonderful! 🌿 What's been going well for you lately, or is there something you'd like to explore?",
        "Great to hear that! Even on good days, it can help to reflect a little. How has your day been overall?",
    ]

    if _NEGATION_EMOTION_PATTERN.search(user_msg):
        reply = random.choice(_NEGATION_REPLIES)
        _try_save_reply(reply)
        return jsonify({"reply": reply, "source": "negation_guard", "tag": "negation_override"})

    # ── Step 4: Game & Activity Recommendations Request ──
    if re.search(r"\b(game|play|activity|activities|recommend\s+a\s+game|suggest\s+a\s+game|what\s+should\s+i\s+play|something\s+to\s+play)\b", user_msg.lower()):
        rec = _get_game_recommendation_by_mood(uid)
        reply = (
            f"I'd love to suggest an activity for you! Based on your state, you might enjoy playing **{rec['title']}** {rec['emoji']}.\n\n"
            f"*{rec['desc']}*.\n\n"
            f"It's a wonderful, mindful way to take a break and ground yourself. I've placed a quick link below to play it! 🌿"
        )
        _try_save_reply(reply)
        return jsonify({
            "reply": reply,
            "source": "game_recommendation",
            "tag": "coping_strategies",
            "recommendation": rec
        })

    # ── Step 5: Mood & Assessment History Lookup Request ──
    if re.search(r"\b(how\s+is\s+my\s+mood|mood\s+history|mood\s+logs?|average\s+mood|my\s+mood\s+lately|how\s+am\s+i\s+doing)\b", user_msg.lower()):
        try:
            from db import get_analytics, get_user_assessments
            analytics_data = get_analytics(uid)
            assessments = get_user_assessments(uid)
            
            avg_mood = analytics_data.get("avg_mood")
            total_entries = analytics_data.get("total_entries", 0)
            streak = analytics_data.get("streak", 0)
            
            reply = "Here is what I see from your recent wellness metrics: 📊\n\n"
            if total_entries > 0 and avg_mood:
                mood_name = _mood_score_to_name(avg_mood)
                reply += f"• **Mood logs**: You've written **{total_entries} diary entries** (streak: **{streak} days**). Your average logged mood is **{mood_name}** ({avg_mood:.1f}/5).\n"
            else:
                reply += "• **Mood logs**: You haven't logged any diary entries yet. Logging your daily thoughts helps track your emotions! 📖\n"
                
            if assessments:
                latest_ass = assessments[0]
                test_type = latest_ass.get("type", "Assessment")
                severity = latest_ass.get("severity", "Unknown")
                score = latest_ass.get("score", 0)
                reply += f"• **Assessments**: Your latest self-assessment was **{test_type}** with a score of **{score}** (**{severity}** severity).\n"
            else:
                reply += "• **Assessments**: You haven't taken any self-assessments (PHQ-9 / GAD-7) lately. You can find them on the clinical tab to check in on your levels.\n"
                
            reply += "\nHow are you feeling right now compared to these wellness trends?"
            _try_save_reply(reply)
            return jsonify({"reply": reply, "source": "mood_history_lookup"})
        except Exception as e:
            app.logger.warning(f"Mood lookup error: {e}")

    # ── Step 6: Diary Lookup Request ──
    if re.search(r"\b(diary|journal|latest\s+entry|what\s+did\s+i\s+write|my\s+last\s+entry|summarize\s+my\s+diary)\b", user_msg.lower()):
        try:
            from db import get_diary_entries
            entries_map = get_diary_entries(uid)
            sorted_entries = sorted(entries_map.values(), key=lambda e: e.get("date", ""), reverse=True)
            if sorted_entries:
                latest = sorted_entries[0]
                date_str = latest.get("date", "")
                text = latest.get("text", "")
                mood_num = latest.get("mood")
                mood_name = _mood_number_to_name(mood_num)
                tags = latest.get("tags", [])
                
                snippet = text[:180] + "..." if len(text) > 180 else text
                tags_str = ", ".join([f"#{t}" for t in tags]) if tags else "None"
                
                reply = (
                    f"Here is a summary of your latest diary entry from **{date_str}** where you felt **{mood_name}**:\n\n"
                    f"📖 *\"{snippet}\"*\n\n"
                    f"🏷️ **Tags**: {tags_str}\n\n"
                    f"Writing is a powerful way to process experiences. Would you like to share more about how you're feeling right now?"
                )
            else:
                reply = "It looks like you haven't written any diary entries yet. 📖 You can write one on the Diary tab!"
            _try_save_reply(reply)
            return jsonify({"reply": reply, "source": "diary_lookup"})
        except Exception as e:
            app.logger.warning(f"Diary lookup error: {e}")

    # ── Step 7: Fall back to ML model prediction ──
    bundle = load_ml_model()
    if bundle and isinstance(bundle, dict):
        try:
            model = bundle.get("ensemble") or bundle.get("pipeline")
            if model is not None:
                import numpy as np
                le            = bundle["label_encoder"]
                responses_map = bundle.get("responses_map", {})
                processed     = preprocess(user_msg)
                
                proba = model.predict_proba([processed])[0]
                idx   = int(np.argmax(proba))
                conf  = float(proba[idx])
                tag   = le.inverse_transform([idx])[0]
                
                # Check confidence threshold (safety lower threshold for crisis tags)
                threshold = 0.20 if tag in ("suicidal", "self_harm") else 0.45
                
                if conf < threshold:
                    reply = "I want to make sure I understand you properly. Could you share a little more about what you're feeling or going through? 🌿"
                else:
                    if tag in responses_map and responses_map[tag]:
                        reply = random.choice(responses_map[tag])
                    else:
                        reply = _ml_label_to_reply(tag, user_msg)
                        
                rec_game = None
                if tag in ("anxiety", "stressed", "sad", "depression", "loneliness", "anger"):
                    rec_game = _get_game_recommendation_by_mood(uid)
                    reply += f"\n\n{rec_game['emoji']} *Tip: Based on your state, you might enjoy playing [{rec_game['title']}](games/{rec_game['slug']}.html) to help ground yourself.*"
                
                # Check Escalation from intent history
                intent_history = session.get("chat_intent_history", [])
                intent_history.append(tag)
                session["chat_intent_history"] = intent_history[-5:]
                
                escalating = False
                history_set = set(intent_history + [tag])
                if {"anxiety", "depression", "suicidal"}.issubset(history_set) or {"stress", "depression", "suicidal"}.issubset(history_set):
                    escalating = True
                
                if escalating:
                    reply += "\n\n⚠️ *I want to check in — you've shared a lot of heavy thoughts today. Please remember Snehi (044-24640050) and iCALL (9152987821) are always available if things feel like too much.*"
                
                _try_save_reply(reply)
                
                resp_json = {"reply": reply, "source": "ml_model", "tag": tag, "confidence": round(conf, 4)}
                if rec_game:
                    resp_json["recommendation"] = rec_game
                return jsonify(resp_json)

            elif "model" in bundle and bundle.get("vectorizer"):
                vec   = bundle["vectorizer"].transform([user_msg])
                label = bundle["model"].predict(vec)[0]
                reply = _ml_label_to_reply(label, user_msg)
                _try_save_reply(reply)
                return jsonify({"reply": reply, "source": "ml_model"})

        except Exception as e:
            app.logger.warning(f"ML model inference error: {e}")

    # ── Fallback reply — chat always works ──
    reply = _ml_label_to_reply("neutral", user_msg)
    _try_save_reply(reply)
    return jsonify({"reply": reply, "source": "fallback"})


def _ml_label_to_reply(label: str, original_msg: str) -> str:
    label = str(label).lower()
    replies = {
        "happy":    "That's wonderful to hear! 🌸 It sounds like things are going well for you right now. Keep holding onto that feeling.",
        "sad":      "I'm really sorry you're feeling sad 🌧️ That's okay — feelings like this are valid. Would you like to talk about what's been on your mind?",
        "anxious":  "Anxiety can feel so overwhelming 🌿 Take a slow, deep breath with me. You're safe here. What's making you feel anxious?",
        "angry":    "It makes sense to feel angry sometimes 🍂 Your feelings are completely valid. Would it help to share what happened?",
        "neutral":  "Thank you for sharing with me 🌿 I'm here and I'm listening. How can I support you today?",
        "stressed": "Stress can be really heavy to carry 💙 You don't have to face it alone. What's weighing on you most right now?",
        "calm":     "I'm glad you're feeling calm 🌊 That peaceful feeling is something to cherish. Is there anything I can help you with today?",
    }
    return replies.get(label, "Thank you for sharing that with me 🌿 I hear you. Can you tell me a little more about how you're feeling?")


# ══════════════════════════════════════════════════════════════
#  VOICE JOURNAL API
# ══════════════════════════════════════════════════════════════

@app.route("/api/voice/analyze", methods=["POST"])
@user_only
def voice_analyze():
    """Analyze transcribed voice text for emotion using the ML model."""
    import random, numpy as np

    body       = request.get_json(force=True)
    text       = body.get("text", "").strip()
    speech_rate = body.get("speech_rate", 0)
    avg_volume  = body.get("avg_volume", 0)

    if not text:
        return jsonify({"emotion": "neutral", "confidence": 0, "response": "I didn't catch anything — try recording again 🎙️"})

    bundle = load_ml_model()
    if bundle and isinstance(bundle, dict):
        try:
            model = bundle.get("ensemble") or bundle.get("pipeline")
            if model is not None:
                le            = bundle["label_encoder"]
                responses_map = bundle.get("responses_map", {})
                processed     = _preprocess_fallback(text)
                proba = model.predict_proba([processed])[0]
                idx   = int(np.argmax(proba))
                conf  = float(proba[idx])
                tag   = le.inverse_transform([idx])[0]

                if tag in responses_map and responses_map[tag]:
                    response = random.choice(responses_map[tag])
                else:
                    response = _ml_label_to_reply(tag, text)

                # Audio heuristic adjustments
                audio_insight = ""
                if speech_rate > 160:
                    audio_insight = "Your speech was quite fast — you may be feeling rushed or energized."
                elif speech_rate > 0 and speech_rate < 80:
                    audio_insight = "Your speech was slow and measured — you might be feeling reflective or tired."
                if avg_volume and avg_volume < 0.04:
                    audio_insight += " Your voice was very soft."

                return jsonify({
                    "emotion":      tag,
                    "tag":          tag,
                    "confidence":   round(conf, 4),
                    "response":     response,
                    "audio_insight": audio_insight,
                    "source":       "ml_model"
                })
        except Exception as e:
            app.logger.warning(f"Voice emotion analysis error: {e}")

    return jsonify({
        "emotion":    "neutral",
        "tag":        "neutral",
        "confidence": 0.5,
        "response":   "Thank you for sharing your voice 🌿 I'm here and listening.",
        "source":     "fallback"
    })


# ══════════════════════════════════════════════════════════════
#  MUSIC RECOMMENDATION API
# ══════════════════════════════════════════════════════════════

@app.route("/api/music/recommend")
@user_only
def music_recommend():
    """Return playlist data for a given mood."""
    mood = request.args.get("mood", "calm").lower()
    playlists = {
        "anxious":  {"title": "Calming & Grounding",  "spotify_uri": "37i9dQZF1DX4sWSpwq3LiO", "hindi_spotify_uri": "37i9dQZF1DWSwxyU5zGZYe"},
        "sad":      {"title": "Gentle Comfort",       "spotify_uri": "37i9dQZF1DX7qK8ma5wgG1", "hindi_spotify_uri": "4m2fG85s2O4u46YVp8lK0m"},
        "stressed": {"title": "Stress Relief",        "spotify_uri": "37i9dQZF1DX1tuUkMEdloZ", "hindi_spotify_uri": "7AWh76kNnD02RzHFJ4JDyI"},
        "angry":    {"title": "Release & Channel",    "spotify_uri": "37i9dQZF1DX1s9knjP51Oa", "hindi_spotify_uri": "37i9dQZF1DWXLeA8Omikj7"},
        "calm":     {"title": "Sustain Your Peace",   "spotify_uri": "37i9dQZF1DX9uKNf5jGX6m", "hindi_spotify_uri": "37i9dQZF1DWY2284zR0PzP"},
        "happy":    {"title": "Keep the Joy Going",   "spotify_uri": "37i9dQZF1DXdPec7aLTmlC", "hindi_spotify_uri": "37i9dQZF1DX0XUfTFmNBRM"},
        "neutral":  {"title": "Discover Your Mood",   "spotify_uri": "37i9dQZF1DX4WYpdgoIcn6", "hindi_spotify_uri": "37i9dQZF1DWY2284zR0PzP"},
        "lonely":   {"title": "You're Not Alone",     "spotify_uri": "37i9dQZF1DX2pSTOxoPbx9", "hindi_spotify_uri": "37i9dQZF1DX621LhR06P9m"},
    }
    data = playlists.get(mood, playlists["calm"])
    return jsonify({"mood": mood, **data})


# ══════════════════════════════════════════════════════════════
#  DIARY API
# ══════════════════════════════════════════════════════════════


@app.route("/api/entries", methods=["GET"])
@user_only
def get_entries():
    from db import get_diary_entries
    uid = get_current_user_id()
    entries = get_diary_entries(uid)
    return jsonify({"entries": entries})


@app.route("/api/entries/<date_key>", methods=["GET"])
@user_only
def get_entry(date_key):
    from db import get_diary_entry
    uid   = get_current_user_id()
    entry = get_diary_entry(uid, date_key)
    return jsonify({"entry": entry})


@app.route("/api/entries/<date_key>", methods=["POST", "PUT"])
@user_only
def save_entry(date_key):
    from db import save_diary_entry, get_diary_entry
    uid      = get_current_user_id()
    body     = request.get_json(force=True)
    existing = get_diary_entry(uid, date_key) or {}
    entry = save_diary_entry(
        uid      = uid,
        date_key = date_key,
        text     = body.get("text",   existing.get("text", "")),
        mood     = body.get("mood",   existing.get("mood")),
        tags     = body.get("tags",   existing.get("tags", [])),
        photos   = body.get("photos", existing.get("photos", [])),
    )
    return jsonify({"entry": entry, "status": "saved"})


@app.route("/api/entries/<date_key>", methods=["DELETE"])
@user_only
def delete_entry(date_key):
    from db import delete_diary_entry
    uid = get_current_user_id()
    delete_diary_entry(uid, date_key)
    return jsonify({"status": "deleted"})


@app.route("/api/upload", methods=["POST"])
@user_only
def upload_photo():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file.filename or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file"}), 400
    ext      = file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid.uuid4().hex}.{ext}"
    file.save(UPLOADS_DIR / filename)
    return jsonify({"url": f"/api/photos/{filename}", "filename": filename})


@app.route("/api/analyze", methods=["POST"])
@user_only
def analyze_diary():
    from db import get_analytics, get_user_assessments, get_diary_entries
    import torch
    import sys
    sys.path.append(str(CHATBOT_DIR))
    from recommendation_models import normalize_mood_sequence
    
    uid = get_current_user_id()
    
    try:
        analytics_data = get_analytics(uid)
        entries_map = get_diary_entries(uid)
        assessments = get_user_assessments(uid)
        
        total_entries = analytics_data.get("total_entries", 0)
        avg_mood = analytics_data.get("avg_mood")
        tag_freq = analytics_data.get("tag_freq", {})
        
        if total_entries == 0:
            return jsonify({"insight": (
                "You haven't written any diary entries yet. 📖 "
                "Reflection begins with your first words. "
                "Write down how your day went, even in just a few words, and I will be here to reflect with you. 🌿"
            )})
            
        # Get sorted moods for LSTM forecast
        sorted_entries = sorted(entries_map.values(), key=lambda e: e.get("date", ""), reverse=False)
        moods = [float(e.get("mood")) for e in sorted_entries if e.get("mood") is not None]
        
        # Determine forecast using LSTM
        forecast_direction = "stable"
        if len(moods) >= 3:
            try:
                _, lstm_model = load_recommendation_models()
                if lstm_model is not None:
                    norm_seq = normalize_mood_sequence(moods, target_len=5)
                    x_tensor = torch.tensor([norm_seq], dtype=torch.float32).unsqueeze(-1)
                    with torch.no_grad():
                        pred_score_norm = lstm_model(x_tensor).item()
                        pred_score = round(((pred_score_norm + 1.0) / 2.0) * 4.0 + 1.0, 2)
                        
                        last_mood = moods[-1]
                        if pred_score > last_mood + 0.3:
                            forecast_direction = "improving"
                        elif pred_score < last_mood - 0.3:
                            forecast_direction = "dipping"
            except Exception as e:
                app.logger.warning(f"Error running LSTM for reflection: {e}")

        # Determine dominant mood category (1=excited, 2=happy, 3=calm, 4=sad, 5=anxious)
        mood_str = "neutral"
        if avg_mood:
            if avg_mood < 1.8:
                mood_str = "excited/joyful"
            elif avg_mood < 2.5:
                mood_str = "happy"
            elif avg_mood < 3.5:
                mood_str = "calm"
            elif avg_mood < 4.3:
                mood_str = "sad/heavy"
            else:
                mood_str = "anxious/stressed"
                
        # Analyze tags
        top_tags = sorted(tag_freq.items(), key=lambda x: x[1], reverse=True)
        tag_mention = ""
        if top_tags:
            tag_mention = f" I notice that you have been focusing a lot on tags like #{top_tags[0][0]}"
            if len(top_tags) > 1:
                tag_mention += f" and #{top_tags[1][0]}"
            tag_mention += "."

        # Check assessments
        assessment_mention = ""
        if assessments:
            latest = assessments[0]
            severity = latest.get("severity", "").lower()
            if "severe" in severity or "moderate" in severity:
                assessment_mention = " I know things have felt clinically heavy for you lately, and you are carrying a lot."
                
        # Determine suggestion based on state
        if mood_str in ("anxious/stressed", "sad/heavy"):
            suggestion = "When feelings get heavy, try a slow, calming activity like the Guided Breathing Quest or Calm Grid Sudoku to anchor yourself."
        elif mood_str == "excited/joyful":
            suggestion = "To celebrate your high energy, you might enjoy sketching in Color Your World or exploring Cozy Island Garden."
        else:
            suggestion = "Keep practicing mindfulness. Today might be a good day to check in on Cozy Island Garden for some quiet reflection."

        # Compile final reflections
        if mood_str == "anxious/stressed":
            reflection = (
                f"Looking over your last {total_entries} entries, I can feel how much stress and anxiety you've been navigating lately.{tag_mention}"
                f"{assessment_mention} It takes real courage to put these feelings onto paper. "
                f"Your forecasting suggests you're currently in a challenging period, but remember that mood states are like weather — they shift. "
                f"{suggestion} Take it one gentle breath at a time. 🌿"
            )
        elif mood_str == "sad/heavy":
            reflection = (
                f"Reading your diary pages, it feels like things have been a bit gray or heavy recently.{tag_mention}"
                f"{assessment_mention} Thank you for showing up for yourself and writing through these low moments. "
                f"Even when the forecast feels cloudy, taking time to log your thoughts is a beautiful act of self-care. "
                f"{suggestion} Be extra kind to yourself today. 🌸"
            )
        elif mood_str == "excited/joyful":
            reflection = (
                f"Your diary entries are glowing with wonderful, positive energy!{tag_mention} "
                f"It is so beautiful to see you celebrating these bright, joyful moments. "
                f"Writing down these highlights creates a beautiful registry of happy times to look back on when days are harder. "
                f"{suggestion} Keep sharing this brightness! 🌞"
            )
        else:  # Happy or Calm
            trend_text = "stable and grounded"
            if forecast_direction == "improving":
                trend_text = "on a gentle, positive upward path"
            
            reflection = (
                f"Your recent diary entries show a wonderful sense of balance.{tag_mention} "
                f"Your emotional trend looks {trend_text}, which is a direct reflection of the mindfulness you are practicing. "
                f"Keeping a consistent log is a wonderful way to maintain this balance. "
                f"{suggestion} I'm glad to be walking this journey with you. 🌿"
            )

        return jsonify({"insight": reflection})
        
    except Exception as e:
        app.logger.error(f"Error in offline analyze: {e}")
        return jsonify({"insight": (
            "I analyzed your entries and noticed a steady, mindful progression. "
            "Writing is a powerful way to look back and understand your patterns. "
            "Keep dedicating this time to yourself; every entry is a step forward. 🌿"
        )})


@app.route("/api/analytics", methods=["GET"])
@user_only
def analytics():
    from db import get_analytics
    uid  = get_current_user_id()
    data = get_analytics(uid)
    return jsonify(data)


@app.route("/api/mood/forecast", methods=["GET"])
@user_only
def mood_forecast():
    import torch
    import sys
    sys.path.append(str(CHATBOT_DIR))
    from recommendation_models import normalize_mood_sequence, denormalize_mood
    from db import get_diary_entries
    
    uid = get_current_user_id()
    try:
        entries_map = get_diary_entries(uid)
        sorted_entries = sorted(entries_map.values(), key=lambda e: e.get("date", ""))
        moods = []
        for e in sorted_entries:
            m = e.get("mood")
            if m is not None:
                moods.append(float(m))
                
        if not moods:
            return jsonify({"mood_score": 3.0, "mood_name": "Calm", "emoji": "🙂"})
            
        if len(moods) < 3:
            avg = sum(moods) / len(moods)
            pred_score = round(avg, 2)
        else:
            _, lstm_model = load_recommendation_models()
            if lstm_model is not None:
                norm_seq = normalize_mood_sequence(moods, target_len=5)
                x_tensor = torch.tensor([norm_seq], dtype=torch.float32).unsqueeze(-1)
                with torch.no_grad():
                    pred_norm = lstm_model(x_tensor).item()
                pred_score = round(denormalize_mood(pred_norm), 2)
            else:
                avg = sum(moods) / len(moods)
                pred_score = round(avg, 2)
                
        rounded = int(round(pred_score))
        rounded = max(1, min(5, rounded))
        
        labels_map = {
            1: {"name": "Excited", "emoji": "🌟"},
            2: {"name": "Happy", "emoji": "😊"},
            3: {"name": "Calm", "emoji": "🙂"},
            4: {"name": "Sad", "emoji": "😔"},
            5: {"name": "Anxious", "emoji": "😐"}
        }
        res = labels_map.get(rounded, {"name": "Calm", "emoji": "🙂"})
        return jsonify({
            "mood_score": pred_score,
            "mood_name": res["name"],
            "emoji": res["emoji"]
        })
    except Exception as ex:
        app.logger.warning(f"Error in mood forecast API: {ex}")
        return jsonify({"mood_score": 3.0, "mood_name": "Calm", "emoji": "🙂"})

# ── PDF export ────────────────────────────────────────────────
MOOD_LABELS = {5: "Joyful", 4: "Happy", 3: "Calm", 2: "Sad", 1: "Anxious"}

@app.route("/api/export/pdf", methods=["GET"])
@user_only
def export_pdf():
    from db import get_diary_entries
    uid         = get_current_user_id()
    entries_map = get_diary_entries(uid)
    entries     = sorted(entries_map.values(), key=lambda e: e.get("date", ""))

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2.5*cm, rightMargin=2.5*cm,
        topMargin=2.5*cm,  bottomMargin=2.5*cm
    )
    styles = getSampleStyleSheet()

    def style(name, **kw):
        return ParagraphStyle(name, parent=styles["Normal"], **kw)

    title_s = style("t", fontName="Helvetica-Bold", fontSize=24,
                    textColor=colors.HexColor("#0F6E56"), spaceAfter=4, alignment=TA_CENTER)
    sub_s   = style("s", fontName="Helvetica-Oblique", fontSize=11,
                    textColor=colors.HexColor("#5DCAA5"), spaceAfter=20, alignment=TA_CENTER)
    date_s  = style("d", fontName="Helvetica-Bold", fontSize=14,
                    textColor=colors.HexColor("#0F6E56"), spaceBefore=14, spaceAfter=4)
    mood_s  = style("m", fontName="Helvetica-Oblique", fontSize=11,
                    textColor=colors.HexColor("#5F5E5A"), spaceAfter=8)
    body_s  = style("b", fontName="Helvetica", fontSize=11,
                    textColor=colors.HexColor("#2C2C2A"), leading=17, spaceAfter=6)
    tag_s   = style("g", fontName="Helvetica-Oblique", fontSize=10,
                    textColor=colors.HexColor("#888780"), spaceAfter=12)

    story = [
        Paragraph("ManoKart — My Diary", title_s),
        Paragraph("A record of your inner journey", sub_s),
        HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#9FE1CB"), spaceAfter=20),
    ]

    for entry in (entries or [Paragraph("No entries yet. Start writing! 🌱", body_s)]):
        if not isinstance(entry, dict):
            story.append(entry)
            continue

        d_str = entry.get("date", "")
        try:
            friendly = datetime.strptime(d_str, "%Y-%m-%d").strftime("%A, %B %d %Y")
        except Exception:
            friendly = d_str

        story.append(Paragraph(friendly, date_s))
        mood_v = entry.get("mood")
        if mood_v is not None:
            story.append(Paragraph(f"Mood: {MOOD_LABELS.get(mood_v, str(mood_v))}", mood_s))
        for para in (entry.get("text") or "").split("\n"):
            if para.strip():
                story.append(Paragraph(para.strip(), body_s))
        tags = entry.get("tags", [])
        if tags:
            story.append(Paragraph("Tags: " + "  •  ".join(f"#{t}" for t in tags), tag_s))

        photo_paths = []
        for photo_url in (entry.get("photos") or [])[:3]:
            fname = photo_url.split("/")[-1]
            fpath = UPLOADS_DIR / fname
            if fpath.exists():
                photo_paths.append(str(fpath))

        if photo_paths:
            cell_w = 5 * cm
            row    = []
            for pp in photo_paths:
                try:
                    row.append(RLImage(pp, width=cell_w, height=cell_w))
                except Exception:
                    row.append("")
            while len(row) < 3:
                row.append("")
            tbl = Table([row], colWidths=[cell_w + 0.3*cm] * 3)
            tbl.setStyle(TableStyle([
                ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
                ("ALIGN",         (0,0), (-1,-1), "CENTER"),
                ("LEFTPADDING",   (0,0), (-1,-1), 4),
                ("RIGHTPADDING",  (0,0), (-1,-1), 4),
                ("TOPPADDING",    (0,0), (-1,-1), 4),
                ("BOTTOMPADDING", (0,0), (-1,-1), 4),
            ]))
            story.append(tbl)
            story.append(Spacer(1, 8))

        story.append(HRFlowable(width="100%", thickness=0.3,
                                color=colors.HexColor("#E1F5EE"), spaceAfter=8))

    doc.build(story)
    buf.seek(0)
    filename = f"manokart_diary_{date.today().isoformat()}.pdf"
    return send_file(buf, mimetype="application/pdf",
                     as_attachment=True, download_name=filename)


@app.route("/api/therapists", methods=["GET"])
@user_only
def get_therapists_api():
    from db import get_therapists
    search = request.args.get("search", "").strip() or None
    specialization = request.args.get("specialization", "").strip() or None
    results = get_therapists(search, specialization)
    return jsonify({"ok": True, "therapists": results})


@app.route("/api/appointments", methods=["POST"])
@user_only
def create_appointment_api():
    from db import create_appointment
    uid = get_current_user_id()
    body = request.get_json(force=True)
    therapist_id = body.get("therapist_id")
    date_str = body.get("date", "").strip()
    time_str = body.get("time", "").strip()
    notes = body.get("notes", "").strip()

    if not therapist_id or not date_str or not time_str:
        return jsonify({"error": "Therapist ID, date, and time slot are required."}), 400

    create_appointment(uid, int(therapist_id), date_str, time_str, notes)
    return jsonify({"ok": True, "msg": "Appointment request submitted successfully."})


@app.route("/api/appointments", methods=["GET"])
@user_only
def get_appointments_api():
    from db import get_user_appointments
    uid = get_current_user_id()
    results = get_user_appointments(uid)
    return jsonify({"ok": True, "appointments": results})


@app.route("/api/appointments/received", methods=["GET"])
@login_required
def get_received_appointments_api():
    from db import get_received_appointments
    uid = get_current_user_id()
    results = get_received_appointments(uid)
    return jsonify({"ok": True, "appointments": results})


@app.route("/api/appointments/<int:app_id>/status", methods=["POST"])
@login_required
def update_appointment_status_api(app_id):
    from db import update_appointment_status
    uid = get_current_user_id()
    body = request.get_json(force=True)
    status = body.get("status", "").strip()
    
    if status not in ("Confirmed", "Cancelled"):
        return jsonify({"error": "Invalid status option."}), 400
        
    res = update_appointment_status(app_id, uid, status)
    if not res:
        return jsonify({"error": "Failed to update appointment status."}), 500
        
    return jsonify({"ok": True, "msg": f"Appointment request has been {status.lower()}."})


@app.route("/api/health")
def health():
    bundle = load_ml_model()
    return jsonify({
        "status":        "ok",
        "ml_model":      "loaded" if bundle else "not found",
        "diary_entries": len(load_diary()["entries"]),
        "games":         len(get_available_games()),
        "anthropic_key": "set" if ANTHROPIC_API_KEY else "missing (not required)",
    })


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
if __name__ == "__main__":
    print("\n" + "═" * 52)
    print("  🌿 ManoKart Server")
    print("═" * 52)
    print(f"  Hub:      http://localhost:5000/")
    print(f"  Auth:     http://localhost:5000/auth")
    print(f"  Diary:    http://localhost:5000/diary")
    print(f"  Chatbot:  http://localhost:5000/chatbot")
    print(f"  Music:    http://localhost:5000/music")
    print(f"  Voice:    http://localhost:5000/voice")
    print(f"  Games:    http://localhost:5000/games")
    print(f"  Health:   http://localhost:5000/api/health")
    print(f"  Root dir:     {ROOT}")
    print(f"  Games dir:    {GAMES_DIR}")
    print(f"  Chatbot dir:  {CHATBOT_DIR}")
    print(f"  Data dir:     {DATA_DIR}")
    print(f"  DiaryApp.jsx: {'✅ found' if DIARY_JSX.exists() else '⚠️  not found at '+str(DIARY_JSX)}")
    hub_screen = GAMES_DIR / 'manokart_games_hub.html'
    print(f"  Games hub:    {'✅ found' if hub_screen.exists() else '⚠️  not found at '+str(hub_screen)}")
    games = get_available_games()
    print(f"\n  {len(games)} game(s) found: {[g['slug'] for g in games] or 'none yet'}")
    print("═" * 52 + "\n")
    app.run(debug=True, port=5000, host="0.0.0.0")