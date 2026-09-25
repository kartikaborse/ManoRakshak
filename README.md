# 🛡️ ManoRakshat (मनोरक्षत्) — AI-Powered Mental Health & Well-being Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python Version](https://img.shields.io/badge/Python-3.9%2B-brightgreen.svg)](https://python.org)
[![Flask Framework](https://img.shields.io/badge/Framework-Flask-black.svg)](https://flask.palletsprojects.org)
[![Status](https://img.shields.io/badge/Status-Active%20Development-success.svg)](#)

> **ManoRakshat** (meaning *"Protection of the Mind"*) is an all-in-one digital mental health platform that bridges compassionate AI support, evidence-based clinical screening, interactive wellness games, voice therapy, and professional therapist connectivity into a unified, secure sanctuary.

---

## 🌟 Key Features

### 🤖 1. Empathetic AI Assistant & RAG Engine
- **Conversational Support:** Instant 24/7 empathetic listening, cognitive reframing suggestions, and coping mechanisms.
- **RAG Architecture & Offline LLM:** Retrieval-Augmented Generation using curated clinical guidelines, backed by a local offline fallback engine when network connectivity is limited.
- **Safety & Crisis Protocols:** Automated detection of crisis keywords with immediate display of helpline numbers and safety resources.

### 📊 2. Clinical Assessment & Screening Suite
- **Validated Tools:** Interactive digital screeners for **PHQ-9** (Depression Severity), **GAD-7** (Anxiety Screening), and **GHQ-12** (General Health Questionnaire).
- **Instant Risk Scoring:** Real-time feedback, longitudinal trend visualization, and automatic recommendations based on assessment results.
- **Clinical Dashboard:** Multi-dimensional charts charting patient well-being over time.

### 🎮 3. Interactive Therapeutic Games
A collection of 7 specially engineered web games built with custom physics and game loops designed to alleviate anxiety, improve focus, and teach mindfulness:
1. **🌸 Cozy Island Garden:** Mood-seed planting and daily emotional garden nurturing.
2. **🫁 Body & Breath Quest:** Interactive guided breathing and somatic grounding exercise.
3. **🧩 Calm Grid Sudoku:** Stress-free, pressureless logic puzzle with soothing visuals.
4. **🎨 Color Your World:** Canvas painting unlocked by positive daily mindfulness check-ins.
5. **🧱 Mood Blocks:** Emotion-colored falling-block puzzle for stress release.
6. **🌌 Spirit Journey:** Atmospheric navigation guiding floating spirits to tranquil waters.
7. **🌊 Stress Relief Ocean:** Interactive ocean wave simulation for instant visual calming.

### 🧑‍⚕️ 4. Therapist Directory & Consultation Portal
- **Verified Directory:** Browse certified psychiatrists, clinical psychologists, and counseling specialists across India.
- **Filtering & Search:** Search by specialization (ADHD, CBT, Trauma, Anxiety, Mood Swings), availability, fee structure, and consultation mode (Online / In-Person).
- **Therapist Portal:** Dedicated dashboard for practitioners to manage appointments, review patient consent logs, and upload consultation notes.

### 🎙️ 5. Voice & Audio Therapy Hub
- **Voice Analysis & Synthesis:** Pitch-shifted audio reflections and custom voice profiles for soothing self-talk.
- **Ambient Soundscapes:** Curated audio therapy including binaural beats, ocean rain, forest ambience, and white noise.
- **Voice Journaling:** Record daily audio reflections with automatic transcription and emotional tone analysis.

### 📖 6. Digital Sanctuary & Mood Diary
- **Lined Paper Aesthetic:** Private journal supporting markdown text, mood ratings (1–5), photo attachments, and custom tags.
- **AI Reflections:** Gentle automated insights identifying emotional patterns over time.
- **Export Capabilities:** One-click PDF report generation containing diary entries, mood charts, and photos.

---

## 🏗️ System Architecture

```
ManoRakshat/
├── backend/                    # Flask Application & Core API Services
│   ├── app.py                  # Primary HTTP router & session coordinator
│   ├── db.py                   # MySQL / SQLite ORM database wrapper
│   ├── offline_llm_engine.py   # Offline inference engine for conversational AI
│   ├── rag_engine.py           # Retrieval-Augmented Generation vector pipeline
│   ├── voice_engine.py         # Voice synthesis & audio signal processing
│   ├── setup_therapists.py     # Initial seed script for verified clinical practitioners
│   └── templates/              # Jinja2 Web UI Templates (Hub, Clinical, Voice, Profile, etc.)
├── chatbot/                    # ML / NLP Chatbot Subsystem
│   ├── chatbot.py              # Natural language classifier & intent router
│   ├── train_model.py          # Intent model training pipeline
│   └── train_recommendation_models.py # Collaborative filtering for therapy recommendations
├── games/                      # HTML5 Canvas / JS Wellness Mini-Games
│   ├── gameEngine.js           # Shared game engine core, storage & frame manager
│   ├── manorakshat_games_hub.html # Interactive Game Launcher
│   └── manorakshat_*.html      # Standalone therapeutic game modules
├── static/                     # Static Web Assets (CSS, JS, Avatars, Audio)
├── import_db.py                # Database Initialization & Schema Migrator
├── manorakshat_db.sql          # Full Database Dump (Schema + Initial Seed Data)
├── DiaryApp.jsx                # Modular React Frontend component for Diary App
└── requirements.txt            # Python Dependencies
```

---

## 🚀 Getting Started

### Prerequisites
- **Python 3.9+**
- **MySQL / MariaDB** (Optional, falls back to SQLite or local database)
- **Node.js 18+** (Optional, only required for React development)

### Installation & Setup

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/kartikaborse/ManoRakshat.git
   cd ManoRakshat
   ```

2. **Create and Activate a Virtual Environment:**
   ```bash
   # Windows
   python -m venv venv
   .\venv\Scripts\activate

   # Linux/macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Initialize the Database:**
   ```bash
   python import_db.py
   python backend/setup_therapists.py
   ```

5. **Launch the Application:**
   ```bash
   python backend/app.py
   ```
   The application will be live at `http://127.0.0.1:5000` (or `http://localhost:5000`).

---

## 📊 Database Schema Summary

The database (`manorakshat_db`) stores user records, clinical assessments, therapist profiles, diary entries, and games metrics:
- **`users`**: Account credentials, preferences, role assignment (patient / therapist / admin).
- **`therapists`**: Clinical credentials, contact details, consultation fees, and location info.
- **`assessments`**: Historical scores for PHQ-9, GAD-7, and GHQ-12 screeners.
- **`diary_entries`**: Text logs, mood ratings (1-5), emotion tags, and photo links.
- **`game_progress`**: High scores, total relaxation minutes, and unlocked garden items.

---

## 🔒 Security & Privacy

- **Data Privacy:** User logs and clinical screeners are encrypted in transit and at rest.
- **Anonymized Analytics:** No personally identifiable information (PII) is exposed to external ML models.
- **Role-Based Access Control (RBAC):** Strict boundaries between patient data and therapist access.

---

## 🤝 Contributing

Contributions are welcome! If you'd like to improve ManoRakshat, please follow these steps:
1. Fork the project repository.
2. Create your feature branch (`git checkout -b feature/AmazingFeature`).
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`).
4. Push to the branch (`git push origin feature/AmazingFeature`).
5. Open a Pull Request.

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<p align="center">Developed with ❤️ to empower mental health and well-being everywhere.</p>
