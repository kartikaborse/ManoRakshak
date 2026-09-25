"""
ManoRakshat — MySQL Database Helpers
─────────────────────────────────
Connects to XAMPP's MariaDB (manorakshat_db) and provides
clean helper functions for all CRUD operations.
"""

import mysql.connector
from mysql.connector import pooling, Error
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date

# ──────────────────────────────────────────────────────────────
#  CONNECTION POOL
# ──────────────────────────────────────────────────────────────
_pool = None

import os

DB_CONFIG = {
    "host":     os.environ.get("DB_HOST", "localhost"),
    "user":     os.environ.get("DB_USER", "root"),
    "password": os.environ.get("DB_PASSWORD", ""),
    "database": os.environ.get("DB_NAME", "manorakshat_db"),
    "port":     int(os.environ.get("DB_PORT", "3306")),
    "charset":  "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": True,
}


def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="manorakshat_pool",
            pool_size=5,
            pool_reset_session=True,
            **DB_CONFIG,
        )
    return _pool


def get_conn():
    return get_pool().get_connection()


def query(sql, params=None, fetchone=False, fetchall=False):
    """Execute a query and optionally fetch results."""
    conn = get_conn()
    try:
        cur = conn.cursor(dictionary=True)
        cur.execute(sql, params or ())
        if fetchone:
            return cur.fetchone()
        if fetchall:
            return cur.fetchall()
        conn.commit()
        return cur.lastrowid
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════
#  USER OPERATIONS
# ══════════════════════════════════════════════════════════════

def create_user(email: str, username: str, full_name: str, password: str, role: str = 'user') -> dict:
    """Create a new user with a specified role. Returns user dict or raises Error."""
    hashed = generate_password_hash(password)
    uid = query(
        """INSERT INTO users (email, username, full_name, hashed_password, role)
           VALUES (%s, %s, %s, %s, %s)""",
        (email, username, full_name, hashed, role),
    )
    return get_user_by_id(uid)


def get_user_by_email(email: str) -> dict | None:
    return query(
        "SELECT * FROM users WHERE email = %s",
        (email,), fetchone=True,
    )


def get_user_by_id(uid: int) -> dict | None:
    return query(
        "SELECT * FROM users WHERE id = %s",
        (uid,), fetchone=True,
    )


def check_login(email: str, password: str) -> dict | None:
    """Validate login. Returns user dict or None."""
    user = get_user_by_email(email)
    if user and check_password_hash(user["hashed_password"], password):
        # Update last active
        query(
            "UPDATE users SET last_active_date = NOW() WHERE id = %s",
            (user["id"],),
        )
        return user
    return None


def update_user_streak(uid: int, streak: int):
    query(
        "UPDATE users SET wellness_streak = %s WHERE id = %s",
        (streak, uid),
    )


def update_user_profile(uid: int, full_name: str, username: str, avatar_emoji: str) -> dict | None:
    """Update user's profile details. Returns updated user dict."""
    query(
        """UPDATE users 
           SET full_name = %s, username = %s, avatar_emoji = %s 
           WHERE id = %s""",
        (full_name, username, avatar_emoji, uid),
    )
    return get_user_by_id(uid)


def update_user_password(uid: int, new_password_plain: str) -> bool:
    """Update user's password securely."""
    hashed = generate_password_hash(new_password_plain)
    query(
        "UPDATE users SET hashed_password = %s WHERE id = %s",
        (hashed, uid),
    )
    return True


# ══════════════════════════════════════════════════════════════
#  DIARY / JOURNAL OPERATIONS
# ══════════════════════════════════════════════════════════════

