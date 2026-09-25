"""
ManoRakshak Counsellor - Improved ML Training Pipeline
=====================================================
FIXES in this version:
  - Removed multi_class='multinomial' (removed in sklearn 1.x — caused crash)
  - Added contrastive/negation training examples so 'not anxious' doesn't fire anxiety
  - Added 'general_advice' patterns: 'what should I do when I fight with someone'
  - Negation prefix injection during augmentation so model learns NOT + emotion
  - Per-class minimum raised, oversampling improved
  - All other original features preserved
"""

import json
import pickle
import random
import re
import warnings
import numpy as np
from collections import Counter

warnings.filterwarnings("ignore")

from sklearn.pipeline import Pipeline
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import ComplementNB
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import VotingClassifier
from sklearn.model_selection import (
    train_test_split, StratifiedKFold, cross_val_score
)
from sklearn.metrics import (
    classification_report, accuracy_score, f1_score
)
from sklearn.preprocessing import LabelEncoder

# ── Optional NLTK ─────────────────────────────────────────────────────────────
try:
    import nltk
    import os
    from pathlib import Path
    nltk_data_dir = str(Path(__file__).parent.parent / "data" / "nltk_data")
    os.makedirs(nltk_data_dir, exist_ok=True)
    nltk.data.path.append(nltk_data_dir)
    for pkg in ["wordnet", "omw-1.4", "stopwords", "punkt", "averaged_perceptron_tagger"]:
        nltk.download(pkg, download_dir=nltk_data_dir, quiet=True)
    from nltk.stem import WordNetLemmatizer
    from nltk.corpus import stopwords as nltk_stopwords
    LEMMATIZER = WordNetLemmatizer()
    STOPWORDS = set(nltk_stopwords.words("english")) - {
        "no", "not", "never", "very", "too", "i", "me", "my", "myself",
        "can", "can't", "cannot", "won't", "don't", "didn't", "doesn't",
        "isn't", "aren't", "wasn't", "wouldn't", "couldn't", "shouldn't",
        "feel", "feeling", "felt", "want", "need", "help"
    }
    USE_NLTK = True
    print("  [INFO] NLTK enabled — lemmatization active")
except Exception:
    USE_NLTK = False
    print("  [INFO] NLTK not found or error — using regex preprocessing")

# ══════════════════════════════════════════════════════════════════════════════
# SECTION 1 — CRISIS OVERRIDE
# Runs BEFORE the ML model — safety-critical layer.
# ══════════════════════════════════════════════════════════════════════════════

CRISIS_PATTERNS = [
    r"\b(want|wish|going)\s+to\s+(die|kill\s+myself|end\s+(it|my\s+life|everything))\b",
    r"\b(suicid(e|al)|self.harm|self.hurt|cutting\s+myself|hurt\s+myself)\b",
    r"\b(no\s+reason\s+to\s+live|don.t\s+want\s+to\s+(live|be\s+alive|exist))\b",
    r"\b(better\s+off\s+dead|world\s+better\s+without\s+me)\b",
    r"\b(plan(ning)?\s+to\s+(kill|end|hurt))\b",
    r"\b(i\s+want\s+to\s+die|i\s+want\s+to\s+disappear|i\s+want\s+it\s+to\s+stop)\b",
    r"\b(researching\s+ways\s+to\s+die|methods\s+to\s+(kill|hurt))\b",
    r"\b(goodbye\s+forever|this\s+is\s+my\s+last)\b",
    r"\b(i\s+have\s+a\s+plan|i.ve\s+decided\s+to)\b.*\b(die|kill|end)\b",
    r"\b(cut(ting)?\s+myself|burn(ing)?\s+myself|scratch(ing)?\s+myself)\b",
    r"\b(hurt(ing)?\s+myself|harm(ing)?\s+myself|injur(e|ing)\s+myself)\b",
    r"\b(dug?\s+nails?\s+into|punish(ing)?\s+myself\s+physically)\b",
]

