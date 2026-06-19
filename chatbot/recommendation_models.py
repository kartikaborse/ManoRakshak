try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

import numpy as np

# ══════════════════════════════════════════════════════════════
#  1. PYTORCH LSTM FOR MOOD FORECASTING
# ══════════════════════════════════════════════════════════════

if HAS_TORCH:
    class MoodLSTM(nn.Module):
        def __init__(self, input_size=1, hidden_size=16, num_layers=1, output_size=1):
            super(MoodLSTM, self).__init__()
            self.hidden_size = hidden_size
            self.num_layers = num_layers
            self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
            self.fc = nn.Linear(hidden_size, output_size)
            
        def forward(self, x):
            # x shape: (batch_size, seq_len, input_size)
            h0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
            c0 = torch.zeros(self.num_layers, x.size(0), self.hidden_size).to(x.device)
            out, _ = self.lstm(x, (h0, c0))
            # Take the output of the last time step
            out = self.fc(out[:, -1, :])
            return out
else:
    class MoodLSTM:
        pass

def normalize_mood_sequence(seq, target_len=5):
    """
    Normalizes a sequence of mood numbers (1-5) to [-1.0, 1.0],
    and pads or truncates to target_len.
    """
    if not seq:
        seq = [3.0]
    
    # Pad if too short, using the average or the first element
    if len(seq) < target_len:
        fill_val = float(seq[0])
        seq = [fill_val] * (target_len - len(seq)) + [float(x) for x in seq]
    elif len(seq) > target_len:
        seq = seq[-target_len:]
        
    # Scale: 1 -> -1.0, 3 -> 0.0, 5 -> 1.0
    return [(float(x) - 3.0) / 2.0 for x in seq]

def denormalize_mood(val):
    """Maps a predicted continuous value back to [1.0, 5.0]."""
    score = (float(val) * 2.0) + 3.0
    return max(1.0, min(5.0, score))


# ══════════════════════════════════════════════════════════════
#  2. FEATURE FORMATTER FOR RANDOM FOREST RECOMMENDER
# ══════════════════════════════════════════════════════════════

# The tags we support as features for game recommendation
TAG_FEATURES = ["anxiety", "stress", "sad", "work", "health"]

def format_recommendation_features(current_mood, avg_mood, phq9_score, gad7_score, hour, tags_list):
    """
    Converts user session features to a 10-dimensional numpy array:
    [current_mood, avg_mood, phq9_score, gad7_score, normalized_hour, tag_features...]
    """
    # Fallbacks
    current_mood = float(current_mood) if current_mood is not None else 3.0
    avg_mood = float(avg_mood) if avg_mood is not None else 3.0
    phq9_score = float(phq9_score) if phq9_score is not None else 0.0
    gad7_score = float(gad7_score) if gad7_score is not None else 0.0
    
    # Normalize hour to [0.0, 1.0]
    norm_hour = float(hour) / 24.0
    
    # Check tag triggers
    tags_lower = [t.lower().strip() for t in tags_list] if tags_list else []
    tag_bits = []
    for tf in TAG_FEATURES:
        tag_bits.append(1.0 if any(tf in t for t in tags_lower) else 0.0)
        
    feats = [current_mood, avg_mood, phq9_score, gad7_score, norm_hour] + tag_bits
    return np.array(feats, dtype=np.float32)