def get_diary_entries(uid: int) -> dict:
    """Return all entries for a user, keyed by date string (YYYY-MM-DD)."""
    rows = query(
        """SELECT id, entry_date, title, content, mood_tag,
                  sentiment_score, word_count, ai_insight,
                  created_at, updated_at
           FROM journal_entries
           WHERE user_id = %s
           ORDER BY entry_date DESC""",
        (uid,), fetchall=True,
    )
    entries = {}
    for r in rows:
        date_key = r["entry_date"].isoformat() if r["entry_date"] else r["created_at"].strftime("%Y-%m-%d")
        # Fetch tags and photos for this entry
        tags = query(
            "SELECT tag FROM diary_tags WHERE entry_id = %s",
            (r["id"],), fetchall=True,
        )
        photos = query(
            "SELECT url, filename FROM diary_photos WHERE entry_id = %s",
            (r["id"],), fetchall=True,
        )
        # Map mood_tag string to mood number for frontend compatibility
        mood_num = _mood_tag_to_number(r["mood_tag"])
        entries[date_key] = {
            "id":       r["id"],
            "date":     date_key,
            "text":     r["content"] or "",
            "mood":     mood_num,
            "tags":     [t["tag"] for t in tags],
            "photos":   [p["url"] for p in photos],
            "created":  r["created_at"].isoformat() if r["created_at"] else None,
            "updated":  r["updated_at"].isoformat() if r["updated_at"] else None,
        }
    return entries