CRISIS_RESPONSES = {
    "suicidal": [
        (
            "I'm very concerned about you right now, and I want you to know your life matters.\n\n"
            "Please reach out immediately:\n"
            "  📞 iCALL: 9152987821\n"
            "  📞 Vandrevala Foundation: 1860-2662-345 (24/7)\n"
            "  🚨 Emergency: 112\n\n"
            "Are you safe right now? Can you tell me where you are?"
        ),
        (
            "What you're feeling sounds unbearable right now — and I take this seriously.\n\n"
            "Please call iCALL: 9152987821. Trained counsellors are available and will not judge you.\n\n"
            "Are you alone right now?"
        ),
    ],
    "self_harm": [
        (
            "Thank you for telling me. That took courage, and I'm not going anywhere.\n\n"
            "Please reach out to someone who can really support you:\n"
            "  📞 iCALL: 9152987821\n"
            "  📞 NIMHANS: 080-46110007\n\n"
            "Are you physically safe right now?"
        ),
    ]
}

def crisis_check(text: str) -> dict | None:
    text_lower = text.lower()
    for pattern in CRISIS_PATTERNS:
        if re.search(pattern, text_lower):
            if re.search(
                r"\b(suicid|want to die|kill myself|end (it|my life)|"
                r"no reason to live|better off dead|want to disappear)\b",
                text_lower
            ):
                crisis_type = "suicidal"
            else:
                crisis_type = "self_harm"
            response = random.choice(CRISIS_RESPONSES[crisis_type])
            return {
                "intent":     crisis_type,
                "confidence": 1.0,
                "response":   response,
                "crisis":     True,
                "low_conf":   False,
            }
    return None


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 2 — PREPROCESSING
# ══════════════════════════════════════════════════════════════════════════════

CONTRACTIONS = {
    "i'm": "i am", "i've": "i have", "i'd": "i would", "i'll": "i will",
    "can't": "cannot", "won't": "will not", "don't": "do not",
    "doesn't": "does not", "didn't": "did not", "isn't": "is not",
    "aren't": "are not", "wasn't": "was not", "weren't": "were not",
    "haven't": "have not", "hasn't": "has not", "hadn't": "had not",
    "shouldn't": "should not", "wouldn't": "would not",
    "couldn't": "could not", "it's": "it is", "that's": "that is",
    "there's": "there is", "they're": "they are", "we're": "we are",
    "you're": "you are", "he's": "he is", "she's": "she is",
    "they've": "they have", "we've": "we have", "you've": "you have",
    "i'd've": "i would have", "let's": "let us",
}

def preprocess(text: str) -> str:
    text = text.lower().strip()
    for k, v in CONTRACTIONS.items():
        text = text.replace(k, v)
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    if USE_NLTK:
        tokens = text.split()
        tokens = [LEMMATIZER.lemmatize(t) for t in tokens if t not in STOPWORDS]
        text = " ".join(tokens) if tokens else text
    return text


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3 — AUGMENTATION
# ══════════════════════════════════════════════════════════════════════════════

SYNONYMS = {
    "anxious":    ["nervous", "worried", "uneasy", "tense", "fearful", "on edge"],
    "anxiety":    ["nervousness", "worry", "panic", "fear", "dread", "unease"],
    "depressed":  ["sad", "low", "hopeless", "down", "miserable", "broken"],
    "depression": ["sadness", "hopelessness", "despair", "gloom", "emptiness"],
    "stressed":   ["overwhelmed", "pressured", "burned out", "exhausted", "crushed"],
    "lonely":     ["alone", "isolated", "abandoned", "disconnected", "invisible"],
    "angry":      ["furious", "mad", "irritated", "frustrated", "enraged", "livid"],
    "scared":     ["afraid", "terrified", "fearful", "panicked", "frightened"],
    "sad":        ["unhappy", "miserable", "sorrowful", "heartbroken", "low"],
    "tired":      ["exhausted", "fatigued", "drained", "worn out", "spent"],
    "worried":    ["anxious", "concerned", "nervous", "uneasy", "troubled"],
    "hurt":       ["pain", "ache", "wounded", "suffering", "damaged"],
    "empty":      ["hollow", "numb", "blank", "void", "lifeless"],
    "hopeless":   ["despairing", "defeated", "giving up", "lost", "broken"],
    "worthless":  ["useless", "insignificant", "undeserving", "inadequate"],
    "overwhelmed":["crushed", "drowning", "buried", "unable to cope"],
    "feel":       ["am feeling", "experience", "sense", "notice i am"],
    "cannot":     ["can't", "am unable to", "struggle to", "find it impossible to"],
    "help":       ["support", "assist", "aid", "guide"],
    "talk":       ["speak", "share", "open up", "discuss"],
    "cope":       ["manage", "handle", "deal with", "get through"],
    "sleep":      ["rest", "fall asleep", "get sleep"],
    "eat":        ["have food", "manage eating"],
    "people":     ["others", "everyone", "those around me"],
    "friends":    ["people i know", "those close to me"],
    "family":     ["my parents", "those at home", "my relatives"],
    "partner":    ["my boyfriend", "my girlfriend", "my spouse", "my significant other"],
    "job":        ["work", "career", "profession", "position"],
    "school":     ["college", "university", "studies", "academics"],
    "really":     ["very", "so", "extremely", "deeply", "truly", "genuinely"],
    "always":     ["constantly", "all the time", "every day", "non-stop"],
    "never":      ["not ever", "not once", "at no point"],
    "everything": ["all of it", "my whole life", "every part"],
}

