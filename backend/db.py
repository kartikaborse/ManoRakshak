"""
ManoRakshak.AI — MySQL Database Helpers
─────────────────────────────────
Connects to XAMPP's MariaDB (manorakshak_db) and provides
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
    "database": os.environ.get("DB_NAME", "manorakshak_db"),
    "port":     int(os.environ.get("DB_PORT", "3306")),
    "charset":  "utf8mb4",
    "collation": "utf8mb4_unicode_ci",
    "autocommit": True,
}


def get_pool():
    global _pool
    if _pool is None:
        _pool = pooling.MySQLConnectionPool(
            pool_name="manorakshak_pool",
            pool_size=5,
            pool_reset_session=True,
            **DB_CONFIG,
        )
        ensure_victim_tables()
    return _pool


def ensure_victim_tables():
    """Ensure all Version 2 Victim Protection & Distress System tables exist."""
    try:
        conn = get_pool().get_connection()
        cur = conn.cursor()
        cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_profiles (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL UNIQUE,
            case_number VARCHAR(100) NOT NULL UNIQUE,
            category VARCHAR(150) NOT NULL,
            judicial_stage VARCHAR(100) DEFAULT 'Investigation',
            counselor_id INT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY (counselor_id) REFERENCES therapists(id) ON DELETE SET NULL
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_distress_scores (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            score FLOAT NOT NULL,
            sentiment_score FLOAT DEFAULT NULL,
            vocal_stress FLOAT DEFAULT NULL,
            assessment_score INT DEFAULT NULL,
            details_json TEXT DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_alerts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            score FLOAT NOT NULL,
            reason TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'Active',
            resolution_notes TEXT DEFAULT NULL,
            resolved_by INT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            resolved_at DATETIME NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_vault_incidents (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            incident_type VARCHAR(100) NOT NULL,
            description TEXT NOT NULL,
            evidence_file_path VARCHAR(255) DEFAULT NULL,
            threat_severity VARCHAR(20) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_sos_alerts (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            latitude VARCHAR(50) NOT NULL,
            longitude VARCHAR(50) NOT NULL,
            status VARCHAR(50) DEFAULT 'Active',
            dispatched_officer VARCHAR(150) DEFAULT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        cur.execute("""
        CREATE TABLE IF NOT EXISTS victim_compensation_claims (
            id INT AUTO_INCREMENT PRIMARY KEY,
            user_id INT NOT NULL,
            case_number VARCHAR(100) NOT NULL,
            amount_entitled FLOAT NOT NULL,
            stage VARCHAR(100) NOT NULL,
            status VARCHAR(50) DEFAULT 'Pending Officer Review',
            petition_text TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        print(f"Warning: ensure_victim_tables encountered error: {e}")


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


# ══════════════════════════════════════════════════════════════
#  VERSION 2 — VICTIM MONITORING & DISTRESS SYSTEM CRUD
# ══════════════════════════════════════════════════════════════

def get_victim_profile(user_id: int) -> dict | None:
    """Fetch the victim case profile for a user."""
    return query(
        "SELECT * FROM victim_profiles WHERE user_id = %s",
        (user_id,), fetchone=True
    )


def create_victim_profile(user_id: int, case_number: str, category: str, judicial_stage: str = 'Investigation', counselor_id: int = None) -> dict | None:
    """Create a new victim case profile."""
    query(
        """INSERT INTO victim_profiles (user_id, case_number, category, judicial_stage, counselor_id)
           VALUES (%s, %s, %s, %s, %s)
           ON DUPLICATE KEY UPDATE case_number=%s, category=%s, judicial_stage=%s, counselor_id=%s""",
        (user_id, case_number, category, judicial_stage, counselor_id, case_number, category, judicial_stage, counselor_id)
    )
    return get_victim_profile(user_id)


def update_victim_profile_stage(user_id: int, judicial_stage: str):
    """Update a victim's current judicial/rehabilitation stage."""
    query(
        "UPDATE victim_profiles SET judicial_stage = %s WHERE user_id = %s",
        (judicial_stage, user_id)
    )


def save_victim_distress_score(user_id: int, score: float, sentiment_score: float = None, vocal_stress: float = None, assessment_score: int = None, details_json: str = None) -> int:
    """Save a computed Dynamic Distress Score (DDS)."""
    return query(
        """INSERT INTO victim_distress_scores (user_id, score, sentiment_score, vocal_stress, assessment_score, details_json)
           VALUES (%s, %s, %s, %s, %s, %s)""",
        (user_id, score, sentiment_score, vocal_stress, assessment_score, details_json)
    )


def get_victim_distress_history(user_id: int) -> list:
    """Fetch longitudinal distress scores for a victim."""
    rows = query(
        """SELECT id, score, sentiment_score, vocal_stress, assessment_score, details_json, created_at
           FROM victim_distress_scores
           WHERE user_id = %s
           ORDER BY created_at ASC""",
        (user_id,), fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def trigger_victim_alert(user_id: int, score: float, reason: str) -> int:
    """Insert an active critical distress/crisis alert for a user."""
    # Check if there is already an active alert for this user with similar score to avoid redundancy
    existing = query(
        "SELECT id FROM victim_alerts WHERE user_id = %s AND status = 'Active'",
        (user_id,), fetchone=True
    )
    if existing:
        return existing["id"]
        
    return query(
        """INSERT INTO victim_alerts (user_id, score, reason, status)
           VALUES (%s, %s, %s, 'Active')""",
        (user_id, score, reason)
    )


def get_active_alerts() -> list:
    """Fetch all active alerts joined with victim and counselor details."""
    rows = query(
        """SELECT va.id, va.user_id, va.score, va.reason, va.status, va.created_at,
                  u.full_name as victim_name, u.email as victim_email,
                  vp.case_number, vp.category, vp.judicial_stage, vp.counselor_id,
                  t.name as counselor_name
           FROM victim_alerts va
           JOIN users u ON va.user_id = u.id
           JOIN victim_profiles vp ON u.id = vp.user_id
           LEFT JOIN therapists t ON vp.counselor_id = t.id
           WHERE va.status = 'Active'
           ORDER BY va.created_at DESC""",
        fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def resolve_alert(alert_id: int, resolved_by_user_id: int, notes: str) -> bool:
    """Resolve an active alert."""
    query(
        """UPDATE victim_alerts
           SET status = 'Resolved', resolution_notes = %s, resolved_by = %s,
               resolved_at = NOW()
           WHERE id = %s""",
        (notes, resolved_by_user_id, alert_id)
    )
    return True


def get_supervised_victims(counselor_user_id: int) -> list:
    """Fetch all victims assigned to a counselor (therapist user)."""
    therapist = get_therapist_by_user_id(counselor_user_id)
    if not therapist:
        return []
        
    rows = query(
        """SELECT vp.id, vp.user_id, vp.case_number, vp.category, vp.judicial_stage, vp.created_at,
                  u.full_name as victim_name, u.email as victim_email, u.username as victim_username
           FROM victim_profiles vp
           JOIN users u ON vp.user_id = u.id
           WHERE vp.counselor_id = %s
           ORDER BY u.full_name ASC""",
        (therapist["id"],), fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def get_all_victims_for_admin() -> list:
    """Fetch all victims for state/district admin monitoring."""
    rows = query(
        """SELECT vp.id, vp.user_id, vp.case_number, vp.category, vp.judicial_stage, vp.created_at,
                  u.full_name as victim_name, u.email as victim_email, u.username as victim_username,
                  t.name as counselor_name
           FROM victim_profiles vp
           JOIN users u ON vp.user_id = u.id
           LEFT JOIN therapists t ON vp.counselor_id = t.id
           ORDER BY vp.created_at DESC""",
        fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def log_vault_incident(user_id: int, incident_type: str, description: str, evidence_file_path: str, threat_severity: str) -> int:
    """Log an incident of threat or intimidation in the witness protection vault."""
    return query(
        """INSERT INTO victim_vault_incidents (user_id, incident_type, description, evidence_file_path, threat_severity)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, incident_type, description, evidence_file_path, threat_severity)
    )


def get_vault_incidents(user_id: int) -> list:
    """Retrieve all logged vault incidents for a specific victim."""
    rows = query(
        """SELECT id, incident_type, description, evidence_file_path, threat_severity, created_at
           FROM victim_vault_incidents
           WHERE user_id = %s
           ORDER BY created_at DESC""",
        (user_id,),
        fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def log_sos_alert(user_id: int, latitude: str, longitude: str) -> int:
    """Log a new active SOS alert with Geolocation coordinates."""
    return query(
        """INSERT INTO victim_sos_alerts (user_id, latitude, longitude)
           VALUES (%s, %s, %s)""",
        (user_id, latitude, longitude)
    )


def get_active_sos_alerts() -> list:
    """Fetch all active SOS signals with victim names and details."""
    rows = query(
        """SELECT vsa.id, vsa.user_id, vsa.latitude, vsa.longitude, vsa.status, vsa.dispatched_officer, vsa.created_at,
                  u.full_name as victim_name, u.username as victim_username
           FROM victim_sos_alerts vsa
           JOIN users u ON vsa.user_id = u.id
           WHERE vsa.status = 'Active'
           ORDER BY vsa.created_at DESC""",
        fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def dispatch_officer_to_sos(sos_id: int, officer_name: str) -> int:
    """Update SOS alert status and record dispatched officer."""
    return query(
        """UPDATE victim_sos_alerts
           SET status = 'Dispatched', dispatched_officer = %s
           WHERE id = %s""",
        (officer_name, sos_id)
    )


def submit_compensation_claim(user_id: int, case_number: str, amount_entitled: float, stage: str, petition_text: str) -> int:
    """Submit a statutory compensation relief claim petition."""
    return query(
        """INSERT INTO victim_compensation_claims (user_id, case_number, amount_entitled, stage, petition_text)
           VALUES (%s, %s, %s, %s, %s)""",
        (user_id, case_number, amount_entitled, stage, petition_text)
    )


def get_victim_claims(user_id: int) -> list:
    """Retrieve all claims submitted by a specific victim."""
    rows = query(
        """SELECT id, case_number, amount_entitled, stage, status, petition_text, created_at
           FROM victim_compensation_claims
           WHERE user_id = %s
           ORDER BY created_at DESC""",
        (user_id,),
        fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def get_all_pending_claims() -> list:
    """Fetch all pending relief claims for counselor/admin review."""
    rows = query(
        """SELECT cc.id, cc.user_id, cc.case_number, cc.amount_entitled, cc.stage, cc.status, cc.petition_text, cc.created_at,
                  u.full_name as victim_name
           FROM victim_compensation_claims cc
           JOIN users u ON cc.user_id = u.id
           ORDER BY cc.created_at DESC""",
        fetchall=True
    )
    for r in rows:
        if r.get("created_at"):
            r["created_at"] = r["created_at"].isoformat()
    return rows


def update_claim_status(claim_id: int, status: str) -> int:
    """Approve, reject, or disburse a compensation claim."""
    return query(
        """UPDATE victim_compensation_claims
           SET status = %s
           WHERE id = %s""",
        (status, claim_id)
    )


def get_silent_period_victims(hours: int = 48) -> list:
    """Fetch victims who have been silent / non-responsive for over specified hours."""
    rows = query(
        """SELECT vp.user_id, vp.case_number, vp.category, vp.judicial_stage,
                  u.full_name as victim_name, u.email as victim_email,
                  MAX(vds.created_at) as last_checkin
           FROM victim_profiles vp
           JOIN users u ON vp.user_id = u.id
           LEFT JOIN victim_distress_scores vds ON vp.user_id = vds.user_id
           GROUP BY vp.user_id, vp.case_number, vp.category, vp.judicial_stage, u.full_name, u.email
           HAVING last_checkin IS NULL OR TIMESTAMPDIFF(HOUR, last_checkin, NOW()) >= %s
           ORDER BY last_checkin ASC""",
        (hours,), fetchall=True
    )
    for r in rows:
        if r.get("last_checkin"):
            r["last_checkin"] = r["last_checkin"].isoformat()
        else:
            r["last_checkin"] = "Never Checked In"
    return rows


def get_xai_explanation(score_id: int, user_id: int = None) -> dict | None:
    """
    Generate Explainable AI (XAI / SHAP style) feature importance breakdown
    for a specific Dynamic Distress Score (DDS) entry.
    """
    if score_id <= 0 and user_id:
        row = query(
            """SELECT vds.*, u.full_name as victim_name, vp.case_number, vp.judicial_stage, vp.category
               FROM victim_distress_scores vds
               JOIN users u ON vds.user_id = u.id
               LEFT JOIN victim_profiles vp ON vds.user_id = vp.user_id
               WHERE vds.user_id = %s
               ORDER BY vds.created_at DESC LIMIT 1""",
            (user_id,), fetchone=True
        )
    else:
        row = query(
            """SELECT vds.*, u.full_name as victim_name, vp.case_number, vp.judicial_stage, vp.category
               FROM victim_distress_scores vds
               JOIN users u ON vds.user_id = u.id
               LEFT JOIN victim_profiles vp ON vds.user_id = vp.user_id
               WHERE vds.id = %s""",
            (score_id,), fetchone=True
        )
    if not row:
        return None

    import json
    details = {}
    if row.get("details_json"):
        try:
            details = json.loads(row["details_json"])
        except Exception:
            pass

    score = float(row["score"])
    sentiment_distress = float(row.get("sentiment_score") or 0.40)
    vocal_stress = float(row.get("vocal_stress") or 0.0)
    assessment_score = row.get("assessment_score")
    stage = row.get("judicial_stage", "Investigation")

    text_weight = sentiment_distress * 40.0
    vocal_weight = vocal_stress * 40.0
    clinical_weight = ((assessment_score / 21.0) * 20.0) if assessment_score is not None else 10.0
    delay_weight = 10.0 if stage in ("Trial", "Investigation") else 5.0

    total_raw = max(1.0, text_weight + vocal_weight + clinical_weight + delay_weight)

    feature_contributions = [
        {
            "feature": "NLP Text Sentiment Distress",
            "weight_pct": round((text_weight / total_raw) * 100, 1),
            "score_impact": round(text_weight, 1),
            "description": f"Sentiment tag '{details.get('text_sentiment_tag', 'neutral')}' with distress score {round(sentiment_distress*100)}%"
        },
        {
            "feature": "Voice Acoustic Stress (VSA)",
            "weight_pct": round((vocal_weight / total_raw) * 100, 1),
            "score_impact": round(vocal_weight, 1),
            "description": f"Acoustic pitch tremor & speaking rate stress level {round(vocal_stress*100)}%"
        },
        {
            "feature": "Clinical Self-Assessment (GAD-7/PHQ-9)",
            "weight_pct": round((clinical_weight / total_raw) * 100, 1),
            "score_impact": round(clinical_weight, 1),
            "description": f"Clinical assessment score: {assessment_score if assessment_score is not None else 'N/A'}"
        },
        {
            "feature": "Judicial Trial Delay Vulnerability",
            "weight_pct": round((delay_weight / total_raw) * 100, 1),
            "score_impact": round(delay_weight, 1),
            "description": f"Vulnerability weight associated with stage '{stage}'"
        }
    ]

    return {
        "score_id": score_id,
        "overall_dds": score,
        "victim_name": row["victim_name"],
        "case_number": row.get("case_number"),
        "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
        "feature_contributions": feature_contributions,
        "details": details
    }






