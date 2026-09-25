"""
╔══════════════════════════════════════════════════════╗
║           ManoRakshak — Unified Flask Server            ║
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
║    /games              → games/manorakshak_games_hub    ║
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
    send_file, send_from_directory, render_template_string, render_template
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

sys.path.append(str(ROOT))
sys.path.append(str(CHATBOT_DIR))

for d in [DATA_DIR, UPLOADS_DIR, GAMES_DIR, ML_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# ──────────────────────────────────────────────────────────────
#  FLASK APP
# ──────────────────────────────────────────────────────────────
app = Flask(__name__, static_folder=None)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.secret_key = os.environ.get("FLASK_SECRET", "manorakshak-dev-secret-change-in-prod")

ALLOWED_IMG       = {"png", "jpg", "jpeg", "gif", "webp"}

# ──────────────────────────────────────────────────────────────
#  CORS
# ──────────────────────────────────────────────────────────────
@app.after_request
def add_cors(response):
    response.headers["Access-Control-Allow-Origin"]  = "*"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type,Authorization"
    response.headers["Access-Control-Allow-Methods"] = "GET,POST,PUT,DELETE,OPTIONS"
    
    # Disable cache for dynamic pages to prevent back-button viewing authenticated pages after logout
    if request.endpoint and not request.endpoint.startswith("static"):
        response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
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
    nltk_data_dir = str(DATA_DIR / "nltk_data")
    os.makedirs(nltk_data_dir, exist_ok=True)
    nltk.data.path.append(nltk_data_dir)
    for pkg in ["wordnet", "omw-1.4", "stopwords"]:
        nltk.download(pkg, download_dir=nltk_data_dir, quiet=True)
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
        CHATBOT_DIR / "manorakshak_model.pkl",
        ML_DIR      / "manorakshak_model.pkl",
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
    "manorakshak_body_breath_quest":   {"title": "Body & Breath Quest",  "emoji": "🧘", "desc": "Calm your nervous system with guided breathing"},
    "manorakshak_calm_grid_sudoku":    {"title": "Calm Grid Sudoku",     "emoji": "🔢", "desc": "A soothing number puzzle for a focused mind"},
    "manorakshak_color_your_world":    {"title": "Color Your World",     "emoji": "🎨", "desc": "Express your mood through colour"},
    "manorakshak_cozy_island_garden":  {"title": "Cozy Island Garden",   "emoji": "🌴", "desc": "Escape to a gentle island adventure"},
    "manorakshak_mood_blocks_tetris":  {"title": "Mood Blocks Tetris",   "emoji": "🟦", "desc": "Stack blocks and release tension"},
    "manorakshak_spirit_journey":      {"title": "Spirit Journey",       "emoji": "✨", "desc": "A mindful journey through nature"},
    "manorakshak_stress_relief_ocean": {"title": "Stress Relief Ocean",  "emoji": "🌊", "desc": "Breathe with the waves"},
}

def get_available_games() -> list:
    games = []
    for stem, meta in GAME_META.items():
        path = GAMES_DIR / f"{stem}.html"
        if path.exists():
            games.append({"slug": stem, "path": str(path), **meta})
    for path in sorted(GAMES_DIR.glob("manorakshak_*.html")):
        stem = path.stem
        if stem not in GAME_META and stem not in ("manorakshak_hub_home_screen", "manorakshak_games_hub"):
            games.append({
                "slug":  stem,
                "title": stem.replace("manorakshak_", "").replace("_", " ").title(),
                "emoji": "🎮",
                "desc":  "A ManoRakshak activity",
                "path":  str(path),
            })
    return games


# ══════════════════════════════════════════════════════════════
#  TEMPLATES
# ══════════════════════════════════════════════════════════════


def load_template_file(filename: str) -> str:
    path = TEMPLATES_DIR / filename
    if path.exists():
        return path.read_text(encoding="utf-8")
    return ""

HUB_TEMPLATE = load_template_file("hub.html")
DIARY_SHELL = load_template_file("diary.html")
CHATBOT_SHELL = load_template_file("chatbot.html")


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
    return send_from_directory(ROOT, "auth.html")


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
        response = jsonify({"ok": True, "user": {"id": user["id"], "name": session["user_name"], "role": user.get("role", "user")}})
        response.set_cookie("manorakshak_user_id", str(user["id"]), max_age=30*24*60*60, httponly=False, samesite="Lax")
        return response
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

    try:
        user = check_login(email, password)
    except Exception as db_err:
        print(f"[DB Error] Login failed due to database connection issue: {db_err}")
        return jsonify({"error": "Database error. Please make sure MySQL is running in XAMPP Control Panel."}), 500

    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    session["user_id"]   = user["id"]
    session["user_name"] = user["full_name"] or user["username"]
    session["role"]      = user.get("role", "user")
    response = jsonify({"ok": True, "user": {"id": user["id"], "name": session["user_name"], "role": user.get("role", "user")}})
    response.set_cookie("manorakshak_user_id", str(user["id"]), max_age=30*24*60*60, httponly=False, samesite="Lax")
    return response


@app.route("/api/auth/logout", methods=["POST"])
def logout():
    session.clear()
    response = jsonify({"ok": True})
    response.delete_cookie("manorakshak_user_id")
    return response


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
            
    response = jsonify({
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
    response.set_cookie("manorakshak_user_id", str(user["id"]), max_age=30*24*60*60, httponly=False, samesite="Lax")
    return response


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
    role = get_user_role()
    if role == "therapist":
        return send_from_directory(TEMPLATES_DIR, "therapist_dashboard.html")
    return render_template_string(HUB_TEMPLATE, games=get_available_games())


@app.route("/victim/dashboard")
@login_required
def victim_dashboard_page():
    from db import get_victim_profile, create_victim_profile
    role = get_user_role()
    uid = get_current_user_id()
    if role != "user":
        return redirect("/")
    profile = get_victim_profile(uid)
    if not profile:
        auto_case_num = f"MK-2026-{uid:04d}"
        profile = create_victim_profile(uid, auto_case_num, "General Protection & Atrocity Relief", "Investigation")
    return send_from_directory(TEMPLATES_DIR, "victim_dashboard.html")


@app.route("/games")
@user_only
def list_games_redirect():
    return redirect("/games/")


@app.route("/games/")
@user_only
def list_games():
    hub = GAMES_DIR / "manorakshak_games_hub.html"
    if hub.exists():
        return send_from_directory(GAMES_DIR, "manorakshak_games_hub.html")
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
    for name in ["chatbot.html", "index.html", "manorakshak_chatbot.html"]:
        f = CHATBOT_DIR / name
        if f.exists():
            return send_from_directory(CHATBOT_DIR, name)
    return render_template_string(CHATBOT_SHELL)


@app.route("/diary")
@user_only
def diary_page():
    return render_template_string(DIARY_SHELL)


@app.route("/diary/app.js")
@user_only
def diary_app_js():
    return send_file(ROOT / "DiaryApp.js", mimetype="application/javascript")


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
    return send_from_directory(ROOT, "auth.html")



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
    from recommendation_models import format_recommendation_features

    # Default fallback game
    default_game = {"slug": "manorakshak_calm_grid_sudoku", "title": "Calm Grid Sudoku", "emoji": "🔢", "desc": "A soothing number puzzle designed to cultivate focus and clarity"}

    games_db = {
        "manorakshak_body_breath_quest": {"slug": "manorakshak_body_breath_quest", "title": "Body & Breath Quest", "emoji": "🧘", "desc": "Calm your racing thoughts with guided breathing patterns"},
        "manorakshak_cozy_island_garden": {"slug": "manorakshak_cozy_island_garden", "title": "Cozy Island Garden", "emoji": "🌴", "desc": "Take a gentle escape to grow flowers and nurture a virtual island"},
        "manorakshak_stress_relief_ocean": {"slug": "manorakshak_stress_relief_ocean", "title": "Stress Relief Ocean", "emoji": "🌊", "desc": "Synchronize your breathing with peaceful ocean waves"},
        "manorakshak_mood_blocks_tetris": {"slug": "manorakshak_mood_blocks_tetris", "title": "Mood Blocks Tetris", "emoji": "🟦", "desc": "Focus your mind and stack shapes to release built-up frustration"},
        "manorakshak_calm_grid_sudoku": {"slug": "manorakshak_calm_grid_sudoku", "title": "Calm Grid Sudoku", "emoji": "🔢", "desc": "A soothing number puzzle designed to cultivate focus and clarity"},
        "manorakshak_color_your_world": {"slug": "manorakshak_color_your_world", "title": "Color Your World", "emoji": "🎨", "desc": "Paint beautiful canvases to express and celebrate your positive mood"},
        "manorakshak_spirit_journey": {"slug": "manorakshak_spirit_journey", "title": "Spirit Journey", "emoji": "✨", "desc": "Embark on a peaceful journey to ground yourself in natural settings"}
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

def _process_chat_message(user_msg, uid, session_id="default"):
    import random
    import re
    from datetime import datetime, date

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
        return {"reply": reply, "source": "crisis_override", "tag": "suicidal", "crisis": True}, 200

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
        return {"reply": reply, "source": "greeting_guard", "tag": "greeting"}, 200

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
        return {"reply": reply, "source": "im_fine_guard", "tag": "positive_state"}, 200

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
        return {"reply": reply, "source": "negation_guard", "tag": "negation_override"}, 200

    # ── Step 4: Game & Activity Recommendations Request ──
    if re.search(r"\b(game|play|activity|activities|recommend\s+a\s+game|suggest\s+a\s+game|what\s+should\s+i\s+play|something\s+to\s+play)\b", user_msg.lower()):
        rec = _get_game_recommendation_by_mood(uid)
        reply = (
            f"I'd love to suggest an activity for you! Based on your state, you might enjoy playing **{rec['title']}** {rec['emoji']}.\n\n"
            f"*{rec['desc']}*.\n\n"
            f"It's a wonderful, mindful way to take a break and ground yourself. I've placed a quick link below to play it! 🌿"
        )
        _try_save_reply(reply)
        return {
            "reply": reply,
            "source": "game_recommendation",
            "tag": "coping_strategies",
            "recommendation": rec
        }, 200

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
            return {"reply": reply, "source": "mood_history_lookup"}, 200
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
            return {"reply": reply, "source": "diary_lookup"}, 200
        except Exception as e:
            app.logger.warning(f"Diary lookup error: {e}")

    # ── Step 6.5: Offline RAG + LLM (Llama 3.2 1B via Ollama) ──
    try:
        from backend.offline_llm_engine import generate_offline_counselor_response, is_ollama_running
        if is_ollama_running():
            res_dict = generate_offline_counselor_response(user_msg)
            if res_dict and res_dict.get("response"):
                reply = res_dict["response"]
                _try_save_reply(reply)
                return {
                    "reply": reply,
                    "source": "offline_rag_llm",
                    "model": res_dict.get("model", "llama3.2:1b"),
                    "rag_used": res_dict.get("context_used", False)
                }, 200
    except Exception as e:
        app.logger.warning(f"Offline RAG LLM error, falling back to ML: {e}")

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
                threshold = 0.20 if tag in ("suicidal", "self_harm") else 0.35
                
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
                return resp_json, 200

            elif "model" in bundle and bundle.get("vectorizer"):
                vec   = bundle["vectorizer"].transform([user_msg])
                label = bundle["model"].predict(vec)[0]
                reply = _ml_label_to_reply(label, user_msg)
                _try_save_reply(reply)
                return {"reply": reply, "source": "ml_model"}, 200

        except Exception as e:
            app.logger.warning(f"ML model inference error: {e}")

    # ── Fallback reply ──
    reply = _ml_label_to_reply("neutral", user_msg)
    _try_save_reply(reply)
    return {"reply": reply, "source": "fallback"}, 200


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


@app.route("/api/chat", methods=["POST"])
@user_only
def chat():
    body       = request.get_json(force=True)
    user_msg   = body.get("message", "").strip()
    session_id = body.get("session_id", "default")
    uid        = get_current_user_id()

    if not user_msg:
        return jsonify({"reply": "I didn't catch that — could you say it again? 🌿"})

    resp_data, status_code = _process_chat_message(user_msg, uid, session_id)
    return jsonify(resp_data), status_code


# ──────────────────────────────────────────────────────────────
#  VOICE CLONING & OFFLINE TTS/STT ENDPOINTS
# ──────────────────────────────────────────────────────────────
import voice_engine

UPLOAD_DIR = ROOT / "static" / "uploads"
AUDIO_OUT_DIR = ROOT / "static" / "audio_out"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_OUT_DIR.mkdir(parents=True, exist_ok=True)

@app.route("/api/enroll-voice", methods=["POST"])
@user_only
def enroll_voice():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided."}), 400

    consent = request.form.get("consent_confirmed", "false").lower() == "true"
    if not consent:
        return jsonify({
            "error": "Consent confirmation is required before a voice can be enrolled."
        }), 400

    display_name = request.form.get("display_name", "Loved one").strip()
    relationship = request.form.get("relationship", "").strip()

    tmp_path = UPLOAD_DIR / f"enroll_{uuid.uuid4().hex}.wav"
    request.files["audio"].save(tmp_path)

    try:
        result = voice_engine.enroll_voice(
            user_id=str(get_current_user_id()),
            display_name=display_name,
            audio_path=str(tmp_path),
            consent_confirmed=True,
            relationship=relationship,
        )
    finally:
        if tmp_path.exists():
            tmp_path.unlink()

    return jsonify(result)

@app.route("/api/voices", methods=["GET"])
@user_only
def list_voices():
    return jsonify(voice_engine.list_voices(str(get_current_user_id())))

@app.route("/api/voices/<voice_id>", methods=["DELETE"])
@user_only
def delete_voice(voice_id):
    voice_engine.delete_voice(str(get_current_user_id()), voice_id)
    return jsonify({"deleted": voice_id})

@app.route("/api/voice-chat", methods=["POST"])
@user_only
def voice_chat():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided."}), 400

    voice_id = request.form.get("voice_id") or None
    uid = get_current_user_id()
    session_id = request.form.get("session_id") or "default"

    in_path = UPLOAD_DIR / f"in_{uuid.uuid4().hex}.wav"
    request.files["audio"].save(in_path)

    try:
        user_text = voice_engine.transcribe(str(in_path))
    finally:
        if in_path.exists():
            in_path.unlink()

    if not user_text:
        return jsonify({"error": "Could not understand the audio. Please try again."}), 200

    # Process chatbot reply with full logic
    resp_data, _ = _process_chat_message(user_text, uid, session_id)
    reply_text = resp_data.get("reply", "")
    tag = resp_data.get("tag", "neutral")
    conf = resp_data.get("confidence", 1.0)
    is_crisis = resp_data.get("crisis", False)

    out_name = f"reply_{uuid.uuid4().hex}.wav"
    out_path = AUDIO_OUT_DIR / out_name

    voice_engine.synthesize(
        text=reply_text,
        out_path=str(out_path),
        user_id=str(uid),
        voice_id=voice_id,
        response_tag=tag,
    )

    resp_json = {
        "transcribed_text": user_text,
        "reply": reply_text,
        "tag": tag,
        "confidence": conf,
        "crisis": is_crisis,
        "used_neutral_voice": is_crisis or voice_id is None,
        "audio_url": f"/static/audio_out/{out_name}",
    }
    if "recommendation" in resp_data:
        resp_json["recommendation"] = resp_data["recommendation"]

    return jsonify(resp_json)

@app.route("/static/audio_out/<path:filename>")
def serve_audio(filename):
    return send_from_directory(AUDIO_OUT_DIR, filename)


@app.route("/api/uploads/<path:filename>")
def serve_uploads(filename):
    return send_from_directory(UPLOADS_DIR, filename)


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
                processed     = preprocess(text)
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
    try:
        import torch
        has_torch = True
    except ImportError:
        has_torch = False
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
        if len(moods) >= 3 and has_torch:
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
    try:
        import torch
        has_torch = True
    except ImportError:
        has_torch = False
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
            if lstm_model is not None and has_torch:
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
        Paragraph("ManoRakshak — My Diary", title_s),
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
    filename = f"manorakshak_diary_{date.today().isoformat()}.pdf"
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


# ══════════════════════════════════════════════════════════════
#  CHATBOT VOICE CLONING & TTS
# ══════════════════════════════════════════════════════════════

def estimate_pitch(filepath):
    import numpy as np
    from scipy.io import wavfile
    try:
        fs, data = wavfile.read(filepath)
        if len(data.shape) > 1:
            data = data[:, 0]
        data = data.astype(float)
        
        # Normalize to [-1.0, 1.0] for consistent volume thresholding
        max_val = np.max(np.abs(data))
        if max_val < 1e-4:
            return 120.0  # Quiet fallback
        data = data / max_val
        
        # Frame size of 40ms, hop of 20ms to capture lower frequencies (40Hz period is 25ms)
        frame_len = int(fs * 0.04)
        hop_len = int(fs * 0.02)
        pitches = []
        for i in range(0, len(data) - frame_len, hop_len):
            frame = data[i:i+frame_len]
            # Center the frame
            frame = frame - np.mean(frame)
            if np.std(frame) < 0.01:  # Noise gate threshold on normalized audio
                continue
            
            # Autocorrelation
            corr = np.correlate(frame, frame, mode='full')
            corr = corr[len(corr)//2:]
            
            # Search lags corresponding to 40Hz to 500Hz
            min_lag = int(fs / 500)
            max_lag = int(fs / 40)
            if max_lag >= len(corr):
                max_lag = len(corr) - 1
            if min_lag >= max_lag:
                continue
                
            peak_lag = min_lag + np.argmax(corr[min_lag:max_lag])
            pitch = fs / peak_lag
            if 40 <= pitch <= 500:
                pitches.append(pitch)
                
        if not pitches:
            return 120.0  # Male-like default fallback
        return float(np.median(pitches))
    except Exception as e:
        app.logger.warning(f"Error estimating pitch of {filepath}: {e}")
        return 120.0


def time_stretch(data, factor, nfft=1024, hop=256):
    import numpy as np
    import scipy.signal as signal
    f, t, spec = signal.stft(data, fs=1.0, nperseg=nfft, noverlap=nfft-hop)
    num_frames = spec.shape[1]
    new_num_frames = int(num_frames / factor)
    if new_num_frames <= 0:
        return data
    phase_adv = 2 * np.pi * hop * f
    phase = np.angle(spec[:, 0])
    new_spec = np.zeros((spec.shape[0], new_num_frames), dtype=complex)
    time_indices = np.linspace(0, num_frames - 1, new_num_frames)
    for i, t_idx in enumerate(time_indices):
        idx1 = int(np.floor(t_idx))
        idx2 = min(idx1 + 1, num_frames - 1)
        alpha = t_idx - idx1
        mag = (1 - alpha) * np.abs(spec[:, idx1]) + alpha * np.abs(spec[:, idx2])
        new_spec[:, i] = mag * np.exp(1j * phase)
        if idx1 < num_frames - 1:
            dp = np.angle(spec[:, idx2]) - np.angle(spec[:, idx1]) - phase_adv
            dp = dp - 2 * np.pi * np.round(dp / (2 * np.pi))
            phase += phase_adv + dp
    _, stretched = signal.istft(new_spec, fs=1.0, nperseg=nfft, noverlap=nfft-hop)
    return stretched

def pitch_shift(data, fs, semitones):
    import numpy as np
    import scipy.signal as signal
    if semitones == 0:
        return data
    factor = 2 ** (semitones / 12.0)
    new_len = int(len(data) / factor)
    if new_len <= 0:
        return data
    resampled = signal.resample(data, new_len)
    shifted = time_stretch(resampled, 1.0 / factor)
    return shifted

def get_voice_profile_dir(uid):
    p = DATA_DIR / "voice_profiles" / str(uid)
    p.mkdir(parents=True, exist_ok=True)
    return p

def load_voice_config(uid):
    p = get_voice_profile_dir(uid) / "voice_config.json"
    if p.exists():
        try:
            return json.loads(p.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {
        "enabled": False,
        "voice_type": "system",
        "base_pitch_hz": 150.0,
        "pitch_shift_semitones": 0.0,
        "speed_factor": 1.0,
        "configured": False,
        "browser_voice": ""
    }

def save_voice_config(uid, config):
    p = get_voice_profile_dir(uid) / "voice_config.json"
    p.write_text(json.dumps(config, indent=2), encoding="utf-8")

@app.route("/api/voice/clone/upload", methods=["POST"])
@user_only
def upload_voice_clone():
    if "file" not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files["file"]
    if not file.filename:
        return jsonify({"error": "No selected file"}), 400
    
    uid = get_current_user_id()
    p_dir = get_voice_profile_dir(uid)
    ref_path = p_dir / "voice_ref.wav"
    file.save(ref_path)
    
    # Estimate pitch
    pitch_hz = estimate_pitch(ref_path)
    
    config = load_voice_config(uid)
    config["base_pitch_hz"] = pitch_hz
    config["configured"] = True
    config["voice_type"] = "cloned"
    config["enabled"] = True
    save_voice_config(uid, config)
    
    return jsonify({
        "ok": True,
        "base_pitch_hz": round(pitch_hz, 1),
        "msg": f"Voice profile saved and analyzed successfully. Estimated pitch: {pitch_hz:.1f}Hz"
    })

@app.route("/api/voice/clone/settings", methods=["GET", "POST"])
@user_only
def voice_clone_settings():
    uid = get_current_user_id()
    config = load_voice_config(uid)
    
    if request.method == "POST":
        body = request.get_json(force=True)
        config["enabled"] = bool(body.get("enabled", config.get("enabled")))
        config["voice_type"] = body.get("voice_type", config.get("voice_type"))
        config["pitch_shift_semitones"] = float(body.get("pitch_shift_semitones", config.get("pitch_shift_semitones", 0.0)))
        config["speed_factor"] = float(body.get("speed_factor", config.get("speed_factor", 1.0)))
        config["browser_voice"] = body.get("browser_voice", config.get("browser_voice", ""))
        save_voice_config(uid, config)
        return jsonify({"ok": True, "settings": config})
        
    return jsonify({"ok": True, "settings": config})

@app.route("/api/voice/tts", methods=["POST"])
@user_only
def voice_tts():
    import win32com.client
    import pythoncom
    import tempfile
    import os
    import math
    from scipy.io import wavfile
    import numpy as np

    uid = get_current_user_id()
    body = request.get_json(force=True)
    text = body.get("text", "").strip()
    voice_id = body.get("voice_id")
    tag = body.get("tag")
    
    if not text:
        return jsonify({"error": "No text provided"}), 400
        
    config = load_voice_config(uid)
    
    # ── Step 0: Try XTTS v2 Cloned voice if voice_id is specified ──
    if voice_id:
        try:
            import voice_engine
            out_name = f"tts_{uid}_{uuid.uuid4().hex}.wav"
            out_path = AUDIO_OUT_DIR / out_name
            
            voice_engine.synthesize(
                text=text,
                out_path=str(out_path),
                user_id=str(uid),
                voice_id=voice_id,
                response_tag=tag,
            )
            
            with open(out_path, "rb") as f:
                audio_bytes = f.read()
            try:
                os.remove(out_path)
            except Exception:
                pass
                
            buf = io.BytesIO(audio_bytes)
            buf.seek(0)
            return send_file(buf, mimetype="audio/wav")
        except Exception as xtts_err:
            app.logger.error(f"XTTS synthesis failed: {xtts_err}. Falling back to SAPI5/DSP.")
            
    # ── Step 1: Synthesize base TTS WAV with SAPI5 ──
    temp_dir = tempfile.gettempdir()
    base_wav_path = os.path.join(temp_dir, f"sapi_{uid}_{uuid.uuid4().hex}.wav")
    
    # SAPI requires CoInitialize if in thread context (Flask runs multithreaded)
    pythoncom.CoInitialize()
    try:
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        filestream = win32com.client.Dispatch("SAPI.SpFileStream")
        
        # Format 18 is SAFT16kHz16BitMono (standard PCM WAV)
        filestream.Format.Type = 18
        filestream.Open(base_wav_path, 3, False)
        voice.AudioOutputStream = filestream
        
        speed_factor = config.get("speed_factor", 1.0)
        sapi_rate = int(10 * math.log(speed_factor) / math.log(1.5)) if speed_factor > 0 else 0
        sapi_rate = max(-10, min(10, sapi_rate))
        voice.Rate = sapi_rate
        
        voice.Speak(text)
        filestream.Close()
    except Exception as e:
        app.logger.error(f"SAPI synthesis failed: {e}")
        pythoncom.CoUninitialize()
        return jsonify({"error": "Failed to synthesize speech"}), 500
    finally:
        pythoncom.CoUninitialize()
        
    # ── Step 2: Apply DSP if cloned mode is active and configured ──
    output_wav_path = base_wav_path
    
    if config.get("voice_type") == "cloned" and config.get("configured"):
        ref_path = get_voice_profile_dir(uid) / "voice_ref.wav"
        if ref_path.exists():
            try:
                # Estimate baseline pitch of SAPI voice dynamically
                sapi_pitch = estimate_pitch(base_wav_path)
                target_pitch = config.get("base_pitch_hz", 150.0)
                
                # Manual pitch adjustment semitones
                user_semitones = config.get("pitch_shift_semitones", 0.0)
                
                # Auto pitch conversion semitones
                auto_semitones = 12 * math.log2(target_pitch / sapi_pitch) if sapi_pitch > 0 else 0
                total_semitones = auto_semitones + user_semitones
                
                # Cap the pitch shifting to prevent extreme audio distortion
                total_semitones = max(-12.0, min(12.0, total_semitones))
                
                # Load synthesized audio
                fs, audio_data = wavfile.read(base_wav_path)
                if len(audio_data.shape) > 1:
                    audio_data = audio_data[:, 0]
                audio_float = audio_data.astype(float) / 32768.0
                
                # Shift pitch
                shifted = pitch_shift(audio_float, fs, total_semitones)
                
                # Save processed audio
                processed_path = os.path.join(temp_dir, f"processed_{uid}_{uuid.uuid4().hex}.wav")
                wavfile.write(processed_path, fs, (shifted * 32767).astype(np.int16))
                
                # Clean up SAPI base file
                try:
                    os.remove(base_wav_path)
                except Exception:
                    pass
                
                output_wav_path = processed_path
            except Exception as dsp_err:
                app.logger.error(f"DSP Pitch shifting failed: {dsp_err}")
                
    # ── Step 3: Send file ──
    try:
        with open(output_wav_path, "rb") as f:
            audio_bytes = f.read()
        try:
            os.remove(output_wav_path)
        except Exception:
            pass
        buf = io.BytesIO(audio_bytes)
        buf.seek(0)
        return send_file(buf, mimetype="audio/wav")
    except Exception as io_err:
        app.logger.error(f"Error reading synthesized audio file: {io_err}")
        return jsonify({"error": "Failed to stream audio file"}), 500


@app.route("/api/health")
def health():
    bundle = load_ml_model()
    return jsonify({
        "status":        "ok",
        "ml_model":      "loaded" if bundle else "not found",
        "diary_entries": len(load_diary()["entries"]),
        "games":         len(get_available_games()),
    })


# ══════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════
def validate_and_setup_ollama():
    """Verify Ollama service and models are available, and perform auto-indexing if database is missing."""
    import os
    from backend.offline_llm_engine import is_ollama_running
    from backend.rag_engine import check_ollama_model, index_knowledge_base, DB_PATH
    
    print("\n" + "─" * 52)
    print("  Ollama & RAG Offline Assistant Diagnostics")
    print("─" * 52)
    
    ollama_ok = is_ollama_running()
    llm_model = os.environ.get("OLLAMA_LLM_MODEL", "llama3.2:1b")
    embed_model = os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
    
    if not ollama_ok:
        print("  Status: ⚠️  Ollama service is NOT running/responsive.")
        print("          Offline RAG + LLM features will fall back to local ML models.")
        print("          To enable: Install and start Ollama (http://ollama.ai).")
    else:
        print("  Status: ✅ Ollama service is running.")
        
        # Verify LLM Model
        if check_ollama_model(llm_model):
            print(f"  LLM Model:   ✅ '{llm_model}' is available.")
        else:
            print(f"  LLM Model:   ⚠️  '{llm_model}' is NOT downloaded.")
            print(f"               To download, run: ollama pull {llm_model}")
            
        # Verify Embedding Model
        if check_ollama_model(embed_model):
            print(f"  Embed Model: ✅ '{embed_model}' is available.")
        else:
            print(f"  Embed Model: ⚠️  '{embed_model}' is NOT downloaded.")
            print(f"               To download, run: ollama pull {embed_model}")
            
    # Auto-indexing check
    force_reindex = os.environ.get("FORCE_RAG_REINDEX", "false").lower() == "true"
    db_exists = os.path.exists(DB_PATH) and len(os.listdir(DB_PATH)) > 0 if os.path.exists(DB_PATH) else False
    
    if force_reindex or not db_exists:
        if force_reindex:
            print("\n  RAG Database: Forced re-indexing requested via FORCE_RAG_REINDEX.")
        else:
            print("\n  RAG Database: ⚠️  Vector database folder is missing or empty.")
            
        if ollama_ok and check_ollama_model(embed_model):
            print("                Indexing knowledge base now...")
            try:
                index_knowledge_base()
                print("                ✅ RAG Indexing complete!")
            except Exception as e:
                print(f"                ❌ RAG Indexing failed: {e}")
        else:
            print("                Cannot perform indexing. Ollama or Embedding model is unavailable.")
            print("                Run 'python index_rag.py' manually once they are online.")
    else:
        print("  RAG Database: ✅ Persistent database files found.")
        
    print("─" * 52 + "\n")

# ══════════════════════════════════════════════════════════════
#  VERSION 2 — ATROCITY VICTIM MONITORING & DISTRESS PREDICTION APIs
# ══════════════════════════════════════════════════════════════

@app.route("/api/victim/profile", methods=["GET", "POST"])
@user_only
def api_victim_profile():
    from db import get_victim_profile, create_victim_profile
    uid = get_current_user_id()
    if request.method == "GET":
        profile = get_victim_profile(uid)
        if not profile:
            return jsonify({"ok": True, "profile": None})
        return jsonify({"ok": True, "profile": profile})
    
    # POST: Create or update profile
    body = request.get_json(force=True)
    case_num = body.get("case_number", "").strip()
    category = body.get("category", "").strip()
    stage = body.get("judicial_stage", "Investigation").strip()
    counselor_id = body.get("counselor_id")
    
    if not case_num or not category:
        return jsonify({"error": "Case number and Atrocity Category are required"}), 400
        
    try:
        profile = create_victim_profile(uid, case_num, category, stage, counselor_id)
        return jsonify({"ok": True, "profile": profile})
    except Exception as e:
        app.logger.error(f"Error creating victim profile: {e}")
        return jsonify({"error": "Failed to save victim profile"}), 500


@app.route("/api/victim/distress-history", methods=["GET"])
@login_required
def api_victim_distress_history():
    from db import get_victim_distress_history
    role = get_user_role()
    uid = get_current_user_id()
    
    target_uid = request.args.get("user_id", type=int)
    if role == "therapist" and target_uid:
        uid_to_query = target_uid
    else:
        uid_to_query = uid
        
    history = get_victim_distress_history(uid_to_query)
    return jsonify({"ok": True, "history": history})


@app.route("/api/victim/alerts", methods=["GET"])
@login_required
def api_victim_alerts():
    if get_user_role() != "therapist":
        return jsonify({"error": "Access denied"}), 403
        
    from db import get_active_alerts
    alerts = get_active_alerts()
    return jsonify({"ok": True, "alerts": alerts})


@app.route("/api/victim/alerts/<int:alert_id>/resolve", methods=["POST"])
@login_required
def api_resolve_alert(alert_id):
    if get_user_role() != "therapist":
        return jsonify({"error": "Access denied"}), 403
        
    from db import resolve_alert
    body = request.get_json(force=True)
    notes = body.get("notes", "").strip()
    uid = get_current_user_id()
    
    if not notes:
        return jsonify({"error": "Resolution notes are required"}), 400
        
    success = resolve_alert(alert_id, uid, notes)
    return jsonify({"ok": success})


@app.route("/api/victim/checkin", methods=["POST"])
@user_only
def api_victim_checkin():
    """
    Continuous Check-in Endpoint.
    Accepts text and optional audio file, runs sentiment analysis + voice stress metrics,
    calculates Dynamic Distress Score (DDS), logs it, and triggers alerts if threshold is crossed.
    """
    import math
    from db import get_victim_profile, save_victim_distress_score, trigger_victim_alert, get_user_assessments
    
    uid = get_current_user_id()
    text = request.form.get("text", "").strip()
    
    vocal_stress = None
    vsa_metrics = {}
    transcribed_text = ""
    
    if "audio" in request.files:
        audio_file = request.files["audio"]
        temp_name = f"vsa_{uuid.uuid4().hex}.wav"
        temp_path = UPLOAD_DIR / temp_name
        audio_file.save(temp_path)
        
        try:
            # 1. Transcribe text using Whisper
            transcribed_text = voice_engine.transcribe(str(temp_path))
            if transcribed_text and not text:
                text = transcribed_text
            
            # 2. Extract acoustic stress metrics
            vsa_metrics = voice_engine.analyze_voice_stress(str(temp_path))
            vocal_stress = vsa_metrics.get("stress_score", 0.0)
        except Exception as e:
            app.logger.error(f"VSA Analysis failed: {e}")
        finally:
            if temp_path.exists():
                temp_path.unlink()

    if not text and vocal_stress is None:
        return jsonify({"error": "Please provide either text or a voice recording check-in."}), 400

    # 1. Calculate Text Sentiment Distress Score
    text_distress_score = 0.5
    sentiment_tag = "neutral"
    
    if text:
        import numpy as np
        bundle = load_ml_model()
        if bundle and isinstance(bundle, dict):
            try:
                model = bundle.get("ensemble") or bundle.get("pipeline")
                if model is not None:
                    le = bundle["label_encoder"]
                    processed = preprocess(text)
                    proba = model.predict_proba([processed])[0]
                    idx = int(np.argmax(proba))
                    sentiment_tag = le.inverse_transform([idx])[0]
                    
                    tag_distress_weights = {
                        "anxious": 0.85,
                        "sad": 0.75,
                        "angry": 0.70,
                        "suicidal": 1.0,
                        "self_harm": 1.0,
                        "calm": 0.20,
                        "happy": 0.10,
                        "excited": 0.05
                    }
                    text_distress_score = tag_distress_weights.get(sentiment_tag, 0.40)
            except Exception as e:
                app.logger.warning(f"Error calculating text distress: {e}")

    # 2. Fetch Latest Clinical Assessments
    assessment_score_norm = None
    last_assessment = None
    try:
        assessments = get_user_assessments(uid)
        if assessments:
            last_assessment = assessments[0]
            score = last_assessment.get("score", 0)
            a_type = last_assessment.get("type", "GAD-7").upper()
            max_possible = 27 if "PHQ" in a_type else 21
            assessment_score_norm = score / max_possible
    except Exception as e:
        app.logger.warning(f"Error reading user assessments: {e}")

    # 3. Dynamic Distress Score (DDS) Weighted Aggregation
    weights = {"text": 0.4, "vocal": 0.4, "clinical": 0.2}
    total_weight = 0.0
    weighted_sum = 0.0
    
    if text:
        weighted_sum += text_distress_score * weights["text"]
        total_weight += weights["text"]
        
    if vocal_stress is not None:
        weighted_sum += vocal_stress * weights["vocal"]
        total_weight += weights["vocal"]
        
    if assessment_score_norm is not None:
        weighted_sum += assessment_score_norm * weights["clinical"]
        total_weight += weights["clinical"]
        
    dds = (weighted_sum / total_weight) * 100 if total_weight > 0 else 50.0
    dds = min(100.0, max(0.0, dds))
    
    # 4. Contextual Additive Adjustments (Case Stage)
    profile = get_victim_profile(uid)
    if profile:
        stage = profile.get("judicial_stage", "Investigation")
        if stage == "Investigation":
            dds += 5.0
        elif stage == "Trial":
            dds += 10.0

    dds = round(min(100.0, dds), 2)

    # 5. Save score in DB
    details = {
        "text_sentiment_tag": sentiment_tag,
        "text_sentiment_distress": round(text_distress_score, 4),
        "vocal_stress_metrics": vsa_metrics,
        "latest_clinical_assessment": last_assessment,
        "transcribed_audio": transcribed_text
    }
    a_score_val = last_assessment.get("score") if last_assessment else None
    
    save_victim_distress_score(
        user_id=uid,
        score=dds,
        sentiment_score=text_distress_score if text else None,
        vocal_stress=vocal_stress,
        assessment_score=a_score_val,
        details_json=json.dumps(details)
    )

    # 6. Check Risk Threshold (Alert Trigger)
    alert_triggered = False
    alert_id = None
    if dds > 75.0:
        alert_triggered = True
        reason = f"DDS exceeded risk threshold at {dds}%. "
        reasons = []
        if text_distress_score > 0.7:
            reasons.append(f"high textual distress (sentiment: {sentiment_tag})")
        if vocal_stress and vocal_stress > 0.6:
            reasons.append(f"high vocal tension (VSA stress: {round(vocal_stress*100)}%)")
        if last_assessment and score > 15:
            reasons.append(f"severe clinical check-in score ({score} on {last_assessment.get('type')})")
            
        reason += "Indicators: " + ", ".join(reasons) if reasons else "Triggered by overall weighted metrics."
        alert_id = trigger_victim_alert(uid, dds, reason)

    # 7. Generate Rehabilitation Suggestions
    recommendations = []
    if dds > 75.0:
        recommendations.append({
            "type": "witness_protection",
            "title": "Witness Protection Referral",
            "desc": "Due to high distress/threat levels, you can request an immediate security audit and witness protection allocation via local police nodal officers."
        })
    if last_assessment and last_assessment.get("severity", "").lower() in ("moderate", "severe"):
        recommendations.append({
            "type": "clinical",
            "title": "Emergency Counselling Session",
            "desc": "Your indicators show severe anxiety or depression. We recommend scheduling an immediate session with your assigned counselor."
        })
    
    if profile:
        category = profile.get("category", "")
        recommendations.append({
            "type": "legal_aid",
            "title": "Legal Services Association (DLSA)",
            "desc": f"Under the SC/ST Act provisions for {category}, you are entitled to free legal aid representation. We can auto-route your files to the nearest District Legal Services Authority."
        })
        recommendations.append({
            "type": "compensation",
            "title": "Victim Relief Compensation Claim",
            "desc": "Check your compensation disbursement status. Victims of atrocity are entitled to financial relief schemes (up to 8.25 Lakhs depending on the offense category)."
        })
    else:
        recommendations.append({
            "type": "legal_aid",
            "title": "District Legal Aid",
            "desc": "Access free legal consultation and witness advocacy resources."
        })

    return jsonify({
        "ok": True,
        "distress_score": dds,
        "sentiment_tag": sentiment_tag,
        "vsa_metrics": vsa_metrics,
        "transcribed_text": transcribed_text,
        "alert_triggered": alert_triggered,
        "alert_id": alert_id,
        "recommendations": recommendations
    })


@app.route("/api/victim/recommendations", methods=["GET"])
@user_only
def api_victim_recommendations():
    from db import get_victim_profile
    uid = get_current_user_id()
    profile = get_victim_profile(uid)
    
    recs = []
    if profile:
        stage = profile.get("judicial_stage", "Investigation")
        category = profile.get("category", "")
        
        if stage == "Investigation":
            recs.append({
                "title": "Charge Sheet Filing Tracker",
                "desc": "Under the SC/ST Act, the police must submit the charge sheet within 60 days. Click here to trace status updates from the Deputy Superintendent of Police (DySP)."
            })
        elif stage == "Trial":
            recs.append({
                "title": "Special Court Court-Appearance Assistance",
                "desc": "You are eligible for travel allowance (TA/DA) and daily allowance for attending court hearings. Submit your receipts here."
            })
            recs.append({
                "title": "Witness Protection & Security",
                "desc": "If you or your family are facing intimidation, you can file a petition under Section 15A of the SC/ST Act for safety arrangements."
            })
            
        recs.append({
            "title": "Mandatory Relief Compensation Scheme",
            "desc": f"Get assistance claiming the statutory relief funds allocated for victims of '{category}' offenses."
        })
        recs.append({
            "title": "Relocation & Rehabilitation Support",
            "desc": "Government programs offer land allotment, house construction support, and employment slots for severely affected families."
        })
    else:
        recs.append({
            "title": "General Victim Compensation Fund",
            "desc": "Learn about the Central Victim Compensation Fund (CVCF) and state assistance schemes."
        })
        
    return jsonify({"ok": True, "recommendations": recs})


@app.route("/api/victim/supervised-list", methods=["GET"])
@login_required
def api_supervised_list():
    if get_user_role() != "therapist":
        return jsonify({"error": "Access denied"}), 403
        
    from db import get_supervised_victims, get_all_victims_for_admin
    uid = get_current_user_id()
    
    scope = request.args.get("scope", "my")
    if scope == "all":
        victims = get_all_victims_for_admin()
    else:
        victims = get_supervised_victims(uid)
        
    from db import get_victim_distress_history
    enriched = []
    for v in victims:
        history = get_victim_distress_history(v["user_id"])
        latest_score = history[-1]["score"] if history else 30.0
        v["latest_distress_score"] = latest_score
        enriched.append(v)
        
    enriched.sort(key=lambda x: x["latest_distress_score"], reverse=True)
    return jsonify({"ok": True, "victims": enriched})


@app.route("/api/victim/vault", methods=["POST"])
@user_only
def create_vault_incident_api():
    from db import log_vault_incident, trigger_victim_alert
    from werkzeug.utils import secure_filename
    
    uid = get_current_user_id()
    incident_type = request.form.get("incident_type", "verbal_threat").strip()
    description = request.form.get("description", "").strip()
    
    if not description:
        return jsonify({"error": "Incident description is required."}), 400
        
    evidence_file = request.files.get("evidence")
    file_path = None
    if evidence_file and evidence_file.filename:
        fname = secure_filename(evidence_file.filename)
        # prefix user_id and timestamp
        fname = f"vault_{uid}_{int(datetime.now().timestamp())}_{fname}"
        file_path = str(UPLOADS_DIR / fname)
        evidence_file.save(file_path)
        
    # Auto severity mapping
    severity = "Medium"
    critical_keywords = ["kill", "murder", "weapon", "shoot", "attack", "death", "beat", "burn", "destroy", "gun", "knife"]
    desc_lower = description.lower()
    if any(kw in desc_lower for kw in critical_keywords):
        severity = "High"
        
    try:
        log_vault_incident(uid, incident_type, description, file_path, severity)
        if severity == "High":
            # Auto-trigger priority alert on counselor dashboard
            trigger_victim_alert(
                user_id=uid,
                score=100.0,
                reason=f"URGENT WITNESS VAULT THREAT INCIDENT LOGGED (Type: {incident_type}): {description[:200]}..."
            )
        return jsonify({"ok": True, "severity": severity})
    except Exception as e:
        app.logger.error(f"Error logging vault incident: {e}")
        return jsonify({"error": "Failed to store threat evidence."}), 500


@app.route("/api/victim/vault", methods=["GET"])
@login_required
def get_vault_incidents_api():
    from db import get_vault_incidents
    role = get_user_role()
    uid = get_current_user_id()
    
    if role == "therapist":
        target_uid = request.args.get("user_id")
        if not target_uid:
            return jsonify({"error": "user_id parameter is required for counselors."}), 400
        uid = int(target_uid)
        
    try:
        incidents = get_vault_incidents(uid)
        return jsonify({"ok": True, "incidents": incidents})
    except Exception as e:
        app.logger.error(f"Error fetching vault incidents: {e}")
        return jsonify({"error": "Failed to load logged incidents."}), 500


@app.route("/api/victim/schemes", methods=["GET"])
@user_only
def get_rehab_schemes_api():
    from db import get_victim_profile
    uid = get_current_user_id()
    profile = get_victim_profile(uid)
    
    schemes = [
        {
            "title": "National Safai Karamcharis Finance and Development Corporation (NSKFDC)",
            "desc": "Offers rehabilitation schemes and low-interest self-employment loans up to ₹5.0 Lakhs to targeted caste beneficiaries and manual scavengers.",
            "link": "https://nskfdc.nic.in"
        },
        {
            "title": "PM-DAKSH (Pradhan Mantri Dakshta Aur Kushalta Sampann Hitgrahi)",
            "desc": "Providing free skill development training programs (short-term & long-term) with monthly stipends for youths of SC/ST and marginalized groups.",
            "link": "https://pmdaksh.dosje.gov.in"
        },
        {
            "title": "One Stop Center Scheme (Sakhi)",
            "desc": "Subsidized shelter, medical support, legal aid, and counseling center for female atrocity survivors. Auto-integrated with closest nodal office.",
            "link": "https://wcd.nic.in"
        },
        {
            "title": "Dr. Ambedkar Scheme for Social Integration",
            "desc": "Relief schemes and incentives for inter-caste marriages under the protection of district courts to promote integration and combat boycott threat.",
            "link": "https://ambedkarfoundation.nic.in"
        }
    ]
    return jsonify({"ok": True, "schemes": schemes})


@app.route("/api/victim/sos", methods=["POST"])
@user_only
def trigger_sos_api():
    from db import log_sos_alert, trigger_victim_alert
    uid = get_current_user_id()
    lat = request.json.get("latitude") if request.is_json else request.form.get("latitude")
    lng = request.json.get("longitude") if request.is_json else request.form.get("longitude")
    
    if not lat or not lng:
        return jsonify({"error": "Latitude and Longitude coordinates are required."}), 400
        
    try:
        log_sos_alert(uid, str(lat), str(lng))
        trigger_victim_alert(
            user_id=uid,
            score=100.0,
            reason=f"🚨 CRITICAL SOS TRIGGERED: Victim locked GPS position at lat: {lat}, lng: {lng}."
        )
        return jsonify({"ok": True, "msg": "SOS dispatched successfully."})
    except Exception as e:
        app.logger.error(f"Error handling SOS route: {e}")
        return jsonify({"error": "Failed to log SOS emergency alert."}), 500


@app.route("/api/victim/sos", methods=["GET"])
@login_required
def get_sos_api():
    from db import get_active_sos_alerts
    role = get_user_role()
    if role != "therapist":
        return jsonify({"error": "Unauthorized."}), 403
    try:
        alerts = get_active_sos_alerts()
        return jsonify({"ok": True, "alerts": alerts})
    except Exception as e:
        app.logger.error(f"Error fetching SOS alerts: {e}")
        return jsonify({"error": "Failed to load active SOS signals."}), 500


@app.route("/api/victim/sos/<int:sos_id>/dispatch", methods=["POST"])
@login_required
def dispatch_sos_api(sos_id):
    from db import dispatch_officer_to_sos
    role = get_user_role()
    if role != "therapist":
        return jsonify({"error": "Unauthorized."}), 403
    
    officer = request.json.get("officer_name") if request.is_json else request.form.get("officer_name")
    if not officer:
        officer = "Nodal Protection Guard"
        
    try:
        dispatch_officer_to_sos(sos_id, officer)
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.error(f"Error updating dispatch status: {e}")
        return jsonify({"error": "Failed to dispatch guard."}), 500


@app.route("/api/victim/claims", methods=["POST"])
@user_only
def create_claim_api():
    from db import submit_compensation_claim, get_victim_profile
    uid = get_current_user_id()
    profile = get_victim_profile(uid)
    
    if not profile:
        return jsonify({"error": "No registered victim case file found."}), 400
        
    stage = request.json.get("stage") if request.is_json else request.form.get("stage")
    bank_name = request.json.get("bank_name", "State Bank of India") if request.is_json else request.form.get("bank_name", "State Bank of India")
    bank_ifsc = request.json.get("bank_ifsc", "") if request.is_json else request.form.get("bank_ifsc", "")
    bank_account = request.json.get("bank_account", "") if request.is_json else request.form.get("bank_account", "")
    
    if not stage:
        return jsonify({"error": "Stage parameter is required."}), 400
        
    # Map statutory amounts
    # SC/ST Act Rule 12(4) Relief Scales:
    # Category Caste Violence / Grievous Hurt is 4.5 Lakhs (450,000).
    # Stage FIR gets 50% (225,000). Stage Charge Sheet gets 25% (112,500). Stage Verdict gets 25% (112,500).
    category = profile["category"] or ""
    amount = 450000.0 # base default
    if "8.25" in category or "Arson" in category or "Loss of Life" in category:
        amount = 825000.0
    elif "1.0" in category or "Social Boycott" in category or "100000" in category:
        amount = 100000.0
        
    tranche_pct = 0.50 if stage == "FIR" else 0.25
    tranche_amount = amount * tranche_pct
    
    try:
        from datetime import datetime
        date_str = datetime.now().strftime("%Y-%m-%d")
        petition_text = f"""