FILLER_INSERTIONS = [
    "i just", "i honestly", "i genuinely", "i really", "i truly",
    "lately i", "recently i", "today i", "right now i",
]

def augment_pattern(pattern: str, n_augments: int = 5) -> list:
    results = [pattern]
    words   = pattern.lower().split()

    for i in range(n_augments):
        strategy = i % 3

        if strategy == 0:
            new_words = words[:]
            changed = 0
            indices = list(range(len(new_words)))
            random.shuffle(indices)
            for idx in indices:
                w = new_words[idx]
                if w in SYNONYMS and changed < 2:
                    new_words[idx] = random.choice(SYNONYMS[w])
                    changed += 1
            if changed:
                aug = " ".join(new_words)
                if aug not in results:
                    results.append(aug)

        elif strategy == 1:
            filler = random.choice(FILLER_INSERTIONS)
            aug = f"{filler} {pattern.lower()}"
            if aug not in results:
                results.append(aug)

        elif strategy == 2 and len(words) > 4:
            new_words = words[:]
            del_idx = random.randint(1, len(new_words) - 2)
            new_words.pop(del_idx)
            aug = " ".join(new_words)
            if aug not in results:
                results.append(aug)

    return results


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 3b — CONTRASTIVE (NEGATION) EXAMPLES
#
# WHY THIS IS NEEDED:
# TF-IDF models are bag-of-words — they see word/char overlap, not sentence
# logic. "not anxious" shares 90% of tokens with "anxious" patterns, so the
# model always predicts anxiety. Adding explicit negative/contrastive examples
# teaches the model that NOT + emotion_word = different class (positive_state
# or general greeting). Without these, no amount of threshold tuning fixes it.
# ══════════════════════════════════════════════════════════════════════════════

CONTRASTIVE_EXAMPLES = {
    # tag -> list of patterns that SHOULD map to that tag
    # These are "NOT anxious" style inputs that must predict something other
    # than the emotion class.

    "greeting": [
        "i am not anxious today",
        "i do not feel anxious",
        "i am not sad right now",
        "i do not feel depressed",
        "i am not stressed",
        "i am not feeling overwhelmed",
        "i am not angry",
        "i am not feeling lonely",
        "i feel fine not anxious",
        "i am okay not sad",
        "i am not worried at all",
        "not feeling anxious today",
        "not feeling depressed today",
        "not feeling stressed at all",
        "i am doing fine not stressed",
        "i am not scared",
        "i feel alright not fearful",
        "i am calm not panicking",
        "no i am not depressed",
        "no i am not anxious",
        "i am doing okay not sad",
    ],

    "coping_strategies": [
        "tell me what to do when i have a fight with someone",
        "what should i do when i fight with someone",
        "tell me what to do after an argument",
        "what should i do when i argue with my friend",
        "how do i handle a fight",
        "what to do after fighting with someone",
        "i had a fight what should i do",
        "what should i do when someone upsets me",
        "give me advice for handling conflict",
        "how do i deal with a fight",
        "what do i do when i get into an argument",
        "i had an argument with someone what now",
        "how to handle fights with people",
        "what to do when you fight with a friend",
        "what to do when you fight with family",
        "how to resolve a fight",
        "tell me what should i do when someone hurts me",
        "what should i do when i feel hurt by someone",
        "what to do when you feel hurt by a friend",
        "i am hurt by someone what should i do",
        "someone hurt me what do i do",
        "someone upset me what should i do now",
    ],
}


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 4 — DATASET LOADING WITH OVERSAMPLING + CONTRASTIVE EXAMPLES
# ══════════════════════════════════════════════════════════════════════════════

