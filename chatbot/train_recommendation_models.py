import os
import pickle
import random
import numpy as np
import torch
import torch.nn as nn
from sklearn.ensemble import RandomForestClassifier
from recommendation_models import MoodLSTM, normalize_mood_sequence, format_recommendation_features

# Set random seeds for reproducibility
random.seed(42)
np.random.seed(42)
torch.manual_seed(42)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LSTM_SAVE_PATH = os.path.join(SCRIPT_DIR, "mood_lstm.pt")
RF_SAVE_PATH = os.path.join(SCRIPT_DIR, "recommendation_rf.pkl")

# ══════════════════════════════════════════════════════════════
#  1. GENERATE DATA & TRAIN PYTORCH LSTM
# ══════════════════════════════════════════════════════════════

def generate_lstm_data(n_samples=5000, seq_len=5):
    """
    Generates synthetic mood time-series sequences.
    1 = excited/joyful, 2 = happy, 3 = calm, 4 = sad, 5 = anxious
    """
    X, y = [], []
    for _ in range(n_samples):
        # Pick a starting mood
        mood = random.choice([1.0, 2.0, 3.0, 4.0, 5.0])
        seq = []
        # Generate a sequence based on random walk with boundaries
        for _ in range(seq_len + 1):
            seq.append(mood)
            # Mood transitions are usually gradual but can have minor fluctuations
            change = random.choice([-1.0, 0.0, 0.0, 1.0])
            mood = max(1.0, min(5.0, mood + change))
            
        # First 5 are features, 6th is target
        x_raw = seq[:seq_len]
        y_raw = seq[seq_len]
        
        # Normalize to [-1.0, 1.0]
        x_norm = normalize_mood_sequence(x_raw, target_len=seq_len)
        y_norm = (y_raw - 3.0) / 2.0
        
        X.append(x_norm)
        y.append([y_norm])
        
    return torch.tensor(X, dtype=torch.float32).unsqueeze(-1), torch.tensor(y, dtype=torch.float32)

def train_lstm():
    print("--- Training Mood LSTM Model ---")
    X, y = generate_lstm_data()
    
    # Split into train and validation
    train_size = int(0.8 * len(X))
    X_train, X_val = X[:train_size], X[train_size:]
    y_train, y_val = y[:train_size], y[train_size:]
    
    model = MoodLSTM(input_size=1, hidden_size=16, num_layers=1, output_size=1)
    criterion = nn.MSELoss()
    optimizer = torch.optim.Adam(model.parameters(), lr=0.01)
    
    epochs = 30
    batch_size = 64
    
    for epoch in range(epochs):
        model.train()
        permutation = torch.randperm(X_train.size(0))
        epoch_loss = 0.0
        
        for i in range(0, X_train.size(0), batch_size):
            indices = permutation[i:i+batch_size]
            batch_x, batch_y = X_train[indices], y_train[indices]
            
            optimizer.zero_grad()
            outputs = model(batch_x)
            loss = criterion(outputs, batch_y)
            loss.backward()
            optimizer.step()
            
            epoch_loss += loss.item() * batch_x.size(0)
            
        epoch_loss /= X_train.size(0)
        
        # Eval
        model.eval()
        with torch.no_grad():
            val_outputs = model(X_val)
            val_loss = criterion(val_outputs, y_val).item()
            
        if (epoch + 1) % 5 == 0 or epoch == 0:
            print(f"  Epoch {epoch+1:2d}/{epochs} | Train Loss: {epoch_loss:.5f} | Val Loss: {val_loss:.5f}")
            
    # Save the PyTorch model state dict
    torch.save(model.state_dict(), LSTM_SAVE_PATH)
    print(f"  [OK] LSTM Model saved to {LSTM_SAVE_PATH}\n")


# ══════════════════════════════════════════════════════════════
#  2. GENERATE DATA & TRAIN RANDOM FOREST RECOMMENDER
# ══════════════════════════════════════════════════════════════

GAMES = [
    "manokart_body_breath_quest",
    "manokart_calm_grid_sudoku",
    "manokart_cozy_island_garden",
    "manokart_mood_blocks_tetris",
    "manokart_color_your_world",
    "manokart_spirit_journey",
    "manokart_stress_relief_ocean"
]

def generate_rf_data(n_samples=4000):
    """
    Generates synthetic feature matrices and recommendation targets.
    """
    X, y = [], []
    for _ in range(n_samples):
        # Pick random values
        current_mood = float(random.choice([1, 2, 3, 4, 5]))
        avg_mood = max(1.0, min(5.0, current_mood + random.uniform(-1.0, 1.0)))
        phq9_score = float(random.randint(0, 27))
        gad7_score = float(random.randint(0, 21))
        hour = float(random.randint(0, 23))
        
        # Select active tags based on current mood
        tags_list = []
        if current_mood == 5: # Anxious/Stressed/Angry
            tags_list.append(random.choice(["anxiety", "stress", "work", "panic"]))
        elif current_mood == 4: # Sad
            tags_list.append(random.choice(["sad", "grief", "lonely"]))
        else: # Calm/Happy
            if random.random() < 0.3:
                tags_list.append(random.choice(["health", "peace", "general"]))
                
        # Run feature formatter
        feats = format_recommendation_features(current_mood, avg_mood, phq9_score, gad7_score, hour, tags_list)
        
        # Clinical and mood logical rules to assign recommendation targets
        if any("anxiety" in t or "panic" in t for t in tags_list) or gad7_score >= 12:
            target_game = "manokart_body_breath_quest" if random.random() < 0.6 else "manokart_stress_relief_ocean"
        elif any("sad" in t or "grief" in t for t in tags_list) or phq9_score >= 12:
            target_game = "manokart_cozy_island_garden"
        elif any("stress" in t or "work" in t for t in tags_list) or current_mood == 5:
            target_game = "manokart_mood_blocks_tetris" if random.random() < 0.7 else "manokart_stress_relief_ocean"
        elif current_mood in (1, 2): # Joyful/Happy
            target_game = "manokart_color_your_world"
        else: # Calm/Neutral (3)
            target_game = "manokart_calm_grid_sudoku" if random.random() < 0.6 else "manokart_spirit_journey"
            
        X.append(feats)
        y.append(target_game)
        
    return np.array(X), np.array(y)

def train_rf():
    print("--- Training Random Forest Recommender ---")
    X, y = generate_rf_data()
    
    # Train test split
    from sklearn.model_selection import train_test_split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.15, random_state=42)
    
    clf = RandomForestClassifier(n_estimators=80, max_depth=8, random_state=42)
    clf.fit(X_train, y_train)
    
    train_acc = clf.score(X_train, y_train)
    test_acc = clf.score(X_test, y_test)
    print(f"  Train Accuracy: {train_acc*100:.2f}%")
    print(f"  Test Accuracy : {test_acc*100:.2f}%")
    
    # Save the Random Forest model bundle
    bundle = {
        "model": clf,
        "feature_names": [
            "current_mood", "avg_mood", "phq9_score", "gad7_score", "norm_hour",
            "tag_anxiety", "tag_stress", "tag_sad", "tag_work", "tag_health"
        ]
    }
    with open(RF_SAVE_PATH, "wb") as f:
        pickle.dump(bundle, f)
    print(f"  [OK] Random Forest Recommender saved to {RF_SAVE_PATH}\n")


if __name__ == "__main__":
    train_lstm()
    train_rf()
