"""
ManoKart Counsellor Chatbot  —  with Active Learning
======================================================
FIXES in this version:
  - CONFIDENCE_THRESHOLD lowered from 0.70 → 0.45
    (0.70 was the primary bug: almost every real input fell below it and got
     the "I want to make sure I understand you" fallback instead of an answer)
  - Negation guard expanded: covers more patterns (not anxious, no i am fine, etc.)
  - Greeting guard expanded to handle more "I'm okay" / "I'm fine" inputs
  - predict() handles both 'ensemble' (new) and 'pipeline' (old) bundle keys
  - preprocess() defined here so pickle.load() always finds it
  - Diary / game features, active learning queue, debug mode all preserved

Run:  python chatbot/chatbot.py
Run with debug info:  python chatbot/chatbot.py --debug
"""

import pickle, random, os, sys, json, textwrap, datetime, re
import numpy as np

SCRIPT_DIR           = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH           = os.path.join(SCRIPT_DIR, "manokart_model.pkl")
REVIEW_QUEUE_PATH    = os.path.join(SCRIPT_DIR, "review_queue.json")

# ── FIX: Was 0.70 — this caused EVERY ambiguous input (including real questions
#    like "tell me what to do when I fight with someone") to hit the fallback.
#    0.45 matches the train_model default of 0.35 + a small web-UI buffer.
CONFIDENCE_THRESHOLD = 0.35

RETRAIN_EVERY        = 10

CRISIS_TAGS    = {"suicidal", "self_harm"}
CRISIS_MESSAGE = (
    "\n  *** IMPORTANT SAFETY NOTICE ***\n"
    "  If you are in crisis, please reach out immediately:\n"
    "  - iCALL (India):          9152987821\n"
    "  - Vandrevala Foundation:  1860-2662-345  (24/7)\n"
    "  - NIMHANS Helpline:       080-46110007\n"
    "  - Emergency:              112\n"
)

def _c(code, t): return f"\033[{code}m{t}\033[0m"
def teal(t):   return _c("36", t)
def bold(t):   return _c("1",  t)
def dim(t):    return _c("2",  t)
def red(t):    return _c("31", t)
def green(t):  return _c("32", t)
def yellow(t): return _c("33", t)

def wrap(text, w=70, indent="  "):
    out = []
    for para in text.split("\n"):
        if not para.strip():
            out.append("")
        else:
            out.append(indent + textwrap.fill(para, width=w,
                        subsequent_indent=indent).lstrip())
    return "\n".join(out)


# ═══════════════════════════════════════════════════════════════════
#  preprocess() must live here so pickle.load() can find it
# ═══════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════
#  Custom unpickler — redirects preprocess references from train_model
#  to this module so old .pkl files still load correctly.
# ═══════════════════════════════════════════════════════════════════
import types

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

def load_model():
    if not os.path.exists(MODEL_PATH):
        print(red(f"\n  '{MODEL_PATH}' not found. Run python train_model.py first.\n"))
        sys.exit(1)
    with open(MODEL_PATH, "rb") as f:
        try:
            return _FixedUnpickler(f).load()
        except Exception:
            f.seek(0)
            return pickle.load(f)


# ═══════════════════════════════════════════════════════════════════
#  NEGATION GUARD — runs before ML model in predict()
#
#  WHY: TF-IDF models are bag-of-words — they see 'anxious' as a
#  strong feature regardless of whether 'not' precedes it. A regex
#  pre-check catches these before the model can misclassify them.
# ═══════════════════════════════════════════════════════════════════

# Regex that catches: "not anxious", "no i am not sad", "i'm fine not stressed", etc.
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

# Phrases that mean "I'm okay" — should map to greeting, not any emotion
_IM_FINE_PATTERN = re.compile(
    r"^(i am fine|i am okay|i am good|i am alright|i'm fine|i'm okay|"
    r"i'm good|i'm alright|i feel fine|i feel okay|i feel good|"
    r"i feel alright|doing fine|doing okay|doing well|feeling okay|"
    r"feeling fine|feeling good|feeling better|i am doing fine|"
    r"i am doing okay|i am doing good|all good|all okay|"
    r"not bad|i am not bad|pretty good|pretty okay)[\.\!]*$",
    re.IGNORECASE
)

