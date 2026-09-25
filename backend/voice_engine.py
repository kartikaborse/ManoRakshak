"""
ManoRakshat Voice Engine
======================
Fully offline speech-to-text and voice-cloned text-to-speech.

SAFETY DESIGN — read before changing:
--------------------------------------
1. CRISIS RESPONSES NEVER USE THE CLONED VOICE.
   When chatbot.py's predict() returns a tag in CRISIS_TAGS, this module
   forces playback through the NEUTRAL_VOICE (a flat, non-cloned default
   speaker) instead of the user's enrolled loved-one voice. A person in
   crisis should hear help arrive as help — not as a simulated voice of
   someone they've lost or who isn't actually present. This is enforced
   in synthesize(), not left to the caller, so it can't be skipped by
   forgetting a flag upstream.

2. THIS MODULE ONLY HANDLES AUDIO. It does not, and should not, generate
   first-person statements as the cloned person ("I love you", "I'm proud
   of you"). That is a content decision that belongs in dataset.json /
   responses_map — keep bot responses in the bot's own voice/persona
   ("It sounds like that was really hard"), even when read aloud in a
   cloned timbre. Don't change response text generation here.

3. Voice enrollment requires explicit consent confirmation (see
   enroll_voice()) before a profile is saved. The consent flag is stored
   alongside the voice profile and re-checked at synthesis time.
"""

import os
import json
import uuid
import shutil
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
VOICES_DIR = BASE_DIR / "voices"
VOICES_DIR.mkdir(exist_ok=True)
PROFILES_PATH = VOICES_DIR / "profiles.json"

NEUTRAL_VOICE_SAMPLE = BASE_DIR / "voices" / "_neutral_default.wav"

CRISIS_TAGS = {"suicidal", "self_harm"}

# ── Lazy-loaded heavy models ────────────────────────────────────────────────
_whisper_model = None
_tts_model = None


def _get_whisper():
    global _whisper_model
    if _whisper_model is None:
        from faster_whisper import WhisperModel
        # "small" balances speed/accuracy on CPU; use "base" for faster/weaker
        _whisper_model = WhisperModel("small", device="cpu", compute_type="int8")
    return _whisper_model


def _get_tts():
    global _tts_model
    if _tts_model is None:
        try:
            from TTS.api import TTS
            _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
        except Exception as e:
            print(f"[VoiceEngine] Coqui TTS not installed or not supported on this Python version: {e}")
            return None
    return _tts_model


# ── Profiles ─────────────────────────────────────────────────────────────────
def _load_profiles() -> dict:
    if PROFILES_PATH.exists():
        with open(PROFILES_PATH) as f:
            return json.load(f)
    return {}


def _save_profiles(profiles: dict):
    with open(PROFILES_PATH, "w") as f:
        json.dump(profiles, f, indent=2)


def enroll_voice(user_id: str, display_name: str, audio_path: str,
                  consent_confirmed: bool, relationship: str = "") -> dict:
    """
    Register a voice sample for cloning. Requires explicit consent.

    consent_confirmed must be True and should only be set True by the
    frontend after the user has checked a box affirming:
      - they have the right to use this recording, and
      - they understand the bot will not claim to BE this person.
    """
    if not consent_confirmed:
        raise PermissionError(
            "Voice enrollment requires consent_confirmed=True. "
            "The UI must collect explicit confirmation before calling this."
        )

    profiles = _load_profiles()
    voice_id = str(uuid.uuid4())[:8]
    dest = VOICES_DIR / f"{voice_id}.wav"
    shutil.copy(audio_path, dest)

    profiles.setdefault(user_id, {})
    profiles[user_id][voice_id] = {
        "display_name": display_name,
        "relationship": relationship,
        "sample_path": str(dest),
        "consent_confirmed": True,
    }
    _save_profiles(profiles)
    return {"voice_id": voice_id, "display_name": display_name}


def list_voices(user_id: str) -> dict:
    return _load_profiles().get(user_id, {})


def delete_voice(user_id: str, voice_id: str):
    profiles = _load_profiles()
    entry = profiles.get(user_id, {}).pop(voice_id, None)
    if entry:
        sample = Path(entry["sample_path"])
        if sample.exists():
            sample.unlink()
        _save_profiles(profiles)


# ── STT ──────────────────────────────────────────────────────────────────────
def transcribe(audio_path: str) -> str:
    """Offline speech-to-text via faster-whisper."""
    model = _get_whisper()
    segments, _info = model.transcribe(audio_path, language="en", vad_filter=True)
    text = " ".join(seg.text.strip() for seg in segments)
    return text.strip()


# ── TTS ──────────────────────────────────────────────────────────────────────
def synthesize(text: str, out_path: str, user_id: str, voice_id: str | None,
                response_tag: str | None = None) -> str:
    """
    Offline TTS. Uses the cloned voice UNLESS response_tag is a crisis tag,
    in which case it forces the neutral default voice regardless of what
    the caller passed in.
    """
    tts = _get_tts()
    if tts is None:
        raise RuntimeError("Coqui TTS engine is not available on this Python environment.")

    use_neutral = (response_tag in CRISIS_TAGS) or (voice_id is None)

    speaker_wav = None
    if not use_neutral:
        profiles = _load_profiles()
        entry = profiles.get(user_id, {}).get(voice_id)
        if entry and entry.get("consent_confirmed") and Path(entry["sample_path"]).exists():
            speaker_wav = entry["sample_path"]
        else:
            use_neutral = True

    if use_neutral:
        if NEUTRAL_VOICE_SAMPLE.exists():
            speaker_wav = str(NEUTRAL_VOICE_SAMPLE)
        else:
            # Falls back to XTTS's built-in default speaker if no neutral
            # sample has been provided by the operator.
            speaker_wav = None

    if speaker_wav:
        tts.tts_to_file(text=text, speaker_wav=speaker_wav, language="en", file_path=out_path)
    else:
        tts.tts_to_file(text=text, language="en", file_path=out_path)

    return out_path
