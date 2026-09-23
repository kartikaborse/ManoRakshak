"""
ManoRakshak.AI Voice Engine
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
        from TTS.api import TTS
        _tts_model = TTS("tts_models/multilingual/multi-dataset/xtts_v2")
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


# ══════════════════════════════════════════════════════════════
#  VERSION 2 — ACOUSTIC VOICE STRESS ANALYTICS (VSA) ENGINE
# ══════════════════════════════════════════════════════════════

def analyze_voice_stress(audio_path: str) -> dict:
    """
    Pure-Python/Numpy Voice Stress Analyzer.
    Analyzes jitter (pitch instability), silence ratio, and average amplitude/RMS.
    """
    import wave
    import numpy as np

    try:
        with wave.open(audio_path, 'rb') as w:
            params = w.getparams()
            channels = params.nchannels
            sampwidth = params.sampwidth
            framerate = params.framerate
            nframes = params.nframes
            
            if nframes == 0:
                return {"vocal_jitter": 0.0, "vocal_shimmer": 0.0, "silence_ratio": 0.0, "stress_score": 0.0}
            
            raw_data = w.readframes(nframes)
            
        # Convert bytes to numpy array based on sample width
        if sampwidth == 1:
            data = np.frombuffer(raw_data, dtype=np.uint8).astype(np.float32) - 128
        elif sampwidth == 2:
            data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)
        elif sampwidth == 4:
            data = np.frombuffer(raw_data, dtype=np.int32).astype(np.float32)
        else:
            data = np.frombuffer(raw_data, dtype=np.int16).astype(np.float32)

        # Merge channels to mono if stereo
        if channels > 1:
            data = data.reshape(-1, channels).mean(axis=1)

        # Normalize data
        max_val = np.max(np.abs(data))
        if max_val > 0:
            data = data / max_val

        # 1. Compute silent regions and silence ratio
        # Let's divide into 30ms frames
        frame_size = int(framerate * 0.03)  # 30ms
        if frame_size <= 0:
            frame_size = 1024
        
        frames = [data[i:i+frame_size] for i in range(0, len(data), frame_size) if len(data[i:i+frame_size]) == frame_size]
        
        if not frames:
            return {"vocal_jitter": 0.0, "vocal_shimmer": 0.0, "silence_ratio": 0.0, "stress_score": 0.0}

        rms_list = [np.sqrt(np.mean(f**2)) for f in frames]
        # Silence threshold: 10% of max average RMS or absolute 0.015
        max_rms = max(rms_list) if rms_list else 0.1
        silence_thresh = max(0.015, 0.1 * max_rms)
        
        silent_frames = sum(1 for rms in rms_list if rms < silence_thresh)
        silence_ratio = silent_frames / len(frames) if frames else 0.0

        # 2. Extract pitch (F0) and calculate Jitter/Shimmer on voiced frames
        # Human pitch range: 60Hz to 400Hz
        # Sample rate / Pitch range: (framerate/400) to (framerate/60)
        min_lag = int(framerate / 400)
        max_lag = int(framerate / 60)
        
        pitch_periods = []
        amplitudes = []
        
        for f, rms in zip(frames, rms_list):
            if rms >= silence_thresh:  # Voiced frame
                # Autocorrelation
                corr = np.correlate(f, f, mode='full')
                corr = corr[len(corr)//2:]  # Keep second half
                
                # Find peak in the human pitch range lag window
                if len(corr) > max_lag:
                    lag_section = corr[min_lag:max_lag]
                    if len(lag_section) > 0:
                        peak_lag = min_lag + np.argmax(lag_section)
                        # Ensure the autocorrelation is reasonably high to confirm voice periodicity
                        if corr[peak_lag] > 0.25 * corr[0]:
                            pitch_periods.append(peak_lag)
                            amplitudes.append(rms)

        # 3. Calculate Jitter and Shimmer
        vocal_jitter = 0.0
        vocal_shimmer = 0.0
        
        if len(pitch_periods) >= 2:
            # Jitter (local): average absolute difference between consecutive periods / average period
            diffs = np.abs(np.diff(pitch_periods))
            vocal_jitter = np.mean(diffs) / np.mean(pitch_periods) if np.mean(pitch_periods) > 0 else 0.0
            
            # Shimmer (local): average absolute difference between consecutive peak amplitudes / average amplitude
            amp_diffs = np.abs(np.diff(amplitudes))
            vocal_shimmer = np.mean(amp_diffs) / np.mean(amplitudes) if np.mean(amplitudes) > 0 else 0.0

        # Bound the metrics to realistic percentages (e.g. 0 to 1)
        vocal_jitter = float(min(1.0, max(0.0, vocal_jitter)))
        vocal_shimmer = float(min(1.0, max(0.0, vocal_shimmer)))
        silence_ratio = float(min(1.0, max(0.0, silence_ratio)))

        # 4. Generate a combined vocal stress score (0.0 to 1.0)
        # Jitter contributes 50%, silence ratio contributes 30%, shimmer contributes 20%
        # High jitter (irregular voice tremors) is a very strong marker for physical stress/fear.
        # High silence ratio (long pauses/hesitations) indicates depression or cognitive overload.
        # Normalize jitter/shimmer relative to typical stress benchmarks
        scaled_jitter = min(1.0, vocal_jitter / 0.10)
        scaled_shimmer = min(1.0, vocal_shimmer / 0.15)
        stress_score = (scaled_jitter * 0.5) + (silence_ratio * 0.3) + (scaled_shimmer * 0.2)
        
        return {
            "vocal_jitter": round(vocal_jitter, 4),
            "vocal_shimmer": round(vocal_shimmer, 4),
            "silence_ratio": round(silence_ratio, 4),
            "stress_score": round(float(stress_score), 4)
        }

    except Exception as e:
        print(f"Error in VSA calculation: {e}")
        return {
            "vocal_jitter": 0.0,
            "vocal_shimmer": 0.0,
            "silence_ratio": 0.0,
            "stress_score": 0.0,
            "error": str(e)
        }