_NEGATION_REPLIES = [
    "That's really good to hear! 🌸 It's always nice when things feel a bit lighter. What's on your mind today?",
    "Glad you're feeling okay! Sometimes even just checking in with yourself matters. Is there anything you'd like to talk about?",
    "That's wonderful! 🌿 What's been going well for you lately, or is there something you'd like to explore?",
    "Great to hear that! Even on good days, it can help to reflect a little. How has your day been overall?",
]

_IM_FINE_REPLIES = [
    "Great to hear you're doing okay! 🌿 Is there anything on your mind you'd like to talk through, or just checking in?",
    "That's good! Sometimes just touching base with yourself is enough. Anything you'd like to share or explore today?",
    "Glad to hear it! 🌸 I'm here whenever you want to talk — what's on your mind?",
]


# ═══════════════════════════════════════════════════════════════════
#  GREETING GUARD — simple patterns that are always greetings
# ═══════════════════════════════════════════════════════════════════
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


# ═══════════════════════════════════════════════════════════════════
#  PREDICT — full pipeline with all guards + ML fallback
# ═══════════════════════════════════════════════════════════════════

def predict(raw_text: str, bundle: dict):
    """
    Returns: (tag, confidence, response, uncertain_bool)

    Pipeline order:
      1. Greeting guard  — hi/hello/hey → always greeting response
      2. "I'm fine" guard — "i am okay" etc → positive acknowledgement
      3. Negation guard  — "not anxious" etc → positive acknowledgement
      4. ML model prediction
      5. Confidence threshold check → uncertain fallback if below threshold
    """
    text_stripped = raw_text.strip()

    # ── 1. Greeting guard ─────────────────────────────────────────
    if _GREETING_PATTERN.match(text_stripped):
        return "greeting", 1.0, random.choice(_GREETING_REPLIES), False

    # ── 2. "I'm fine / okay / good" guard ─────────────────────────
    if _IM_FINE_PATTERN.match(text_stripped):
        return "positive_state", 1.0, random.choice(_IM_FINE_REPLIES), False

    # ── 3. Negation guard ─────────────────────────────────────────
    # Catches: "i am not anxious", "no i am not sad", "not feeling stressed"
    if _NEGATION_EMOTION_PATTERN.search(text_stripped):
        return "negation_override", 1.0, random.choice(_NEGATION_REPLIES), False

    # ── 4. ML model ───────────────────────────────────────────────
    processed = preprocess(raw_text)

    model = bundle.get("ensemble") or bundle.get("pipeline")
    if model is None:
        raise KeyError("Model bundle has neither 'ensemble' nor 'pipeline' key.")

    le            = bundle["label_encoder"]
    responses_map = bundle["responses_map"]

    proba     = model.predict_proba([processed])[0]
    idx       = int(np.argmax(proba))
    conf      = float(proba[idx])
    tag       = le.inverse_transform([idx])[0]

    # ── 5. Confidence threshold ───────────────────────────────────
    # FIX: Was 0.70 — caused almost every real input to fall back.
    # Now uses CONFIDENCE_THRESHOLD = 0.45 (set at top of file).
    uncertain = conf < CONFIDENCE_THRESHOLD

    if uncertain:
        response = (
            "I want to make sure I understand you. "
            "Could you tell me a little more about what's on your mind or how you're feeling?"
        )
    else:
        response = random.choice(responses_map.get(tag, [
            "I'm here and listening. Can you tell me a little more?"
        ]))

    return tag, round(conf, 4), response, uncertain


# ── Review queue ──────────────────────────────────────────────────────────────
def load_queue():
    if not os.path.exists(REVIEW_QUEUE_PATH):
        return []
    with open(REVIEW_QUEUE_PATH) as f:
        return json.load(f)

def save_queue(q):
    with open(REVIEW_QUEUE_PATH, "w") as f:
        json.dump(q, f, indent=2)