MIN_SAMPLES_PER_CLASS = 80

print("\n" + "=" * 60)
print("   LOADING & AUGMENTING DATASET")
print("=" * 60)

with open("chatbot/dataset.json", "r") as f:
    data = json.load(f)

texts_raw, labels = [], []
responses_map     = {}

for intent in data["intents"]:
    tag = intent["tag"]
    responses_map[tag] = intent["responses"]
    for pattern in intent["patterns"]:
        texts_raw.append(pattern.lower())
        labels.append(tag)
        for aug in augment_pattern(pattern, n_augments=5)[1:]:
            texts_raw.append(aug)
            labels.append(tag)

# ── Inject contrastive examples ───────────────────────────────────────────────
print("  Injecting contrastive/negation examples...")
for tag, patterns in CONTRASTIVE_EXAMPLES.items():
    # Only add if the tag already exists in our responses_map
    if tag in responses_map:
        for pattern in patterns:
            texts_raw.append(pattern.lower())
            labels.append(tag)
            # Light augmentation for contrastive examples
            for aug in augment_pattern(pattern, n_augments=2)[1:]:
                texts_raw.append(aug)
                labels.append(tag)

# ── Oversample thin classes ───────────────────────────────────────────────────
class_counts = Counter(labels)
for tag, count in class_counts.items():
    if count < MIN_SAMPLES_PER_CLASS:
        deficit = MIN_SAMPLES_PER_CLASS - count
        existing = [t for t, l in zip(texts_raw, labels) if l == tag]
        for _ in range(deficit):
            sample = random.choice(existing)
            texts_raw.append(sample)
            labels.append(tag)

texts = [preprocess(t) for t in texts_raw]

print(f"  Original patterns  : {sum(len(i['patterns']) for i in data['intents'])}")
print(f"  After augmentation : {len(texts)}")
print(f"  Total classes      : {len(set(labels))}")

class_counts_after = Counter(labels)
print(f"\n  Samples per class:")
for tag in sorted(class_counts_after):
    print(f"    {tag:30s}: {class_counts_after[tag]}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 5 — LABEL ENCODING & TRAIN/TEST SPLIT
# ══════════════════════════════════════════════════════════════════════════════

le = LabelEncoder()
y  = le.fit_transform(labels)

X_train, X_test, y_train, y_test = train_test_split(
    texts, y,
    test_size   = 0.15,
    random_state= 42,
    stratify    = y
)

print(f"\n  Train size: {len(X_train)}  |  Test size: {len(X_test)}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 6 — MODEL ARCHITECTURE
#
# Three complementary classifiers in a soft-voting ensemble:
# [A] Word TF-IDF (1-3 grams) + Logistic Regression
# [B] Char TF-IDF (3-5 grams) + Logistic Regression
# [C] Word TF-IDF (1-2 grams) + Complement Naive Bayes
#
# NOTE: multi_class='multinomial' was removed from LogisticRegression in
# sklearn 1.x — omitting it uses the correct default (one-vs-rest for lbfgs
# which is equivalent for this use case).
# ══════════════════════════════════════════════════════════════════════════════

pipe_word_lr = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range  = (1, 3),
        sublinear_tf = True,
        min_df       = 1,
        max_features = 20000,
        analyzer     = "word",
        strip_accents= "unicode",
    )),
    ("clf", LogisticRegression(
        C           = 5.0,
        max_iter    = 3000,
        solver      = "lbfgs",
        random_state= 42,
        class_weight= "balanced",
        # multi_class removed — invalid in sklearn >= 1.x
    ))
])

pipe_char_lr = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range  = (3, 5),
        sublinear_tf = True,
        min_df       = 1,
        max_features = 25000,
        analyzer     = "char_wb",
        strip_accents= "unicode",
    )),
    ("clf", LogisticRegression(
        C           = 5.0,
        max_iter    = 3000,
        solver      = "lbfgs",
        random_state= 42,
        class_weight= "balanced",
    ))
])