def get_diary_entry(uid: int, date_key: str) -> dict | None:
    """Get a single entry by date."""
    row = query(
        """SELECT id, entry_date, content, mood_tag, word_count,
                  created_at, updated_at
           FROM journal_entries
           WHERE user_id = %s AND entry_date = %s""",
        (uid, date_key), fetchone=True,
    )
    if not row:
        return None

    tags = query("SELECT tag FROM diary_tags WHERE entry_id = %s",
                 (row["id"],), fetchall=True)
    photos = query("SELECT url FROM diary_photos WHERE entry_id = %s",
                   (row["id"],), fetchall=True)

    mood_num = _mood_tag_to_number(row["mood_tag"])
    return {
        "id":      row["id"],
        "date":    date_key,
        "text":    row["content"] or "",
        "mood":    mood_num,
        "tags":    [t["tag"] for t in tags],
        "photos":  [p["url"] for p in photos],
        "created": row["created_at"].isoformat() if row["created_at"] else None,
        "updated": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


def save_diary_entry(uid: int, date_key: str, text: str, mood, tags: list, photos: list) -> dict:
    """Create or update a diary entry for a given date."""
    mood_tag = _mood_number_to_tag(mood)
    word_count = len(text.split()) if text else 0

    # Check if entry exists for this date
    existing = query(
        "SELECT id FROM journal_entries WHERE user_id = %s AND entry_date = %s",
        (uid, date_key), fetchone=True,
    )

    if existing:
        entry_id = existing["id"]
        query(
            """UPDATE journal_entries
               SET content = %s, mood_tag = %s, word_count = %s, updated_at = NOW()
               WHERE id = %s""",
            (text, mood_tag, word_count, entry_id),
        )
    else:
        entry_id = query(
            """INSERT INTO journal_entries (user_id, entry_date, content, mood_tag, word_count)
               VALUES (%s, %s, %s, %s, %s)""",
            (uid, date_key, text, mood_tag, word_count),
        )

    # Sync tags: delete old, insert new
    query("DELETE FROM diary_tags WHERE entry_id = %s", (entry_id,))
    for tag in (tags or []):
        query("INSERT INTO diary_tags (entry_id, tag) VALUES (%s, %s)",
              (entry_id, tag))

    # Sync photos: delete old, insert new
    query("DELETE FROM diary_photos WHERE entry_id = %s", (entry_id,))
    for photo_url in (photos or []):
        fname = photo_url.rsplit("/", 1)[-1] if "/" in photo_url else photo_url
        query("INSERT INTO diary_photos (entry_id, filename, url) VALUES (%s, %s, %s)",
              (entry_id, fname, photo_url))

    return get_diary_entry(uid, date_key)


def delete_diary_entry(uid: int, date_key: str):
    """Delete a diary entry (cascades to tags and photos)."""
    query(
        "DELETE FROM journal_entries WHERE user_id = %s AND entry_date = %s",
        (uid, date_key),
    )


# ══════════════════════════════════════════════════════════════
#  CHAT OPERATIONS
# ══════════════════════════════════════════════════════════════

def get_or_create_chat_session(uid: int, session_id: str) -> int:
    """Get or create a chat session. Returns the DB session id (PK)."""
    row = query(
        "SELECT id FROM chat_sessions WHERE user_id = %s AND session_id = %s",
        (uid, session_id), fetchone=True,
    )
    if row:
        query("UPDATE chat_sessions SET updated_at = NOW() WHERE id = %s", (row["id"],))
        return row["id"]
    return query(
        "INSERT INTO chat_sessions (user_id, session_id) VALUES (%s, %s)",
        (uid, session_id),
    )


def save_chat_message(session_pk: int, role: str, content: str):
    query(
        "INSERT INTO chat_messages (session_id, role, content) VALUES (%s, %s, %s)",
        (session_pk, role, content),
    )


def get_chat_history(session_pk: int, limit: int = 20) -> list:
    rows = query(
        """SELECT role, content FROM chat_messages
           WHERE session_id = %s ORDER BY id DESC LIMIT %s""",
        (session_pk, limit), fetchall=True,
    )
    return list(reversed(rows))


# ══════════════════════════════════════════════════════════════
#  ANALYTICS
# ══════════════════════════════════════════════════════════════

def get_analytics(uid: int) -> dict:
    """Compute mood analytics for a user."""
    entries = query(
        """SELECT entry_date, mood_tag, content, word_count, created_at
           FROM journal_entries WHERE user_id = %s ORDER BY entry_date""",
        (uid,), fetchall=True,
    )

    mood_vals = [_mood_tag_to_number(e["mood_tag"]) for e in entries if e.get("mood_tag")]
    mood_vals = [v for v in mood_vals if v is not None]
    avg_mood = round(sum(mood_vals) / len(mood_vals), 2) if mood_vals else None

    dist = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for v in mood_vals:
        if v in dist:
            dist[v] += 1

    # Streak
    streak = 0
    d = date.today()
    date_set = {e["entry_date"] for e in entries if e.get("entry_date")}
    while d in date_set:
        streak += 1
        d = date.fromordinal(d.toordinal() - 1)

    # Tag frequency
    all_tags = query(
        """SELECT dt.tag, COUNT(*) as cnt
           FROM diary_tags dt
           JOIN journal_entries je ON dt.entry_id = je.id
           WHERE je.user_id = %s
           GROUP BY dt.tag ORDER BY cnt DESC""",
        (uid,), fetchall=True,
    )
    tag_freq = {t["tag"]: t["cnt"] for t in all_tags}

    # Mood timeline
    timeline = []
    for e in entries:
        mn = _mood_tag_to_number(e["mood_tag"])
        if mn and e.get("entry_date"):
            timeline.append({"date": e["entry_date"].isoformat(), "mood": mn})

    return {
        "total_entries": len(entries),
        "avg_mood":      avg_mood,
        "mood_dist":     dist,
        "streak":        streak,
        "total_words":   sum(e.get("word_count", 0) for e in entries),
        "tag_freq":      tag_freq,
        "timeline":      timeline,
    }


# ══════════════════════════════════════════════════════════════
#  MOOD MAPPING HELPERS
# ══════════════════════════════════════════════════════════════
# The DiaryApp.jsx uses numeric moods 1-5:
#   1=Joyful, 2=Happy, 3=Calm, 4=Sad, 5=Anxious
# The DB uses mood_tag strings from the mood_entries enum.

_NUM_TO_TAG = {1: "excited", 2: "happy", 3: "calm", 4: "sad", 5: "anxious"}
_TAG_TO_NUM = {v: k for k, v in _NUM_TO_TAG.items()}
# Also handle extra tags from the mood_entries enum
_TAG_TO_NUM.update({
    "grateful": 1, "excited": 1,
    "happy": 2,
    "calm": 3, "neutral": 3,
    "sad": 4, "lonely": 4, "tired": 4,
    "anxious": 5, "stressed": 5, "angry": 5,
})


def _mood_number_to_tag(mood) -> str | None:
    if mood is None:
        return None
    try:
        return _NUM_TO_TAG.get(int(mood))
    except (ValueError, TypeError):
        return str(mood) if mood else None


def _mood_tag_to_number(tag: str) -> int | None:
    if not tag:
        return None
    return _TAG_TO_NUM.get(tag.lower())


def get_user_progress(uid: int) -> dict | None:
    """Get user's full game progress JSON."""
    row = query(
        "SELECT game_progress_json FROM users WHERE id = %s",
        (uid,), fetchone=True
    )
    if row and row["game_progress_json"]:
        try:
            import json
            return json.loads(row["game_progress_json"])
        except Exception:
            return None
    return None


def save_user_progress(uid: int, progress_json: str):
    """Save user's full game progress JSON and update game_progress table."""
    import json
    # 1. Update the users table
    query(
        "UPDATE users SET game_progress_json = %s WHERE id = %s",
        (progress_json, uid)
    )
    
    # 2. Update the game_progress table per game
    try:
        data = json.loads(progress_json)
        games = data.get("games", {})
        for g_id, g_data in games.items():
            times_played = g_data.get("timesPlayed", 0)
            if times_played > 0:
                best_score = g_data.get("bestScore", 0)
                history = g_data.get("history", [])
                last_played_ts = history[0].get("timestamp") if history else None
                last_played_dt = datetime.fromtimestamp(last_played_ts / 1000.0) if last_played_ts else None
                
                # Check if row exists
                existing = query(
                    "SELECT id FROM game_progress WHERE user_id = %s AND game_type = %s",
                    (uid, g_id), fetchone=True
                )
                if existing:
                    query(
                        """UPDATE game_progress 
                           SET sessions = %s, best_score = %s, last_played = %s, updated_at = NOW()
                           WHERE id = %s""",
                        (times_played, best_score, last_played_dt, existing["id"])
                    )
                else:
                    query(
                        """INSERT INTO game_progress (user_id, game_type, sessions, best_score, last_played)
                           VALUES (%s, %s, %s, %s, %s)""",
                        (uid, g_id, times_played, best_score, last_played_dt)
                    )
    except Exception as e:
        print(f"Error updating game_progress details: {e}")


def get_therapists(search_query: str = None, spec_filter: str = None) -> list:
    """Fetch therapists from the database, optionally matching search query and specialization."""
    sql = "SELECT * FROM therapists WHERE 1=1"
    params = []
    
    if search_query:
        sql += " AND (name LIKE %s OR title LIKE %s OR bio LIKE %s OR location LIKE %s)"
        like_pat = f"%{search_query}%"
        params.extend([like_pat, like_pat, like_pat, like_pat])
        
    if spec_filter:
        sql += " AND specialization LIKE %s"
        params.append(f"%{spec_filter}%")
        
    sql += " ORDER BY rating DESC"
    return query(sql, tuple(params), fetchall=True)


def create_appointment(user_id: int, therapist_id: int, app_date: str, app_time: str, notes: str) -> int:
    """Insert a new appointment request."""
    return query(
        """INSERT INTO appointments (user_id, therapist_id, appointment_date, appointment_time, notes, status)
           VALUES (%s, %s, %s, %s, %s, 'Pending')""",
        (user_id, therapist_id, app_date, app_time, notes)
    )


def get_user_appointments(uid: int) -> list:
    """Fetch all appointments for a user, joining with therapist details."""
    rows = query(
        """SELECT a.id, a.appointment_date, a.appointment_time, a.status, a.notes, a.created_at,
                  t.name as therapist_name, t.title as therapist_title, t.photo_url as therapist_photo,
                  t.location as therapist_location, t.contact_email as therapist_email
           FROM appointments a
           JOIN therapists t ON a.therapist_id = t.id
           WHERE a.user_id = %s
           ORDER BY a.appointment_date DESC, a.appointment_time DESC""",
        (uid,), fetchall=True
    )
    # Convert dates to string format for JSON serialization
    for r in rows:
        if r.get("appointment_date"):
            r["appointment_date"] = r["appointment_date"].isoformat()
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def get_therapist_by_user_id(user_id: int) -> dict | None:
    """Get therapist profile linking to a specific user ID."""
    return query(
        "SELECT * FROM therapists WHERE user_id = %s",
        (user_id,), fetchone=True
    )


def save_therapist_profile(user_id: int, name: str, title: str, specialization: str, experience: int, fees: int, location: str, availability: str, contact_email: str, contact_phone: str, bio: str) -> int:
    """Create or update a therapist profile linked to user_id."""
    # Update user's name
    query("UPDATE users SET full_name = %s WHERE id = %s", (name, user_id))
    
    # Check if therapist profile exists
    existing = get_therapist_by_user_id(user_id)
    if existing:
        query(
            """UPDATE therapists
               SET name = %s, title = %s, specialization = %s, experience = %s,
                   fees = %s, location = %s, availability = %s, contact_email = %s,
                   contact_phone = %s, bio = %s
               WHERE id = %s""",
            (name, title, specialization, experience, fees, location, availability,
             contact_email, contact_phone, bio, existing["id"])
        )
        return existing["id"]
    else:
        # Default rating to 5.0 and photo to default avatar for new therapist
        return query(
            """INSERT INTO therapists (user_id, name, title, specialization, experience, rating, fees, location, availability, contact_email, contact_phone, photo_url, bio)
               VALUES (%s, %s, %s, %s, %s, 5.0, %s, %s, %s, %s, %s, '/static/avatars/therapist_default.png', %s)""",
            (user_id, name, title, specialization, experience, fees, location, availability,
             contact_email, contact_phone, bio)
        )


def get_received_appointments(therapist_user_id: int) -> list:
    """Get all appointments booked with this therapist user."""
    therapist = get_therapist_by_user_id(therapist_user_id)
    if not therapist:
        return []
    
    rows = query(
        """SELECT a.id, a.appointment_date, a.appointment_time, a.status, a.notes, a.created_at,
                  u.full_name as patient_name, u.email as patient_email
           FROM appointments a
           JOIN users u ON a.user_id = u.id
           WHERE a.therapist_id = %s
           ORDER BY a.appointment_date DESC, a.appointment_time DESC""",
        (therapist["id"],), fetchall=True
    )
    for r in rows:
        if r.get("appointment_date"):
            r["appointment_date"] = r["appointment_date"].isoformat()
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def update_appointment_status(appointment_id: int, therapist_user_id: int, status: str) -> bool:
    """Update appointment status (Confirm/Cancel) by verifying therapist ownership."""
    therapist = get_therapist_by_user_id(therapist_user_id)
    if not therapist:
        return False
        
    query(
        "UPDATE appointments SET status = %s WHERE id = %s AND therapist_id = %s",
        (status, appointment_id, therapist["id"])
    )
    return True


def save_assessment(user_id: int, test_type: str, score: int, severity: str, answers_json: str) -> int:
    """Save a clinical self-assessment result."""
    return query(
        """INSERT INTO assessments (user_id, type, score, severity, answers)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, test_type, score, severity, answers_json)
    )


def get_user_assessments(user_id: int) -> list:
    """Retrieve all past self-assessments for a user."""
    rows = query(
        """SELECT id, type, score, severity, answers, taken_at
           FROM assessments
           WHERE user_id = %s
           ORDER BY taken_at DESC""",
        (user_id,), fetchall=True
    )
    for r in rows:
        if r.get("taken_at"):
            r["taken_at"] = r["taken_at"].isoformat()
    return rows




