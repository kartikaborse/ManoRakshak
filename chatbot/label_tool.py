"""
ManoKart  —  Active Learning Labelling Tool
============================================
Web interface to review uncertain chatbot predictions,
assign correct labels, and auto-retrain the model every 10 new labels.

Run:   python3 label_tool.py
Open:  http://localhost:5000
"""

import json, os, subprocess, sys, datetime
from flask import Flask, render_template_string, request, redirect, url_for, jsonify

REVIEW_QUEUE_PATH = "review_queue.json"
DATASET_PATH      = "dataset.json"
MODEL_PATH        = "manokart_model.pkl"
RETRAIN_EVERY     = 10

app = Flask(__name__)

# ── Queue helpers ─────────────────────────────────────────────────────────────
def load_queue():
    if not os.path.exists(REVIEW_QUEUE_PATH):
        return []
    with open(REVIEW_QUEUE_PATH) as f:
        return json.load(f)

def save_queue(q):
    with open(REVIEW_QUEUE_PATH, "w") as f:
        json.dump(q, f, indent=2)

def load_dataset():
    with open(DATASET_PATH) as f:
        return json.load(f)

def save_dataset(d):
    with open(DATASET_PATH, "w") as f:
        json.dump(d, f, indent=2)

def count_labeled(q):
    return sum(1 for i in q if i["labeled"])

def count_unlabeled(q):
    return sum(1 for i in q if not i["labeled"])

def add_to_dataset(text, tag):
    """Add a newly labeled pattern into the correct intent in dataset.json."""
    d = load_dataset()
    for intent in d["intents"]:
        if intent["tag"] == tag:
            if text not in intent["patterns"]:
                intent["patterns"].append(text)
            break
    else:
        # Tag doesn't exist yet — create it
        d["intents"].append({
            "tag": tag,
            "patterns": [text],
            "responses": [f"I hear you regarding {tag}. Can you tell me more?"]
        })
    save_dataset(d)

def trigger_retrain():
    """Run train_model.py as subprocess."""
    result = subprocess.run(
        [sys.executable, "train_model.py"],
        capture_output=True, text=True
    )
    return result.stdout + result.stderr

def get_all_tags():
    d = load_dataset()
    return sorted(i["tag"] for i in d["intents"])