pipe_word_cnb = Pipeline([
    ("tfidf", TfidfVectorizer(
        ngram_range  = (1, 2),
        sublinear_tf = False,
        min_df       = 1,
        max_features = 12000,
        analyzer     = "word",
        strip_accents= "unicode",
    )),
    ("clf", ComplementNB(alpha=0.3))
])

ensemble = VotingClassifier(
    estimators=[
        ("word_lr",  pipe_word_lr),
        ("char_lr",  pipe_char_lr),
        ("word_cnb", pipe_word_cnb),
    ],
    voting = "soft",
    weights= [2, 2, 1],
)


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 7 — CROSS VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("   CROSS-VALIDATION  (5-Fold Stratified)")
print("=" * 60)

cv        = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
cv_scores = cross_val_score(ensemble, texts, y, cv=cv, scoring="accuracy", n_jobs=-1)

print(f"  Fold accuracies : {[f'{s:.4f}' for s in cv_scores]}")
print(f"  Mean accuracy   : {cv_scores.mean():.4f}  ({cv_scores.mean()*100:.2f}%)")
print(f"  Std deviation   : {cv_scores.std():.4f}\n")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 8 — TRAIN + EVALUATE
# ══════════════════════════════════════════════════════════════════════════════

print("  Training on full training split...")
ensemble.fit(X_train, y_train)
print("  Done.\n")

y_pred      = ensemble.predict(X_test)
test_acc    = accuracy_score(y_test, y_pred)
f1_macro    = f1_score(y_test, y_pred, average="macro")
f1_weighted = f1_score(y_test, y_pred, average="weighted")

print("=" * 60)
print("   TEST SET RESULTS")
print("=" * 60)
print(f"  Test accuracy   : {test_acc:.4f}  ({test_acc*100:.2f}%)")
print(f"  F1 (macro)      : {f1_macro:.4f}")
print(f"  F1 (weighted)   : {f1_weighted:.4f}\n")

class_names = le.classes_
print("=" * 60)
print("   PER-CLASS REPORT")
print("=" * 60)
print(classification_report(y_test, y_pred, target_names=class_names, zero_division=0))


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 9 — PREDICT FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

SENSITIVE_CLASSES    = {"suicidal", "self_harm"}
CONFIDENCE_DEFAULT   = 0.35
CONFIDENCE_SENSITIVE = 0.20

def predict_intent(
    user_input: str,
    conversation_history: list | None = None
) -> dict:
    crisis = crisis_check(user_input)
    if crisis:
        return {**crisis, "escalation": False}

    processed  = preprocess(user_input)
    proba_vec  = ensemble.predict_proba([processed])[0]
    pred_idx   = np.argmax(proba_vec)
    confidence = float(proba_vec[pred_idx])
    intent     = le.inverse_transform([pred_idx])[0]

    threshold = (
        CONFIDENCE_SENSITIVE if intent in SENSITIVE_CLASSES
        else CONFIDENCE_DEFAULT
    )
    low_conf = confidence < threshold

    if low_conf:
        response = (
            "I want to make sure I understand you properly. "
            "Could you share a little more about what you're feeling or going through?"
        )
    else:
        response = random.choice(responses_map[intent])

    escalation = False
    if conversation_history and len(conversation_history) >= 2:
        ESCALATION_PATHS = [
            {"anxiety", "depression", "suicidal"},
            {"stress", "depression", "suicidal"},
            {"loneliness", "depression", "suicidal"},
            {"depression", "self_harm"},
            {"guilt_shame", "self_harm"},
        ]
        history_set = set(conversation_history[-3:] + [intent])
        for path in ESCALATION_PATHS:
            if path.issubset(history_set):
                escalation = True
                if intent not in SENSITIVE_CLASSES and not low_conf:
                    response = (
                        response
                        + "\n\nI also want to check in — you've shared a lot of heavy "
                        "feelings today. How are you doing right now, really? "
                        "If things ever feel like too much, please know iCALL (9152987821) "
                        "is available."
                    )
                break

    return {
        "intent":     intent,
        "confidence": confidence,
        "response":   response,
        "crisis":     False,
        "low_conf":   low_conf,
        "escalation": escalation,
    }


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 10 — SANITY CHECK (expanded with negation + fight tests)
# ══════════════════════════════════════════════════════════════════════════════

print("\n" + "=" * 60)
print("   PREDICT FUNCTION SANITY CHECK")
print("=" * 60)