============================================================
REPRESENTATION FOR RELEASE OF DELAYED STATUTORY RELIEF
Under SC/ST (Prevention of Atrocities) Rules, Rule 12(4)
============================================================
Date of Filing: {date_str}
To,
The District Magistrate / Chairperson,
District Level Vigilance and Monitoring Committee (DLVMC)
District Collectorate Office.

SUBJECT: Demand for release of overdue '{stage}' tranche of INR {tranche_amount:,.2f}

Respected Chairperson,
I, the undersigned, am a registered victim in Case Number: {profile['case_number']} (Offense category: {profile['category']}). 
Under Rule 12(4) of the SC/ST (Prevention of Atrocities) Rules, the administration is obligated to disburse the statutory relief amount immediately upon the completion of the procedural milestone. 

The milestone for '{stage}' has been completed, but the tranche payment of INR {tranche_amount:,.2f} is currently overdue.
The petitioner requests immediate Direct Benefit Transfer (DBT) to the following verified account:

BANK NAME: {bank_name}
IFSC CODE: {bank_ifsc}
ACCOUNT NO: {bank_account}

We pray for early relief release to avoid financial distress.

Signed,
Complainant ID: {uid}
(Through ManoRakshak Victim Portal Auto-Signature)
============================================================
"""
        submit_compensation_claim(uid, profile["case_number"], tranche_amount, stage, petition_text)
        return jsonify({"ok": True, "petition": petition_text})
    except Exception as e:
        app.logger.error(f"Error submitting claim: {e}")
        return jsonify({"error": "Failed to submit compensation claim."}), 500


@app.route("/api/victim/claims", methods=["GET"])
@login_required
def get_claims_api():
    from db import get_victim_claims, get_all_pending_claims
    role = get_user_role()
    uid = get_current_user_id()
    
    try:
        if role == "therapist":
            claims = get_all_pending_claims()
        else:
            claims = get_victim_claims(uid)
        return jsonify({"ok": True, "claims": claims})
    except Exception as e:
        app.logger.error(f"Error fetching claims: {e}")
        return jsonify({"error": "Failed to load claims list."}), 500


@app.route("/api/victim/claims/<int:claim_id>/status", methods=["POST"])
@login_required
def update_claim_status_api(claim_id):
    from db import update_claim_status
    role = get_user_role()
    if role != "therapist":
        return jsonify({"error": "Unauthorized."}), 403
        
    status = request.json.get("status") if request.is_json else request.form.get("status")
    if not status:
        return jsonify({"error": "Status is required."}), 400
        
    try:
        update_claim_status(claim_id, status)
        return jsonify({"ok": True})
    except Exception as e:
        app.logger.error(f"Error updating claim status: {e}")
        return jsonify({"error": "Failed to update claim status."}), 500


@app.route("/api/victim/hearing-prep", methods=["POST"])
@user_only
def generate_hearing_prep_api():
    from db import get_victim_profile
    uid = get_current_user_id()
    profile = get_victim_profile(uid)
    
    category = profile["category"] if profile else "SC/ST Atrocity"
    stage = profile["judicial_stage"] if profile else "Trial"
    
    # Formulate prompt for Llama 3.2
    prompt = f"""
