# 🌿 My Little Sanctuary — Mental Health Diary

A calming diary app with mood tracking, photo uploads, tags, AI reflections, and PDF export.

## Project Structure

```
diary_app/
├── app.py              ← Flask backend (this is your Python server)
├── requirements.txt    ← Python dependencies
├── data/
│   └── diary.json      ← All diary entries (auto-created)
├── uploads/            ← Uploaded photos (auto-created)
├── static/             ← Place your React build here (index.html, etc.)
└── DiaryApp.jsx        ← React frontend source
```

---


## React Frontend

The `DiaryApp.jsx` is a React component. To use it in your project:

### Option A — Standalone Vite/CRA project
```bash
npm create vite@latest diary-frontend -- --template react
cd diary-frontend
# Copy DiaryApp.jsx into src/
# Replace src/App.jsx content with:
#   import DiaryApp from './DiaryApp'; export default function App(){ return <DiaryApp/>; }
npm run dev
```

### Option B — Integrate into your existing React app
Just import and render `<DiaryApp />` wherever you want the diary to appear.

### Option C — Serve from Flask (production)
Build your React app (`npm run build`) and copy the `dist/` contents into `static/`. Flask will serve them automatically.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/api/entries` | Get all diary entries |
| GET | `/api/entries/:date` | Get a single entry (date = YYYY-MM-DD) |
| POST | `/api/entries/:date` | Save/update an entry |
| DELETE | `/api/entries/:date` | Delete an entry |
| POST | `/api/upload` | Upload a photo (multipart/form-data, field: `file`) |
| GET | `/api/photos/:filename` | Serve an uploaded photo |
| POST | `/api/analyze` | AI mood analysis (needs ANTHROPIC_API_KEY) |
| GET | `/api/analytics` | Mood stats, streaks, tag frequency |
| GET | `/api/export/pdf` | Download full diary as PDF |

### Entry format (JSON)
```json
{
  "date": "2024-05-14",
  "text": "Today was a gentle day...",
  "mood": 3,
  "tags": ["gratitude", "nature"],
  "photos": ["/api/photos/abc123.jpg"],
  "created": "2024-05-14T10:30:00",
  "updated": "2024-05-14T10:45:00"
}
```

### Mood values
| Value | Label |
|-------|-------|
| 5 | Joyful ☀️ |
| 4 | Happy 🌸 |
| 3 | Calm 🌿 |
| 2 | Sad 🌧️ |
| 1 | Anxious 🌪️ |

---

## Features
- ✍️ Daily diary writing with lined paper aesthetic
- 😊 5-level mood tracker with color-coded pills
- 🏷️ Custom + suggested tags with frequency analytics
- 📷 Photo attachments (upload + preview, up to 3 per PDF page)
- 🤖 AI-powered gentle reflection (via Anthropic Claude)
- 📊 Mood charts, streaks, distribution, top tags
- 📄 Full PDF export with photos and formatting
- 💾 Server-side persistence in JSON (swap to SQLite/Postgres easily)
- 🔄 Graceful offline fallback to localStorage

---

## Upgrading to a Real Database

Replace the `load_data()` / `save_data()` helpers in `app.py` with SQLite:

```python
import sqlite3

def get_db():
    db = sqlite3.connect("data/diary.db")
    db.row_factory = sqlite3.Row
    return db
```

The rest of the API stays the same.