def log_uncertain(text, tag, conf):
    q    = load_queue()
    seen = {i["text"] for i in q}
    if text.lower() in seen:
        return sum(1 for i in q if not i["labeled"])
    q.append({
        "id":            len(q) + 1,
        "text":          text.lower(),
        "predicted_tag": tag,
        "confidence":    conf,
        "timestamp":     datetime.datetime.now().isoformat(timespec="seconds"),
        "labeled":       False,
        "correct_tag":   None
    })
    save_queue(q)
    return sum(1 for i in q if not i["labeled"])


# ── UI helpers ────────────────────────────────────────────────────────────────
def banner(meta):
    sep = "  " + "─" * 57
    print(f"\n{teal(sep)}")
    print(teal("  ") + bold("  ManoKart Counsellor  [Active Learning Mode]"))
    print(teal("  ") + dim(f"  Model         : {meta.get('model_type','ML')}"))
    print(teal("  ") + dim(f"  Test accuracy : {meta.get('test_accuracy',0)*100:.2f}%"))
    print(teal("  ") + dim(f"  Conf threshold: {int(CONFIDENCE_THRESHOLD*100)}%"))
    print(teal("  ") + dim(f"  Auto-retrain  : every {RETRAIN_EVERY} new labels"))
    print(f"{teal(sep)}\n")
    print(wrap("Welcome. This is a safe, non-judgmental space. "
               "Share what's on your mind and I will do my best to support you."))
    print(f"\n{dim('  Commands:  quit · info · debug')}\n{teal(sep)}\n")

def bot_say(text, uncertain=False):
    label = yellow("  ManoKart › ") if uncertain else teal("  ManoKart › ")
    print(f"\n{label}{wrap(text).strip()}\n")

def show_info(meta, debug=False):
    q         = load_queue()
    unlabeled = sum(1 for i in q if not i["labeled"])
    labeled   = sum(1 for i in q if i["labeled"])
    print(f"\n{bold('  ── Model ──────────────────────────────────────────────')}")
    for k, v in meta.items():
        if k == "classes": v = ", ".join(v)
        print(dim(f"  {k:<22}: ") + str(v))
    print(f"\n{bold('  ── Active Learning Queue ───────────────────────────────')}")
    print(dim(f"  Total logged    : {len(q)}"))
    print(dim(f"  Labeled         : {labeled}"))
    print(dim(f"  Awaiting review : {unlabeled}"))
    nxt = RETRAIN_EVERY - (labeled % RETRAIN_EVERY)
    print(dim(f"  Next retrain at : {nxt} more label(s)\n"))


# ── Main loop ─────────────────────────────────────────────────────────────────
def main():
    debug  = "--debug" in sys.argv
    bundle = load_model()
    meta   = bundle.get("metadata", {})
    banner(meta)

    turn = 0
    while True:
        try:
            raw = input(green("  You › ")).strip()
        except (EOFError, KeyboardInterrupt):
            raw = "exit"

        if not raw:
            continue
        if raw.lower() in {"quit", "exit", "q"}:
            bot_say("Take good care of yourself. Goodbye.")
            break
        if raw.lower() == "info":
            show_info(meta, debug)
            continue

        tag, conf, response, uncertain = predict(raw, bundle)
        turn += 1

        if uncertain:
            unlabeled = log_uncertain(raw, tag, conf)
            if debug:
                print(yellow(f"  [LOGGED] tag={tag}  conf={conf:.2%}"))
            if unlabeled > 0 and unlabeled % RETRAIN_EVERY == 0:
                print(yellow(f"\n  ⚡ {unlabeled} uncertain messages logged."))
                print(yellow("     Review them and retrain to improve accuracy.\n"))
        elif debug:
            print(dim(f"  [tag={tag}  conf={conf:.2%}]"))

        if tag in CRISIS_TAGS:
            print(red(CRISIS_MESSAGE))

        bot_say(response, uncertain=uncertain)

        if turn % 5 == 0:
            print(dim("  ── A professional counsellor can provide deeper support. ──\n"))

if __name__ == "__main__":
    main()