[System Instruction]
Provide a clear, comforting, and bulleted 4-point court trial preparation guide for a victim of atrocity registered under the offense category: '{category}' currently at the judicial stage: '{stage}'.
Respond ONLY with the 4 bulleted preparation guidelines. Maintain a comforting, reassuring, and legally informative tone. Do not add conversational headers or footers.

4-Point Preparation Checklist:
"""
    try:
        # Request Llama 3.2 from the local Ollama API
        import requests as r_lib
        res = r_lib.post(
            "http://127.0.0.1:11434/api/generate",
            json={"model": "llama3.2:1b", "prompt": prompt, "stream": False},
            timeout=15
        )
        if res.status_code == 200:
            result_text = res.json().get("response", "").strip()
        else:
            result_text = "Failed to communicate with LLM server. Contact DLSA representative."
        return jsonify({"ok": True, "guidelines": result_text})
    except Exception as e:
        app.logger.error(f"Ollama hearing prep generation error: {e}")
        # Fallback rule-based guide if Ollama times out
        fallback_guide = f"1. Prepare all copies of the FIR and witness summons.\n2. You are entitled to travel and daily allowances for attending the Court. Check in with the court clerk.\n3. Request in-camera Special Court hearings if you feel threatened or anxious.\n4. You have the right to request water or ask the judge to repeat the question."
        return jsonify({"ok": True, "guidelines": fallback_guide})


@app.route("/api/admin/analytics", methods=["GET"])
@login_required
def admin_analytics_api():
    import mysql.connector
    from db import get_pool
    uid = get_current_user_id()
    
    try:
        pool = get_pool()
        conn = pool.get_connection()
        cursor = conn.cursor(dictionary=True)
        
        # Total cases count
        cursor.execute("SELECT COUNT(*) as cnt FROM victim_profiles")
        total_cases = cursor.fetchone()["cnt"]
        
        # Active alerts count
        cursor.execute("SELECT COUNT(*) as cnt FROM victim_alerts WHERE status = 'Active'")
        active_alerts = cursor.fetchone()["cnt"]
        
        # Active SOS counts
        cursor.execute("SELECT COUNT(*) as cnt FROM victim_sos_alerts WHERE status = 'Active'")
        active_sos = cursor.fetchone()["cnt"]
        
        # Claims disbursements stats
        cursor.execute("SELECT SUM(amount_entitled) as tot, status FROM victim_compensation_claims GROUP BY status")
        claims_rows = cursor.fetchall()
        
        allocated = 0.0
        disbursed = 0.0
        pending = 0.0
        for row in claims_rows:
            tot_val = float(row["tot"] or 0)
            allocated += tot_val
            if row["status"] == "Disbursed":
                disbursed += tot_val
            elif row["status"] in ["Pending", "Approved"]:
                pending += tot_val
                
        # Query actual cases grouped dynamically by category & judicial stage
        cursor.execute("""
            SELECT vp.category, vp.judicial_stage, COUNT(vp.id) as case_count
            FROM victim_profiles vp
            GROUP BY vp.category, vp.judicial_stage
        """)
        category_rows = cursor.fetchall()

        cursor.execute("""
            SELECT vp.category, COUNT(va.id) as alert_count
            FROM victim_alerts va
            JOIN victim_profiles vp ON va.user_id = vp.user_id
            WHERE va.status = 'Active'
            GROUP BY vp.category
        """)
        alert_dict = {row["category"]: row["alert_count"] for row in cursor.fetchall()}

        cursor.execute("""
            SELECT vp.category, SUM(cc.amount_entitled) as total_payout
            FROM victim_compensation_claims cc
            JOIN victim_profiles vp ON cc.user_id = vp.user_id
            WHERE cc.status = 'Disbursed'
            GROUP BY vp.category
        """)
        payout_dict = {row["category"]: float(row["total_payout"] or 0) for row in cursor.fetchall()}

        regional_data = []
        if category_rows:
            for row in category_rows:
                cat = row["category"]
                regional_data.append({
                    "state": cat,
                    "district": f"Stage: {row['judicial_stage']}",
                    "active_cases": row["case_count"],
                    "active_alerts": alert_dict.get(cat, 0),
                    "payouts_completed": payout_dict.get(cat, 0.0)
                })
        else:
            regional_data = [
                {"state": "SC/ST Atrocity & Harassment", "district": "Stage: Investigation", "active_cases": 1, "active_alerts": 1, "payouts_completed": 225000.0},
                {"state": "Witness Intimidation & Threat", "district": "Stage: Trial", "active_cases": 1, "active_alerts": 0, "payouts_completed": 0.0}
            ]
            
        cursor.close()
        conn.close()
        
        return jsonify({
            "ok": True,
            "total_cases": total_cases,
            "active_alerts": active_alerts,
            "active_sos": active_sos,
            "financials": {
                "allocated": allocated,
                "disbursed": disbursed,
                "pending": pending
            },
            "regional_distribution": regional_data
        })
        
    except Exception as e:
        app.logger.error(f"Error compiling admin analytics: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/admin/dashboard")
@login_required
def admin_dashboard_page():
    return send_from_directory(TEMPLATES_DIR, "admin_dashboard.html")


@app.route("/api/victim/non-response-check", methods=["GET"])
@login_required
def api_non_response_check():
    from db import get_silent_period_victims
    hours = request.args.get("hours", 48, type=int)
    silent_victims = get_silent_period_victims(hours)
    return jsonify({"ok": True, "silent_count": len(silent_victims), "victims": silent_victims})


@app.route("/api/victim/xai-explain/<int:score_id>", methods=["GET"])
@login_required
def api_xai_explain(score_id):
    from db import get_xai_explanation
    uid = get_current_user_id()
    explanation = get_xai_explanation(score_id, user_id=uid)
    if not explanation:
        return jsonify({"error": "Distress score calculation record not found."}), 404
    return jsonify({"ok": True, "explanation": explanation})


@app.route("/api/nhaa/ivrs-simulate", methods=["POST"])
@user_only
def api_nhaa_ivrs_simulate():
    """
    Simulate NHAA 14566 National Helpline Against Atrocities IVRS Phone Call Check-in.
    Processes transcribed phone call speech via scikit-learn VotingClassifier ML model,
    calculates distress score, logs entry & flags alert if critical.
    """
    from db import get_victim_profile, save_victim_distress_score, trigger_victim_alert
    import numpy as np
    
    uid = get_current_user_id()
    body = request.get_json(force=True) if request.is_json else request.form
    transcript = body.get("transcript", "").strip()
    dialect = body.get("dialect", "Hindi / Indic").strip()
    
    if not transcript:
        return jsonify({"error": "IVRS phone call transcript input is required."}), 400
        
    text_distress = 0.45
    sentiment_tag = "neutral"
    
    # Run real ML model on IVRS call speech transcript
    bundle = load_ml_model()
    if bundle and isinstance(bundle, dict):
        try:
            model = bundle.get("ensemble") or bundle.get("pipeline")
            if model is not None:
                le = bundle["label_encoder"]
                processed = preprocess(transcript)
                proba = model.predict_proba([processed])[0]
                idx = int(np.argmax(proba))
                sentiment_tag = le.inverse_transform([idx])[0]
                
                tag_distress_weights = {
                    "anxious": 0.85,
                    "sad": 0.75,
                    "angry": 0.70,
                    "suicidal": 1.0,
                    "self_harm": 1.0,
                    "calm": 0.20,
                    "happy": 0.10,
                    "excited": 0.05
                }
                text_distress = tag_distress_weights.get(sentiment_tag, 0.45)
        except Exception as e:
            app.logger.warning(f"Error running ML model on IVRS transcript: {e}")
            
    vocal_stress = 0.70 if text_distress > 0.6 else 0.20
    dds = round((text_distress * 60.0) + (vocal_stress * 40.0), 2)
    
    details = {
        "channel": "NHAA 14566 IVRS Hotline",
        "dialect": dialect,
        "text_sentiment_tag": sentiment_tag,
        "text_sentiment_distress": text_distress,
        "vocal_stress": vocal_stress,
        "raw_transcript": transcript
    }
    
    score_id = save_victim_distress_score(
        user_id=uid,
        score=dds,
        sentiment_score=text_distress,
        vocal_stress=vocal_stress,
        details_json=json.dumps(details)
    )
    
    alert_triggered = False
    if dds > 75.0:
        alert_triggered = True
        trigger_victim_alert(uid, dds, f"NHAA 14566 IVRS HIGH RISK DISTRESS (Dialect: {dialect}, Sentiment: {sentiment_tag}): {transcript[:150]}")
        
    return jsonify({
        "ok": True,
        "score_id": score_id,
        "channel": "NHAA 14566 Hotline",
        "distress_score": dds,
        "sentiment_tag": sentiment_tag,
        "alert_triggered": alert_triggered,
        "transcript": transcript
    })


if __name__ == "__main__":
    validate_and_setup_ollama()
    print("\n" + "═" * 52)
    print("  🌿 ManoRakshak Server")
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
    hub_screen = GAMES_DIR / 'manorakshak_games_hub.html'
    print(f"  Games hub:    {'✅ found' if hub_screen.exists() else '⚠️  not found at '+str(hub_screen)}")
    games = get_available_games()
    print(f"\n  {len(games)} game(s) found: {[g['slug'] for g in games] or 'none yet'}")
    print("═" * 52 + "\n")
    app.run(debug=True, port=5000, host="0.0.0.0")