# ── HTML template ─────────────────────────────────────────────────────────────
HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>ManoKart — Label Tool</title>
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

  :root {
    --teal:       #1D9E75;
    --teal-light: #E1F5EE;
    --teal-dark:  #0F6E56;
    --amber:      #d97706;
    --amber-bg:   #fffbeb;
    --red:        #dc2626;
    --red-bg:     #fef2f2;
    --gray:       #6b7280;
    --gray-light: #f9fafb;
    --border:     #e5e7eb;
    --text:       #111827;
    --text-muted: #6b7280;
    --radius:     10px;
    --shadow:     0 1px 3px rgba(0,0,0,0.08);
  }

  body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
    background: #f3f4f6;
    color: var(--text);
    min-height: 100vh;
    padding: 0 0 60px;
  }

  /* ── Header ── */
  header {
    background: white;
    border-bottom: 1px solid var(--border);
    padding: 16px 32px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    position: sticky; top: 0; z-index: 10;
  }
  .logo { display: flex; align-items: center; gap: 10px; }
  .logo-dot {
    width: 32px; height: 32px; border-radius: 50%;
    background: var(--teal); display: flex; align-items: center;
    justify-content: center; color: white; font-size: 16px; font-weight: 700;
  }
  .logo-name { font-size: 18px; font-weight: 600; color: var(--text); }
  .logo-sub  { font-size: 13px; color: var(--text-muted); margin-left: 4px; }

  .stats-bar { display: flex; gap: 20px; }
  .stat { text-align: center; }
  .stat-num  { font-size: 20px; font-weight: 700; color: var(--teal); }
  .stat-label{ font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: .05em; }

  /* ── Main layout ── */
  main { max-width: 820px; margin: 32px auto; padding: 0 20px; }

  /* ── Progress ── */
  .progress-section { margin-bottom: 28px; }
  .progress-header  { display: flex; justify-content: space-between; margin-bottom: 8px; font-size: 14px; color: var(--text-muted); }
  .progress-bar { height: 8px; background: var(--border); border-radius: 99px; overflow: hidden; }
  .progress-fill { height: 100%; background: var(--teal); border-radius: 99px; transition: width .4s; }

  /* ── Retrain banner ── */
  .retrain-banner {
    background: var(--teal-light); border: 1px solid var(--teal);
    border-radius: var(--radius); padding: 14px 20px;
    display: flex; align-items: center; justify-content: space-between;
    margin-bottom: 24px; gap: 16px;
  }
  .retrain-banner p { font-size: 14px; color: var(--teal-dark); font-weight: 500; }
  .retrain-banner small { font-size: 12px; color: var(--teal); display: block; margin-top: 2px; }

  /* ── Card ── */
  .card {
    background: white; border: 1px solid var(--border);
    border-radius: var(--radius); padding: 24px;
    margin-bottom: 20px; box-shadow: var(--shadow);
  }

  /* ── Pending item ── */
  .item-header { display: flex; align-items: flex-start; gap: 14px; margin-bottom: 16px; }
  .item-id { font-size: 12px; color: var(--text-muted); background: var(--gray-light); padding: 3px 8px; border-radius: 6px; white-space: nowrap; }
  .item-text { font-size: 16px; font-weight: 500; line-height: 1.5; }
  .item-meta { font-size: 13px; color: var(--text-muted); margin-bottom: 16px; display: flex; gap: 16px; flex-wrap: wrap; }
  .badge { padding: 3px 10px; border-radius: 99px; font-size: 12px; font-weight: 500; }
  .badge-amber { background: var(--amber-bg); color: var(--amber); }
  .badge-teal  { background: var(--teal-light); color: var(--teal-dark); }
  .badge-red   { background: var(--red-bg); color: var(--red); }

  /* ── Label form ── */
  .label-form { display: flex; gap: 10px; flex-wrap: wrap; align-items: center; }
  .label-form select {
    flex: 1; min-width: 200px;
    padding: 9px 14px; border: 1px solid var(--border);
    border-radius: 8px; font-size: 14px; color: var(--text);
    background: white; outline: none; cursor: pointer;
  }
  .label-form select:focus { border-color: var(--teal); }

  .btn {
    padding: 9px 20px; border-radius: 8px; font-size: 14px;
    font-weight: 500; cursor: pointer; border: none; transition: all .15s;
  }
  .btn-primary { background: var(--teal); color: white; }
  .btn-primary:hover { background: var(--teal-dark); }
  .btn-danger  { background: var(--red-bg); color: var(--red); border: 1px solid #fecaca; }
  .btn-danger:hover { background: #fee2e2; }
  .btn-gray    { background: var(--gray-light); color: var(--text-muted); border: 1px solid var(--border); }
  .btn-gray:hover { background: var(--border); }

  .divider { border: none; border-top: 1px solid var(--border); margin: 16px 0; }

  /* ── Done state ── */
  .all-done {
    text-align: center; padding: 60px 20px;
  }
  .all-done .icon { font-size: 48px; margin-bottom: 16px; }
  .all-done h2 { font-size: 22px; font-weight: 600; margin-bottom: 8px; }
  .all-done p  { color: var(--text-muted); font-size: 15px; }

  /* ── History ── */
  .history-toggle { font-size: 13px; color: var(--teal); cursor: pointer; text-decoration: underline; margin-bottom: 16px; display: inline-block; }
  .history-table { width: 100%; border-collapse: collapse; font-size: 13px; }
  .history-table th { text-align: left; color: var(--text-muted); font-weight: 500; padding: 8px 12px; border-bottom: 1px solid var(--border); }
  .history-table td { padding: 8px 12px; border-bottom: 1px solid var(--border); }
  .history-table tr:last-child td { border-bottom: none; }

  /* ── Retrain log ── */
  .log-box {
    background: #0f172a; color: #86efac; font-family: monospace;
    font-size: 12px; padding: 16px; border-radius: 8px;
    max-height: 300px; overflow-y: auto; white-space: pre-wrap;
    margin-top: 16px;
  }

  .empty-state { text-align: center; padding: 40px; color: var(--text-muted); font-size: 15px; }
</style>
</head>
<body>

<header>
  <div class="logo">
    <div class="logo-dot">M</div>
    <div>
      <span class="logo-name">ManoKart</span>
      <span class="logo-sub">Active Learning — Label Tool</span>
    </div>
  </div>
  <div class="stats-bar">
    <div class="stat">
      <div class="stat-num">{{ total }}</div>
      <div class="stat-label">Total logged</div>
    </div>
    <div class="stat">
      <div class="stat-num">{{ labeled }}</div>
      <div class="stat-label">Labeled</div>
    </div>
    <div class="stat">
      <div class="stat-num">{{ unlabeled }}</div>
      <div class="stat-label">Pending</div>
    </div>
    <div class="stat">
      <div class="stat-num">{{ retrains }}</div>
      <div class="stat-label">Retrains done</div>
    </div>
  </div>
</header>

<main>

  <!-- Progress bar -->
  {% if total > 0 %}
  <div class="progress-section">
    <div class="progress-header">
      <span>Labelling progress</span>
      <span>{{ labeled }} / {{ total }}</span>
    </div>
    <div class="progress-bar">
      <div class="progress-fill" style="width: {{ (labeled / total * 100)|int }}%"></div>
    </div>
  </div>
  {% endif %}

  <!-- Retrain ready banner -->
  {% if retrain_ready %}
  <div class="retrain-banner">
    <div>
      <p>⚡ {{ retrain_count }} new labels ready — retraining the model now will improve accuracy.</p>
      <small>Model accuracy increases as more real user messages are labeled and added to training data.</small>
    </div>
    <form method="POST" action="/retrain">
      <button class="btn btn-primary" type="submit">Retrain Now</button>
    </form>
  </div>
  {% endif %}

  <!-- Retrain log -->
  {% if retrain_log %}
  <div class="card">
    <h3 style="font-size:15px; font-weight:600; margin-bottom:12px;">✅ Retraining Complete</h3>
    <p style="font-size:13px; color:#6b7280; margin-bottom:4px;">The model has been updated with your new labels. Accuracy should improve.</p>
    <div class="log-box">{{ retrain_log }}</div>
  </div>
  {% endif %}

  <!-- Pending items -->
  {% if pending %}
  <div class="card">
    <h2 style="font-size:17px; font-weight:600; margin-bottom:4px;">Review Queue</h2>
    <p style="font-size:13px; color:#6b7280; margin-bottom:20px;">
      These messages had confidence below 70%. Assign the correct intent so the model learns.
    </p>

    {% for item in pending %}
    <div style="{% if not loop.first %}border-top: 1px solid #f3f4f6; padding-top: 20px; margin-top: 20px;{% endif %}">
      <div class="item-header">
        <span class="item-id">#{{ item.id }}</span>
        <span class="item-text">"{{ item.text }}"</span>
      </div>
      <div class="item-meta">
        <span>
          Model guessed:
          <span class="badge badge-amber">{{ item.predicted_tag }}</span>
        </span>
        <span>
          Confidence:
          <span class="badge badge-red">{{ (item.confidence * 100)|round(1) }}%</span>
        </span>
        <span style="color:#9ca3af;">{{ item.timestamp }}</span>
      </div>

      <form method="POST" action="/label" style="display:flex; gap:10px; flex-wrap:wrap; align-items:center;">
        <input type="hidden" name="item_id" value="{{ item.id }}">
        <select name="correct_tag" required>
          <option value="" disabled selected>— Select correct intent —</option>
          {% for tag in all_tags %}
          <option value="{{ tag }}" {% if tag == item.predicted_tag %}selected{% endif %}>{{ tag }}</option>
          {% endfor %}
          <option value="__skip__">Skip this one</option>
        </select>
        <button class="btn btn-primary" type="submit">Save Label</button>
        <button class="btn btn-danger" type="submit" name="correct_tag" value="__discard__">Discard</button>
      </form>
    </div>
    {% endfor %}
  </div>

  {% elif not retrain_log %}
  <div class="card all-done">
    <div class="icon">✅</div>
    <h2>All caught up!</h2>
    <p>No pending messages to review right now.<br>Keep chatting and uncertain messages will appear here.</p>
  </div>
  {% endif %}

  <!-- Labeled history -->
  {% if history %}
  <div class="card">
    <h3 style="font-size:15px; font-weight:600; margin-bottom:12px;">Labeled History ({{ history|length }})</h3>
    <table class="history-table">
      <thead>
        <tr>
          <th>#</th>
          <th>Message</th>
          <th>Predicted</th>
          <th>Corrected to</th>
          <th>Conf.</th>
        </tr>
      </thead>
      <tbody>
        {% for item in history %}
        <tr>
          <td style="color:#9ca3af;">{{ item.id }}</td>
          <td>{{ item.text }}</td>
          <td><span class="badge badge-amber">{{ item.predicted_tag }}</span></td>
          <td><span class="badge badge-teal">{{ item.correct_tag }}</span></td>
          <td style="color:#9ca3af;">{{ (item.confidence * 100)|round(1) }}%</td>
        </tr>
        {% endfor %}
      </tbody>
    </table>
  </div>
  {% endif %}

</main>
</body>
</html>
"""

# ── State ─────────────────────────────────────────────────────────────────────
retrain_log    = None
retrain_count  = 0    # labels added since last retrain

@app.route("/")
def index():
    global retrain_log, retrain_count
    q         = load_queue()
    pending   = [i for i in q if not i["labeled"]]
    history   = [i for i in q if i["labeled"] and i["correct_tag"] not in ("__skip__", "__discard__")]
    labeled   = count_labeled(q)
    unlabeled = count_unlabeled(q)

    # Count how many retrains have happened (stored in a simple file)
    retrains = 0
    if os.path.exists(".retrain_count"):
        with open(".retrain_count") as f:
            retrains = int(f.read().strip() or 0)

    retrain_ready  = retrain_count >= RETRAIN_EVERY
    log            = retrain_log
    retrain_log    = None  # clear after showing once

    return render_template_string(HTML,
        pending       = pending,
        history       = history,
        all_tags      = get_all_tags(),
        total         = len(q),
        labeled       = labeled,
        unlabeled     = unlabeled,
        retrains      = retrains,
        retrain_ready = retrain_ready,
        retrain_count = retrain_count,
        retrain_log   = log,
    )


@app.route("/label", methods=["POST"])
def label():
    global retrain_count
    item_id     = int(request.form["item_id"])
    correct_tag = request.form["correct_tag"]
    q           = load_queue()

    for item in q:
        if item["id"] == item_id:
            item["labeled"]     = True
            item["correct_tag"] = correct_tag
            item["labeled_at"]  = datetime.datetime.now().isoformat(timespec="seconds")

            if correct_tag not in ("__skip__", "__discard__"):
                add_to_dataset(item["text"], correct_tag)
                retrain_count += 1

            break

    save_queue(q)

    # Auto-retrain when threshold reached
    if retrain_count >= RETRAIN_EVERY:
        _do_retrain()

    return redirect(url_for("index"))


@app.route("/retrain", methods=["POST"])
def retrain():
    _do_retrain()
    return redirect(url_for("index"))


def _do_retrain():
    global retrain_log, retrain_count
    print("\n[label_tool] Auto-retraining model...")
    retrain_log   = trigger_retrain()
    retrain_count = 0   # reset counter

    # Increment saved retrain count
    count = 0
    if os.path.exists(".retrain_count"):
        with open(".retrain_count") as f:
            count = int(f.read().strip() or 0)
    with open(".retrain_count", "w") as f:
        f.write(str(count + 1))

    print("[label_tool] Retraining complete.\n")


# ── Run ───────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("\n  ManoKart Label Tool")
    print("  Open in browser:  http://localhost:5000\n")
    app.run(debug=False, port=5000)