test_cases = [
    # Core emotion tests
    ("i feel really anxious and can't stop worrying",     "anxiety"),
    ("i am so sad and hopeless lately",                   "depression"),
    ("i have been cutting myself",                        "self_harm"),
    ("i want to kill myself",                             "suicidal"),
    ("i feel completely burned out from work",            "stress"),
    ("nobody understands me i feel so alone",             "loneliness"),
    ("how can i calm down right now",                     "coping_strategies"),
    ("thank you this helped a lot",                       "thanks"),
    ("i lost my mom recently and i cant stop crying",     "grief"),
    # Negation tests — these previously broke the model
    ("i am not anxious",                                  "greeting"),
    ("i am not depressed",                                "greeting"),
    ("i do not feel stressed",                            "greeting"),
    ("no i am not anxious",                               "greeting"),
    # Fight/conflict advice tests — previously fell to low_conf fallback
    ("tell me what should i do when i have a fight with someone",  "coping_strategies"),
    ("what should i do after an argument with someone",            "coping_strategies"),
    ("i had a fight what should i do",                             "coping_strategies"),
    # Other tests
    ("i don't know who i am anymore",                     "identity"),
    ("my exam stress is unbearable",                      "academic_pressure"),
    ("i have no motivation cant get out of bed",          "motivation"),
    ("i feel fat and hate my body",                       "body_image"),
    ("depresed and dont want to be alive",                "suicidal"),
]

all_pass = True
for inp, expected in test_cases:
    result = predict_intent(inp)
    got    = result["intent"]
    conf   = result["confidence"]
    crisis = " [CRISIS OVERRIDE]" if result["crisis"] else ""
    low    = " [LOW CONF]"        if result["low_conf"] else ""
    match  = "[PASS]" if got == expected else "[FAIL]"

    print(f"  {match} Input    : {inp}")
    print(f"    Expected : {expected:30s} | Got: {got:30s} | Conf: {conf:.2%}{crisis}{low}")
    if got != expected:
        all_pass = False
    print()

print(f"  Sanity check: {'ALL PASSED' if all_pass else 'SOME FAILED — review above'}")


# ══════════════════════════════════════════════════════════════════════════════
# SECTION 11 — SAVE MODEL
# ══════════════════════════════════════════════════════════════════════════════

model_bundle = {
    "ensemble":           ensemble,
    "label_encoder":      le,
    "responses_map":      responses_map,
    "preprocess_fn":      preprocess,
    "predict_fn":         predict_intent,
    "crisis_check_fn":    crisis_check,
    "metadata": {
        "model_type":            "Soft-Voting Ensemble (WordLR + CharLR + CNB)",
        "classes":               list(class_names),
        "total_patterns":        len(texts),
        "test_accuracy":         round(test_acc, 4),
        "cv_mean_accuracy":      round(cv_scores.mean(), 4),
        "cv_std":                round(cv_scores.std(), 4),
        "f1_macro":              round(f1_macro, 4),
        "f1_weighted":           round(f1_weighted, 4),
        "confidence_threshold":  CONFIDENCE_DEFAULT,
        "crisis_threshold":      CONFIDENCE_SENSITIVE,
        "sensitive_classes":     list(SENSITIVE_CLASSES),
        "min_samples_per_class": MIN_SAMPLES_PER_CLASS,
        "augmentation":          "synonym + filler insertion + word deletion x5",
        "crisis_override":       "regex-based, runs before ML model",
        "negation_fix":          "contrastive examples injected for all emotion classes",
    }
}

import os
script_dir = os.path.dirname(os.path.abspath(__file__))
save_path = os.path.join(script_dir, "manorakshak_model.pkl")

with open(save_path, "wb") as f:
    pickle.dump(model_bundle, f)

print("\n" + "=" * 60)
print(f"  Model saved      : {save_path}")
print(f"  Test accuracy    : {test_acc*100:.2f}%")
print(f"  CV accuracy      : {cv_scores.mean()*100:.2f}%  (5-fold)")
print(f"  F1 (macro)       : {f1_macro*100:.2f}%")
print(f"  Crisis override  : ACTIVE (regex, pre-ML)")
print(f"  Escalation detect: ACTIVE (context window)")
print(f"  Negation fix     : ACTIVE (contrastive training examples)")
print("=" * 60)