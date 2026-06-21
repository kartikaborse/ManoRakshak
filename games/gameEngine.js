/**
 * ManoKart GameEngine
 * ===================
 * Shared engine for all 7 ManoKart games.
 * Handles: XP, levels, badges, score history, streaks, session tracking.
 *
 * USAGE IN ANY GAME FILE:
 *   <script src="../gameEngine.js"></script>
 *   GameEngine.saveScore('body_breath_quest', 450);
 *
 * STORAGE: localStorage now → swap to Firebase later by replacing
 * _storage.get / _storage.set without touching any game files.
 */

(function (global) {
  'use strict';

  /* ─────────────────────────────────────────────
     CONSTANTS
  ───────────────────────────────────────────── */

  var STORAGE_KEY   = 'manokart_engine_v1';
  var XP_PER_LEVEL  = 500;          // level up every 500 XP
  var MAX_HISTORY   = 50;           // keep last 50 scores per game
  var STREAK_WINDOW = 36 * 60 * 60 * 1000; // 36-hour window for daily streak

  /* All 7 games — display names + icons used across hub/profile/leaderboard */
  var GAMES = {
    body_breath_quest:    { name: 'Body & Breath Quest',    icon: '🧘' },
    calm_grid_sudoku:     { name: 'Calm Grid Sudoku',       icon: '🔢' },
    color_your_world:     { name: 'Color Your World',       icon: '🎨' },
    cozy_island_garden:   { name: 'Cozy Island Garden',     icon: '🌴' },
    mood_blocks_tetris:   { name: 'Mood Blocks Tetris',     icon: '🟦' },
    spirit_journey:       { name: 'Spirit Journey',         icon: '✨' },
    stress_relief_ocean:  { name: 'Stress Relief Ocean',    icon: '🌊' }
  };

  /* Badge definitions — condition(playerData) returns true when earned */
  var BADGES = [
    {
      id: 'first_play',
      name: 'First Step',
      desc: 'Played your first game',
      icon: '🌱',
      condition: function (p) { return p.totalGamesPlayed >= 1; }
    },
    {
      id: 'level_5',
      name: 'Rising Mind',
      desc: 'Reached Level 5',
      icon: '⭐',
      condition: function (p) { return p.level >= 5; }
    },
    {
      id: 'level_10',
      name: 'Mindful Master',
      desc: 'Reached Level 10',
      icon: '🌟',
      condition: function (p) { return p.level >= 10; }
    },
    {
      id: 'streak_3',
      name: '3-Day Streak',
      desc: 'Played 3 days in a row',
      icon: '🔥',
      condition: function (p) { return p.currentStreak >= 3; }
    },
    {
      id: 'streak_7',
      name: 'Week Warrior',
      desc: 'Played 7 days in a row',
      icon: '💎',
      condition: function (p) { return p.currentStreak >= 7; }
    },
    {
      id: 'all_games',
      name: 'Explorer',
      desc: 'Played all 7 games at least once',
      icon: '🗺️',
      condition: function (p) {
        return Object.keys(GAMES).every(function (id) {
          return p.games[id] && p.games[id].timesPlayed > 0;
        });
      }
    },
    {
      id: 'xp_1000',
      name: 'XP Hunter',
      desc: 'Earned 1000 total XP',
      icon: '⚡',
      condition: function (p) { return p.totalXP >= 1000; }
    },
    {
      id: 'xp_5000',
      name: 'XP Legend',
      desc: 'Earned 5000 total XP',
      icon: '🏆',
      condition: function (p) { return p.totalXP >= 5000; }
    },
    {
      id: 'breath_10',
      name: 'Breath Keeper',
      desc: 'Played Body & Breath Quest 10 times',
      icon: '🌬️',
      condition: function (p) {
        return p.games['body_breath_quest'] &&
               p.games['body_breath_quest'].timesPlayed >= 10;
      }
    },
    {
      id: 'sudoku_5',
      name: 'Grid Mind',
      desc: 'Completed Calm Grid Sudoku 5 times',
      icon: '🧩',
      condition: function (p) {
        return p.games['calm_grid_sudoku'] &&
               p.games['calm_grid_sudoku'].timesPlayed >= 5;
      }
    },
    {
      id: 'high_score_500',
      name: 'High Flyer',
      desc: 'Scored 500+ in any single game',
      icon: '🚀',
      condition: function (p) {
        return Object.keys(p.games).some(function (id) {
          return p.games[id].bestScore >= 500;
        });
      }
    },
    {
      id: 'high_score_1000',
      name: 'Elite Player',
      desc: 'Scored 1000+ in any single game',
      icon: '👑',
      condition: function (p) {
        return Object.keys(p.games).some(function (id) {
          return p.games[id].bestScore >= 1000;
        });
      }
    }
  ];

  /* ─────────────────────────────────────────────
     STORAGE LAYER
     Swap _storage.get / _storage.set to use
     Firebase Firestore later — nothing else changes.
  ───────────────────────────────────────────── */

  function getCookie(name) {
    if (typeof document === 'undefined') return null;
    var value = "; " + document.cookie;
    var parts = value.split("; " + name + "=");
    if (parts.length === 2) return parts.pop().split(";").shift();
    return null;
  }

  function getStorageKey() {
    var userId = getCookie('manokart_user_id');
    return userId ? 'manokart_engine_v1_' + userId : 'manokart_engine_v1_guest';
  }

  var _storage = {
    get: function () {
      try {
        var key = getStorageKey();
        var raw = localStorage.getItem(key);
        return raw ? JSON.parse(raw) : null;
      } catch (e) {
        console.warn('[GameEngine] Storage read error:', e);
        return null;
      }
    },
    set: function (data) {
      try {
        var key = getStorageKey();
        localStorage.setItem(key, JSON.stringify(data));
        return true;
      } catch (e) {
        console.warn('[GameEngine] Storage write error:', e);
        return false;
      }
    }
  };

  /* ─────────────────────────────────────────────
     DEFAULT PLAYER STATE
  ───────────────────────────────────────────── */

  function _defaultPlayer() {
    var games = {};
    Object.keys(GAMES).forEach(function (id) {
      games[id] = {
        bestScore:   0,
        totalScore:  0,
        timesPlayed: 0,
        history:     []   // [{ score, xpEarned, timestamp }]
      };
    });
    return {
      totalXP:          0,
      level:            1,
      currentStreak:    0,
      longestStreak:    0,
      lastPlayedDate:   null,
      totalGamesPlayed: 0,
      earnedBadges:     [],
      games:            games,
      createdAt:        Date.now()
    };
  }

  /* ─────────────────────────────────────────────
     CORE HELPERS
  ───────────────────────────────────────────── */

  function _loadPlayer() {
    var data = _storage.get();
    if (!data || data.totalXP === undefined) {
      return _defaultPlayer();
    }
    
    // Ensure all default fields exist (for robustness against partial/corrupt save states)
    var defaults = _defaultPlayer();
    Object.keys(defaults).forEach(function (key) {
      if (data[key] === undefined) {
        data[key] = defaults[key];
      }
    });

    if (!data.games) {
      data.games = defaults.games;
    }

    /* Back-fill any new game keys added later */
    Object.keys(GAMES).forEach(function (id) {
      if (!data.games[id]) {
        data.games[id] = { bestScore: 0, totalScore: 0, timesPlayed: 0, history: [] };
      }
    });
    return data;
  }

  function _savePlayer(player) {
    var res = _storage.set(player);
    if (res) {
      _syncWithServer(player);
    }
    return res;
  }

  function _syncWithServer(player) {
    if (typeof fetch === 'undefined') return;
    fetch('/api/progress', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ progress: player })
    })
    .then(function (r) { return r.json(); })
    .then(function (data) {
      if (data && data.ok) {
        console.log('[GameEngine] Progress successfully synced with server.');
      }
    })
    .catch(function (err) {
      console.warn('[GameEngine] Server sync failed:', err);
    });
  }

  function _initSync() {
    if (typeof fetch === 'undefined') return;
    fetch('/api/progress')
      .then(function (r) {
        if (r.status === 401) return null; // not logged in
        return r.json();
      })
      .then(function (data) {
        if (data && data.ok) {
          if (data.progress) {
            var local = _loadPlayer();
            var server = data.progress;
            // Use whichever has more XP
            if (server.totalXP >= local.totalXP) {
              _storage.set(server); // use _storage.set to avoid infinite loop
              console.log('[GameEngine] Restored progress from server.');
            } else {
              // Server has less XP, upload local
              _syncWithServer(local);
            }
          } else {
            // New user with no progress on server. Save/sync default state.
            var local = _loadPlayer();
            _syncWithServer(local);
          }
          if (typeof window !== 'undefined') {
            window.dispatchEvent(new CustomEvent('gameEngineSynced'));
          }
        }
      })
      .catch(function (err) {
        console.warn('[GameEngine] Server sync load failed:', err);
      });
  }

  // Trigger sync on engine load
  if (typeof window !== 'undefined') {
    setTimeout(_initSync, 100);
  }

  function _calcLevel(totalXP) {
    return Math.floor(totalXP / XP_PER_LEVEL) + 1;
  }

  function _calcXPForScore(score, gameId) {
    /*
     * XP formula:
     * Base XP = score (1 point = 1 XP up to 200)
     * Bonus for high scores, capped to keep it fair.
     *
     * Breathing / relaxation games: XP × 1.2 (they require real effort)
     */
    var base = Math.min(score, 200);
    var bonus = score > 200 ? Math.floor((score - 200) * 0.5) : 0;
    var xp = base + bonus;

    var relaxGames = ['body_breath_quest', 'stress_relief_ocean', 'cozy_island_garden', 'spirit_journey'];
    if (relaxGames.indexOf(gameId) !== -1) {
      xp = Math.floor(xp * 1.2);
    }
    return Math.max(1, xp);  // always at least 1 XP for playing
  }

  function _updateStreak(player) {
    var now = Date.now();
    var last = player.lastPlayedDate;
    if (!last) {
      player.currentStreak = 1;
    } else {
      var diff = now - last;
      if (diff < STREAK_WINDOW) {
        /* Same day or within window — don't double-count */
        var sameDay = new Date(now).toDateString() === new Date(last).toDateString();
        if (!sameDay) {
          player.currentStreak += 1;
        }
      } else {
        /* Streak broken */
        player.currentStreak = 1;
      }
    }
    if (player.currentStreak > player.longestStreak) {
      player.longestStreak = player.currentStreak;
    }
    player.lastPlayedDate = now;
    return player;
  }

  function _checkBadges(player) {
    var newlyEarned = [];
    BADGES.forEach(function (badge) {
      if (player.earnedBadges.indexOf(badge.id) === -1) {
        if (badge.condition(player)) {
          player.earnedBadges.push(badge.id);
          newlyEarned.push(badge);
        }
      }
    });
    return newlyEarned;
  }

  /* ─────────────────────────────────────────────
     PUBLIC API
  ───────────────────────────────────────────── */

  var GameEngine = {

    /**
     * GAMES reference — used by hub/profile to display game info.
     */
    GAMES: GAMES,

    /**
     * BADGES reference — full badge list with metadata.
     */
    BADGES: BADGES,

    /**
     * saveScore(gameId, score)
     * ─────────────────────────
     * Call this at the end of every game.
     * Returns a result object with XP earned, level-up info, new badges.
     *
     * Example:
     *   var result = GameEngine.saveScore('body_breath_quest', 320);
     *   if (result.leveledUp) showLevelUpScreen(result.newLevel);
     *   result.newBadges.forEach(b => showBadgeToast(b));
     */
    saveScore: function (gameId, score) {
      if (!GAMES[gameId]) {
        console.warn('[GameEngine] Unknown game id:', gameId, '— valid ids:', Object.keys(GAMES));
        return null;
      }
      score = Math.max(0, Math.round(score));

      var player     = _loadPlayer();
      var prevLevel  = player.level;
      var xpEarned   = _calcXPForScore(score, gameId);
      var gameData   = player.games[gameId];
      var timestamp  = Date.now();

      /* Update game-specific stats */
      gameData.timesPlayed  += 1;
      gameData.totalScore   += score;
      if (score > gameData.bestScore) { gameData.bestScore = score; }

      /* Prepend to history, trim to MAX_HISTORY */
      gameData.history.unshift({ score: score, xpEarned: xpEarned, timestamp: timestamp });
      if (gameData.history.length > MAX_HISTORY) {
        gameData.history = gameData.history.slice(0, MAX_HISTORY);
      }

      /* Update global player stats */
      player.totalXP          += xpEarned;
      player.totalGamesPlayed += 1;
      player.level             = _calcLevel(player.totalXP);

      /* Streak */
      player = _updateStreak(player);

      /* Badges */
      var newBadges = _checkBadges(player);

      _savePlayer(player);

      return {
        gameId:       gameId,
        score:        score,
        xpEarned:     xpEarned,
        totalXP:      player.totalXP,
        level:        player.level,
        leveledUp:    player.level > prevLevel,
        prevLevel:    prevLevel,
        newLevel:     player.level,
        currentStreak: player.currentStreak,
        newBadges:    newBadges,
        isNewBest:    score >= gameData.bestScore
      };
    },

    /**
     * getPlayer()
     * ────────────
     * Returns the full player state object.
     * Use this to build profile pages, hub displays, etc.
     */
    getPlayer: function () {
      return _loadPlayer();
    },

    /**
     * getGameStats(gameId)
     * ─────────────────────
     * Returns stats for one specific game.
     */
    getGameStats: function (gameId) {
      var player = _loadPlayer();
      return player.games[gameId] || null;
    },

    /**
     * getLeaderboard(gameId, limit)
     * ──────────────────────────────
     * Returns top scores for a game from this device's local history.
     * When Firebase is added, this will query Firestore instead.
     *
     * limit defaults to 10.
     */
    getLeaderboard: function (gameId, limit) {
      limit = limit || 10;
      var player = _loadPlayer();
      var history = (player.games[gameId] && player.games[gameId].history) || [];
      var sorted = history.slice().sort(function (a, b) { return b.score - a.score; });
      return sorted.slice(0, limit);
    },

    /**
     * getGlobalSummary()
     * ───────────────────
     * Returns a summary object useful for the hub home screen.
     */
    getGlobalSummary: function () {
      var player = _loadPlayer();
      var xpToNext = XP_PER_LEVEL - (player.totalXP % XP_PER_LEVEL);
      var xpProgress = Math.round(((player.totalXP % XP_PER_LEVEL) / XP_PER_LEVEL) * 100);

      /* Build per-game summary */
      var gameSummaries = Object.keys(GAMES).map(function (id) {
        var g = player.games[id];
        return {
          id:          id,
          name:        GAMES[id].name,
          icon:        GAMES[id].icon,
          bestScore:   g.bestScore,
          timesPlayed: g.timesPlayed,
          lastPlayed:  g.history.length ? g.history[0].timestamp : null
        };
      });

      return {
        level:            player.level,
        totalXP:          player.totalXP,
        xpToNextLevel:    xpToNext,
        xpProgressPct:    xpProgress,
        currentStreak:    player.currentStreak,
        longestStreak:    player.longestStreak,
        totalGamesPlayed: player.totalGamesPlayed,
        badgesEarned:     player.earnedBadges.length,
        totalBadges:      BADGES.length,
        games:            gameSummaries
      };
    },

    /**
     * getBadgeDetails(badgeId)
     * ─────────────────────────
     * Returns full badge metadata for a given id.
     */
    getBadgeDetails: function (badgeId) {
      for (var i = 0; i < BADGES.length; i++) {
        if (BADGES[i].id === badgeId) { return BADGES[i]; }
      }
      return null;
    },

    /**
     * getEarnedBadges()
     * ──────────────────
     * Returns full badge objects for all badges the player has earned.
     */
    getEarnedBadges: function () {
      var player = _loadPlayer();
      return player.earnedBadges.map(function (id) {
        return GameEngine.getBadgeDetails(id);
      }).filter(Boolean);
    },

    /**
     * getLevelInfo()
     * ───────────────
     * Returns current level, XP progress, XP needed — useful for XP bars.
     */
    getLevelInfo: function () {
      var player      = _loadPlayer();
      var xpInLevel   = player.totalXP % XP_PER_LEVEL;
      var xpToNext    = XP_PER_LEVEL - xpInLevel;
      var progressPct = Math.round((xpInLevel / XP_PER_LEVEL) * 100);
      return {
        level:       player.level,
        totalXP:     player.totalXP,
        xpInLevel:   xpInLevel,
        xpToNext:    xpToNext,
        progressPct: progressPct,
        xpPerLevel:  XP_PER_LEVEL
      };
    },

    /**
     * resetPlayer()
     * ──────────────
     * Wipes all progress. Use only for testing or a "reset account" button.
     */
    resetPlayer: function () {
      _savePlayer(_defaultPlayer());
      console.info('[GameEngine] Player data reset.');
    },

    /**
     * exportData()
     * ─────────────
     * Returns the raw player JSON — useful for backup or Firebase migration.
     */
    exportData: function () {
      return JSON.stringify(_loadPlayer(), null, 2);
    },

    /**
     * importData(jsonString)
     * ──────────────────────
     * Restores player data from a JSON string (e.g. from Firebase).
     */
    importData: function (jsonString) {
      try {
        var data = JSON.parse(jsonString);
        _savePlayer(data);
        return true;
      } catch (e) {
        console.error('[GameEngine] Import failed:', e);
        return false;
      }
    }
  };

  /* ─────────────────────────────────────────────
     EXPOSE GLOBALLY
  ───────────────────────────────────────────── */
  global.GameEngine = GameEngine;

}(typeof window !== 'undefined' ? window : this));
