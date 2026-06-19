import { jsxDEV as _jsxDEV } from "react/jsx-dev-runtime";
// React hooks are provided as globals via the HTML shell (UMD build)
// const { useState, useEffect, useRef, useCallback } = React;

// ── Config ───────────────────────────────────────────────────
const API = "/api";
const MOODS = [{
  label: "Joyful",
  emoji: "☀️",
  value: 5,
  color: "#EF9F27",
  bg: "#FAEEDA",
  border: "#FAC775"
}, {
  label: "Happy",
  emoji: "🌸",
  value: 4,
  color: "#D4537E",
  bg: "#FBEAF0",
  border: "#F4C0D1"
}, {
  label: "Calm",
  emoji: "🌿",
  value: 3,
  color: "#1D9E75",
  bg: "#E1F5EE",
  border: "#9FE1CB"
}, {
  label: "Sad",
  emoji: "🌧️",
  value: 2,
  color: "#378ADD",
  bg: "#E6F1FB",
  border: "#B5D4F4"
}, {
  label: "Anxious",
  emoji: "🌪️",
  value: 1,
  color: "#993556",
  bg: "#FBEAF0",
  border: "#F4C0D1"
}];
const SUGGESTED_TAGS = ["gratitude", "growth", "family", "work", "health", "creative", "anxious", "hopeful", "tired", "proud", "nature", "social"];
const PROMPTS = ["What made you smile today? 🌷", "What are you grateful for right now? 🍃", "Describe your day in three words... 🌙", "What did you learn about yourself today? 🦋", "What's one small win you had today? ✨", "How did your body feel today? 🌸", "What emotion visited you most today? 🌊", "What would you tell your past self today? 🕊️"];

// ── Helpers ───────────────────────────────────────────────────
const todayKey = () => new Date().toISOString().split("T")[0];
const fmt = d => new Date(d + "T12:00:00").toLocaleDateString("en-US", {
  weekday: "long",
  month: "long",
  day: "numeric"
});
const short = d => new Date(d + "T12:00:00").toLocaleDateString("en-US", {
  month: "short",
  day: "numeric"
});
const getMood = v => MOODS.find(m => m.value === v) || MOODS[2];

// ── Build diary-aware system prompt ──────────────────────────
function buildSystemPrompt(entries) {
  const today = todayKey();
  const todayEntry = entries[today];
  const recent = Object.values(entries).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 5);
  let context = `You are a warm, empathetic companion integrated into someone's personal mindful diary app called "My Little Sanctuary". Your role is to be a gentle, supportive friend — not a therapist. You already know how this person has been feeling because you have access to their diary entries.

Respond with care and emotional awareness. Keep replies concise (2-4 sentences usually), warm, and grounded in what they've shared. Don't be preachy. If they seem sad or anxious, acknowledge it gently before offering anything. If they seem joyful, celebrate with them. Always feel human, never clinical.

--- DIARY CONTEXT ---`;
  if (todayEntry) {
    const m = getMood(todayEntry.mood);
    context += `\n\nTODAY (${fmt(today)}):
Mood: ${m.label} ${m.emoji} (${todayEntry.mood}/5)
Tags: ${(todayEntry.tags || []).map(t => '#' + t).join(', ') || 'none'}
Entry: "${(todayEntry.text || '').slice(0, 400)}${todayEntry.text?.length > 400 ? '...' : ''}"`;
  } else {
    context += `\n\nThe person has not written a diary entry today yet.`;
  }
  if (recent.length > 0) {
    const others = recent.filter(e => e.date !== today).slice(0, 3);
    if (others.length > 0) {
      context += `\n\nRECENT ENTRIES:`;
      others.forEach(e => {
        const m = getMood(e.mood);
        context += `\n- ${fmt(e.date)}: ${m.label} ${m.emoji} — "${(e.text || '').slice(0, 120)}..."`;
      });
    }
  }
  context += `\n\nUse this context to inform your tone and responses, but don't quote their diary back at them unless they ask. Just let it shape how you understand and respond to them.`;
  return context;
}

// ── Tag Pill ──────────────────────────────────────────────────
function TagPill({
  tag,
  onRemove,
  color = "#1D9E75",
  bg = "#E1F5EE"
}) {
  return /*#__PURE__*/_jsxDEV("span", {
    style: {
      display: "inline-flex",
      alignItems: "center",
      gap: 4,
      padding: "3px 10px",
      borderRadius: 99,
      background: bg,
      color,
      fontSize: 12,
      fontFamily: "Georgia,serif",
      border: `1px solid ${color}30`
    },
    children: ["#", tag, onRemove && /*#__PURE__*/_jsxDEV("span", {
      onClick: onRemove,
      style: {
        cursor: "pointer",
        fontWeight: 700,
        opacity: 0.6,
        marginLeft: 2
      },
      children: "×"
    }, void 0, false)]
  }, void 0, true);
}

// ── Photo Thumbnail ───────────────────────────────────────────
function PhotoThumb({
  url,
  onRemove
}) {
  return /*#__PURE__*/_jsxDEV("div", {
    style: {
      position: "relative",
      width: 80,
      height: 80,
      borderRadius: 10,
      overflow: "hidden",
      border: "1.5px solid #9FE1CB40",
      flexShrink: 0
    },
    children: [/*#__PURE__*/_jsxDEV("img", {
      src: url.startsWith("/api") ? `http://localhost:5000${url}` : url,
      alt: "",
      style: {
        width: "100%",
        height: "100%",
        objectFit: "cover"
      }
    }, void 0, false), onRemove && /*#__PURE__*/_jsxDEV("button", {
      onClick: onRemove,
      style: {
        position: "absolute",
        top: 3,
        right: 3,
        width: 18,
        height: 18,
        borderRadius: "50%",
        background: "rgba(0,0,0,0.55)",
        border: "none",
        color: "white",
        fontSize: 11,
        cursor: "pointer",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        lineHeight: 1
      },
      children: "×"
    }, void 0, false)]
  }, void 0, true);
}

// ── Mood-Aware Chatbot Panel ──────────────────────────────────
function ChatPanel({
  entries,
  onClose
}) {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [greeted, setGreeted] = useState(false);
  const bottomRef = useRef(null);
  const inputRef = useRef(null);

  // Auto-scroll
  useEffect(() => {
    bottomRef.current?.scrollIntoView({
      behavior: "smooth"
    });
  }, [messages, loading]);

  // Opening greeting based on today's mood
  useEffect(() => {
    if (greeted) return;
    setGreeted(true);
    const today = todayKey();
    const todayEntry = entries[today];
    let greeting;
    if (todayEntry) {
      const m = getMood(todayEntry.mood);
      if (m.value >= 4) greeting = `I can see today's been a ${m.label.toLowerCase()} day for you ${m.emoji} I'm here if you'd like to talk about it, or anything else on your mind.`;else if (m.value === 3) greeting = `Hey 🌿 Looks like today's been a calm one. How are you feeling right now?`;else greeting = `Hey, I noticed today felt a bit ${m.label.toLowerCase()} ${m.emoji} I'm here. Want to talk about it, or just chat?`;
    } else {
      greeting = "Hey 🌿 You haven't written today's entry yet — no pressure. How are you feeling right now?";
    }
    setMessages([{
      role: "assistant",
      content: greeting
    }]);
  }, [entries, greeted]);
  const sendMessage = async () => {
    const trimmed = input.trim();
    if (!trimmed || loading) return;
    const userMsg = {
      role: "user",
      content: trimmed
    };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setLoading(true);

    // Build conversation for API (exclude the greeting from history if it's the only msg)
    const apiMessages = newMessages.map(m => ({
      role: m.role,
      content: m.content
    }));
    try {
      const res = await fetch(`${API}/chat`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: trimmed,
          session_id: "diary_session"
        })
      });
      const data = await res.json();
      const reply = data.reply || "I'm here 🌿";
      setMessages(prev => [...prev, {
        role: "assistant",
        content: reply
      }]);
    } catch {
      setMessages(prev => [...prev, {
        role: "assistant",
        content: "Sorry, I couldn't connect right now 🌿 Try again in a moment."
      }]);
    }
    setLoading(false);
    setTimeout(() => inputRef.current?.focus(), 50);
  };
  const today = todayKey();
  const todayEntry = entries[today];
  const todayMood = todayEntry ? getMood(todayEntry.mood) : null;
  return /*#__PURE__*/_jsxDEV("div", {
    style: {
      position: "fixed",
      bottom: 90,
      right: 24,
      width: 340,
      maxHeight: "70vh",
      background: "white",
      borderRadius: 24,
      boxShadow: "0 8px 48px rgba(15,110,86,.18)",
      border: "0.5px solid #9FE1CB60",
      display: "flex",
      flexDirection: "column",
      zIndex: 100,
      overflow: "hidden",
      animation: "slideUp .25s ease"
    },
    children: [/*#__PURE__*/_jsxDEV("div", {
      style: {
        background: "linear-gradient(135deg,#E1F5EE,#FBEAF0 60%,#FAEEDA)",
        padding: "14px 18px",
        display: "flex",
        alignItems: "center",
        gap: 10,
        borderBottom: "0.5px solid #9FE1CB30"
      },
      children: [/*#__PURE__*/_jsxDEV("div", {
        style: {
          width: 36,
          height: 36,
          borderRadius: "50%",
          background: "linear-gradient(135deg,#5DCAA5,#9FE1CB)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 18,
          flexShrink: 0
        },
        children: "🌿"
      }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
        style: {
          flex: 1
        },
        children: [/*#__PURE__*/_jsxDEV("div", {
          style: {
            fontSize: 14,
            fontWeight: 700,
            color: "#0F6E56",
            fontFamily: "Georgia,serif"
          },
          children: "Your Sanctuary Companion"
        }, void 0, false), todayMood ? /*#__PURE__*/_jsxDEV("div", {
          style: {
            fontSize: 11,
            color: "#5DCAA5",
            fontStyle: "italic"
          },
          children: ["Feeling ", todayMood.label, " today ", todayMood.emoji]
        }, void 0, true) : /*#__PURE__*/_jsxDEV("div", {
          style: {
            fontSize: 11,
            color: "#5DCAA5",
            fontStyle: "italic"
          },
          children: "Here for you, always 🌱"
        }, void 0, false)]
      }, void 0, true), /*#__PURE__*/_jsxDEV("button", {
        onClick: onClose,
        style: {
          background: "none",
          border: "none",
          fontSize: 18,
          color: "#B4B2A9",
          cursor: "pointer",
          lineHeight: 1,
          padding: 4
        },
        children: "×"
      }, void 0, false)]
    }, void 0, true), todayEntry && /*#__PURE__*/_jsxDEV("div", {
      style: {
        padding: "8px 14px",
        background: "#f5fcf9",
        borderBottom: "0.5px solid #E1F5EE",
        display: "flex",
        alignItems: "center",
        gap: 6
      },
      children: [/*#__PURE__*/_jsxDEV("span", {
        style: {
          fontSize: 11
        },
        children: todayMood.emoji
      }, void 0, false), /*#__PURE__*/_jsxDEV("span", {
        style: {
          fontSize: 11,
          color: "#5DCAA5",
          fontStyle: "italic",
          fontFamily: "Georgia,serif"
        },
        children: ["Reading your ", todayMood.label.toLowerCase(), " diary entry from today"]
      }, void 0, true)]
    }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
      style: {
        flex: 1,
        overflowY: "auto",
        padding: "14px 14px 8px",
        display: "flex",
        flexDirection: "column",
        gap: 10
      },
      children: [messages.map((m, i) => /*#__PURE__*/_jsxDEV("div", {
        style: {
          display: "flex",
          justifyContent: m.role === "user" ? "flex-end" : "flex-start"
        },
        children: [m.role === "assistant" && /*#__PURE__*/_jsxDEV("div", {
          style: {
            width: 26,
            height: 26,
            borderRadius: "50%",
            background: "linear-gradient(135deg,#5DCAA5,#9FE1CB)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13,
            flexShrink: 0,
            marginRight: 7,
            marginTop: 2
          },
          children: "🌿"
        }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
          style: {
            maxWidth: "78%",
            padding: "9px 13px",
            borderRadius: m.role === "user" ? "18px 18px 4px 18px" : "18px 18px 18px 4px",
            background: m.role === "user" ? "linear-gradient(135deg,#0F6E56,#1D9E75)" : "#f5fcf9",
            color: m.role === "user" ? "white" : "#2C2C2A",
            fontSize: 13,
            lineHeight: 1.6,
            fontFamily: "Georgia,serif",
            border: m.role === "user" ? "none" : "0.5px solid #E1F5EE"
          },
          children: m.content
        }, void 0, false)]
      }, i, true)), loading && /*#__PURE__*/_jsxDEV("div", {
        style: {
          display: "flex",
          alignItems: "center",
          gap: 8
        },
        children: [/*#__PURE__*/_jsxDEV("div", {
          style: {
            width: 26,
            height: 26,
            borderRadius: "50%",
            background: "linear-gradient(135deg,#5DCAA5,#9FE1CB)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 13
          },
          children: "🌿"
        }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
          style: {
            padding: "9px 14px",
            background: "#f5fcf9",
            borderRadius: "18px 18px 18px 4px",
            border: "0.5px solid #E1F5EE"
          },
          children: /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 4,
              alignItems: "center"
            },
            children: [0, 1, 2].map(i => /*#__PURE__*/_jsxDEV("div", {
              style: {
                width: 6,
                height: 6,
                borderRadius: "50%",
                background: "#9FE1CB",
                animation: `bounce 1.2s ease ${i * 0.2}s infinite`
              }
            }, i, false))
          }, void 0, false)
        }, void 0, false)]
      }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
        ref: bottomRef
      }, void 0, false)]
    }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
      style: {
        padding: "10px 12px",
        borderTop: "0.5px solid #E1F5EE",
        display: "flex",
        gap: 8,
        alignItems: "flex-end"
      },
      children: [/*#__PURE__*/_jsxDEV("textarea", {
        ref: inputRef,
        value: input,
        onChange: e => setInput(e.target.value),
        onKeyDown: e => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
          }
        },
        placeholder: "Say something...",
        rows: 1,
        style: {
          flex: 1,
          padding: "9px 13px",
          borderRadius: 14,
          border: "1.5px solid #D3D1C760",
          fontSize: 13,
          fontFamily: "Georgia,serif",
          color: "#2C2C2A",
          resize: "none",
          outline: "none",
          lineHeight: 1.5,
          maxHeight: 80,
          overflowY: "auto",
          background: "#fafaf8"
        }
      }, void 0, false), /*#__PURE__*/_jsxDEV("button", {
        onClick: sendMessage,
        disabled: !input.trim() || loading,
        style: {
          width: 36,
          height: 36,
          borderRadius: "50%",
          border: "none",
          cursor: input.trim() && !loading ? "pointer" : "not-allowed",
          background: input.trim() && !loading ? "linear-gradient(135deg,#0F6E56,#1D9E75)" : "#E1F5EE",
          color: "white",
          fontSize: 15,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
          transition: "all .2s"
        },
        children: "➤"
      }, void 0, false)]
    }, void 0, true)]
  }, void 0, true);
}

// ══════════════════════════════════════════════════════════════
function MindfulDiary() {
  const [entries, setEntries] = useState({});
  const [view, setView] = useState("write");
  const [selDate, setSelDate] = useState(todayKey());
  const [text, setText] = useState("");
  const [mood, setMood] = useState(null);
  const [tags, setTags] = useState([]);
  const [photos, setPhotos] = useState([]);
  const [tagInput, setTagInput] = useState("");
  const [saved, setSaved] = useState(false);
  const [saving, setSaving] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [aiInsight, setAiInsight] = useState("");
  const [aiLoading, setAiLoading] = useState(false);
  const [analytics, setAnalytics] = useState(null);
  const [toastMsg, setToastMsg] = useState("");
  const [chatOpen, setChatOpen] = useState(false);
  const [prompt] = useState(() => PROMPTS[Math.floor(Math.random() * PROMPTS.length)]);
  const fileInputRef = useRef(null);

  // Voice recording
  const [isVoiceRec, setIsVoiceRec] = useState(false);
  const recognitionRef = useRef(null);
  const last7 = Array.from({
    length: 7
  }, (_, i) => {
    const d = new Date();
    d.setDate(d.getDate() - (6 - i));
    return d.toISOString().split("T")[0];
  });

  // ── Toast ────────────────────────────────────────────────
  const toast = msg => {
    setToastMsg(msg);
    setTimeout(() => setToastMsg(""), 2600);
  };

  // ── Load all entries ─────────────────────────────────────
  const loadEntries = useCallback(async () => {
    try {
      const r = await fetch(`${API}/entries`);
      const d = await r.json();
      setEntries(d.entries || {});
    } catch {
      try {
        setEntries(JSON.parse(localStorage.getItem("diary_entries") || "{}"));
      } catch {}
    }
  }, []);
  useEffect(() => {
    loadEntries();
  }, [loadEntries]);
  useEffect(() => {
    if (view === "analytics") {
      fetch(`${API}/analytics`).then(r => r.json()).then(setAnalytics).catch(() => {});
    }
  }, [view]);
  useEffect(() => {
    const e = entries[selDate];
    if (e) {
      setText(e.text || "");
      setMood(e.mood ?? null);
      setTags(e.tags || []);
      setPhotos(e.photos || []);
    } else {
      setText("");
      setMood(null);
      setTags([]);
      setPhotos([]);
    }
    setSaved(false);
    setAiInsight("");
  }, [selDate, entries]);
  useEffect(() => {
    return () => {
      if (recognitionRef.current) {
        recognitionRef.current.manualStop = true;
        recognitionRef.current.stop();
      }
    };
  }, []);

  // ── Save entry ───────────────────────────────────────────
  const saveEntry = async () => {
    if (!text.trim() || mood === null) return;
    setSaving(true);
    const payload = {
      text,
      mood,
      tags,
      photos: photos.map(p => p.url)
    };
    try {
      const r = await fetch(`${API}/entries/${selDate}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
      });
      const d = await r.json();
      setEntries(prev => ({
        ...prev,
        [selDate]: d.entry
      }));
      setSaved(true);
      toast("Entry saved 🌿");
      setTimeout(() => setSaved(false), 2500);
    } catch {
      const entry = {
        date: selDate,
        text,
        mood,
        tags,
        photos: photos.map(p => p.url),
        updated: new Date().toISOString()
      };
      setEntries(prev => {
        const n = {
          ...prev,
          [selDate]: entry
        };
        localStorage.setItem("diary_entries", JSON.stringify(n));
        return n;
      });
      setSaved(true);
      toast("Saved locally (server offline) 🌿");
      setTimeout(() => setSaved(false), 2500);
    }
    setSaving(false);
  };

  // ── Photo upload ─────────────────────────────────────────
  const handleFileChange = async e => {
    const files = Array.from(e.target.files);
    if (!files.length) return;
    setUploading(true);
    for (const file of files) {
      const fd = new FormData();
      fd.append("file", file);
      try {
        const r = await fetch(`${API}/upload`, {
          method: "POST",
          body: fd
        });
        const d = await r.json();
        if (d.url) setPhotos(prev => [...prev, {
          url: d.url,
          filename: d.filename
        }]);
      } catch {
        const localUrl = URL.createObjectURL(file);
        setPhotos(prev => [...prev, {
          url: localUrl,
          filename: file.name
        }]);
      }
    }
    setUploading(false);
    e.target.value = "";
  };

  // ── Voice Recording (FIXED) ──────────────────────────────
  const toggleVoice = () => {
    const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!SR) {
      toast('Voice not supported — use Chrome or Edge 🎙️');
      return;
    }
    if (isVoiceRec) {
      if (recognitionRef.current) {
        recognitionRef.current.manualStop = true;
        recognitionRef.current.stop();
        recognitionRef.current = null;
      }
      setIsVoiceRec(false);
      toast('Voice recording stopped 🎙️');
      return;
    }
    const rec = new SR();
    rec.continuous = true;
    rec.interimResults = true;
    rec.lang = 'en-US';
    rec.manualStop = false;
    rec.onresult = e => {
      let final = '';
      for (let i = e.resultIndex; i < e.results.length; i++) {
        if (e.results[i].isFinal) final += e.results[i][0].transcript + ' ';
      }
      if (final) setText(prev => prev + final);
    };
    rec.onerror = e => {
      if (e.error === 'no-speech' || e.error === 'aborted') return;
      setIsVoiceRec(false);
      recognitionRef.current = null;
      toast('Mic error: ' + e.error);
    };
    rec.onend = () => {
      const current = recognitionRef.current;
      if (current && !current.manualStop) {
        try {
          current.start();
        } catch (_) {}
      }
    };
    recognitionRef.current = rec;
    rec.start();
    setIsVoiceRec(true);
    toast('Listening... speak now 🎙️');
  };

  // ── Tag helpers ──────────────────────────────────────────
  const addTag = t => {
    const clean = t.trim().toLowerCase().replace(/[^a-z0-9_-]/g, "");
    if (clean && !tags.includes(clean)) setTags(prev => [...prev, clean]);
    setTagInput("");
  };

  // ── AI Analysis ──────────────────────────────────────────
  const analyzeWithAI = async () => {
    const recent = Object.values(entries).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 7);
    if (!recent.length) {
      setAiInsight("Write a few diary entries first so I can understand your patterns! 🌱");
      return;
    }
    setAiLoading(true);
    setAiInsight("");
    const summary = recent.map(e => `Date: ${e.date}, Mood: ${getMood(e.mood).label} (${e.mood}/5)\nEntry: ${(e.text || "").slice(0, 200)}`).join("\n\n");
    try {
      const r = await fetch(`${API}/analyze`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          summary
        })
      });
      const d = await r.json();
      setAiInsight(d.insight || "No insight returned.");
    } catch {
      setAiInsight("Couldn't reach the AI right now. Make sure ANTHROPIC_API_KEY is set on the server 🌿");
    }
    setAiLoading(false);
  };

  // ── PDF Export ────────────────────────────────────────────
  const exportPDF = () => {
    window.open(`${API}/export/pdf`, "_blank");
    toast("Preparing your diary PDF 📄");
  };

  // ── Derived ───────────────────────────────────────────────
  const dist = analytics?.distribution || {};
  const totalEntries = Object.keys(entries).length;
  const todayEntry = entries[todayKey()];
  const todayMood = todayEntry ? getMood(todayEntry.mood) : null;

  // ══════════════════════════════════════════════════════════
  return /*#__PURE__*/_jsxDEV("div", {
    style: {
      fontFamily: "Georgia,serif",
      minHeight: "100vh",
      background: "linear-gradient(160deg,#f7fdf9 0%,#fdf4f8 60%,#fffbf2 100%)",
      position: "relative"
    },
    children: [/*#__PURE__*/_jsxDEV("style", {
      children: `
        @keyframes fadeUp{from{opacity:0;transform:translateY(10px)}to{opacity:1;transform:translateY(0)}}
        @keyframes floatPetal{0%,100%{transform:translateY(0) rotate(0deg)}50%{transform:translateY(-16px) rotate(6deg)}}
        @keyframes toastIn{0%{opacity:0;transform:translateX(-50%) translateY(12px)}100%{opacity:1;transform:translateX(-50%) translateY(0)}}
        @keyframes pulse{0%,100%{box-shadow:0 0 0 4px rgba(231,76,60,.2)}50%{box-shadow:0 0 0 8px rgba(231,76,60,.1)}}
        @keyframes slideUp{from{opacity:0;transform:translateY(16px)}to{opacity:1;transform:translateY(0)}}
        @keyframes bounce{0%,80%,100%{transform:translateY(0)}40%{transform:translateY(-6px)}}
        @keyframes chatPulse{0%,100%{box-shadow:0 4px 24px rgba(15,110,86,.3)}50%{box-shadow:0 4px 32px rgba(15,110,86,.55)}}
        .page{animation:fadeUp .4s ease}
        .mood-pill:hover{transform:scale(1.12)!important;transition:all .2s!important}
        .day-chip:hover{background:rgba(93,202,165,.12)!important}
        .nav-pill:hover{background:rgba(93,202,165,.12)!important}
        .entry-row:hover{background:#f0fbf6!important}
        textarea{resize:none;outline:none;border:none;background:transparent}
        textarea::placeholder{color:#B4B2A9}
        input[type=file]{display:none}
        ::-webkit-scrollbar{width:4px}::-webkit-scrollbar-thumb{background:#9FE1CB;border-radius:99px}
      `
    }, void 0, false), [{
      w: 160,
      h: 160,
      bg: "#9FE1CB",
      t: -30,
      r: -30,
      d: "0s"
    }, {
      w: 100,
      h: 100,
      bg: "#FAC775",
      b: 60,
      l: -20,
      d: "3s"
    }, {
      w: 75,
      h: 75,
      bg: "#F4C0D1",
      t: "42%",
      r: 10,
      d: "5.5s"
    }].map((p, i) => /*#__PURE__*/_jsxDEV("div", {
      style: {
        position: "fixed",
        width: p.w,
        height: p.h,
        borderRadius: "50% 0 50% 0",
        background: p.bg,
        opacity: 0.1,
        top: p.t,
        right: p.r,
        bottom: p.b,
        left: p.l,
        animation: `floatPetal 9s ease-in-out ${p.d} infinite`,
        pointerEvents: "none",
        zIndex: 0
      }
    }, i, false)), toastMsg && /*#__PURE__*/_jsxDEV("div", {
      style: {
        position: "fixed",
        bottom: 28,
        left: "50%",
        transform: "translateX(-50%)",
        background: "#0F6E56",
        color: "white",
        padding: "10px 22px",
        borderRadius: 99,
        fontSize: 13,
        fontFamily: "Georgia,serif",
        zIndex: 999,
        animation: "toastIn .3s ease",
        whiteSpace: "nowrap",
        boxShadow: "0 4px 24px rgba(15,110,86,.25)"
      },
      children: toastMsg
    }, void 0, false), chatOpen && /*#__PURE__*/_jsxDEV(ChatPanel, {
      entries: entries,
      onClose: () => setChatOpen(false)
    }, void 0, false), /*#__PURE__*/_jsxDEV("button", {
      onClick: () => setChatOpen(o => !o),
      title: "Chat with your sanctuary companion",
      style: {
        position: "fixed",
        bottom: 24,
        right: 24,
        width: 56,
        height: 56,
        borderRadius: "50%",
        border: "none",
        cursor: "pointer",
        zIndex: 101,
        background: chatOpen ? "#1D9E75" : "linear-gradient(135deg,#0F6E56,#1D9E75)",
        color: "white",
        fontSize: 24,
        boxShadow: "0 4px 24px rgba(15,110,86,.3)",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        animation: !chatOpen && todayEntry ? "chatPulse 3s ease infinite" : "none",
        transition: "all .25s"
      },
      children: chatOpen ? "×" : "🌿"
    }, void 0, false), !chatOpen && todayMood && /*#__PURE__*/_jsxDEV("div", {
      style: {
        position: "fixed",
        bottom: 86,
        right: 24,
        background: "#0F6E56",
        color: "white",
        padding: "5px 12px",
        borderRadius: 99,
        fontSize: 11,
        fontFamily: "Georgia,serif",
        whiteSpace: "nowrap",
        zIndex: 101,
        pointerEvents: "none",
        boxShadow: "0 2px 12px rgba(15,110,86,.2)",
        fontStyle: "italic"
      },
      children: ["I know you're feeling ", todayMood.label.toLowerCase(), " today ", todayMood.emoji]
    }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
      style: {
        background: "linear-gradient(135deg,#E1F5EE,#FBEAF0 55%,#FAEEDA)",
        borderBottom: "0.5px solid #9FE1CB30",
        padding: "20px 24px 0",
        position: "relative",
        zIndex: 1
      },
      children: /*#__PURE__*/_jsxDEV("div", {
        style: {
          maxWidth: 780,
          margin: "0 auto"
        },
        children: [/*#__PURE__*/_jsxDEV("div", {
          style: {
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            flexWrap: "wrap",
            gap: 10
          },
          children: [/*#__PURE__*/_jsxDEV("div", {
            children: [/*#__PURE__*/_jsxDEV("a", {
              href: "/",
              style: {
                textDecoration: "none"
              },
              children: /*#__PURE__*/_jsxDEV("h1", {
                style: {
                  margin: 0,
                  fontSize: 24,
                  fontWeight: 700,
                  color: "#0F6E56",
                  letterSpacing: "-0.3px"
                },
                children: "🌿 My Little Sanctuary"
              }, void 0, false)
            }, void 0, false), /*#__PURE__*/_jsxDEV("p", {
              style: {
                margin: "2px 0 0",
                fontSize: 13,
                color: "#5DCAA5",
                fontStyle: "italic"
              },
              children: "A safe space, just for you"
            }, void 0, false)]
          }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 8,
              flexWrap: "wrap",
              alignItems: "center"
            },
            children: [/*#__PURE__*/_jsxDEV("a", {
              href: "/",
              style: {
                textDecoration: "none"
              },
              children: /*#__PURE__*/_jsxDEV("button", {
                className: "nav-pill",
                style: {
                  padding: "7px 16px",
                  borderRadius: 99,
                  border: "1.5px solid #C0E0C840",
                  background: "transparent",
                  color: "#888780",
                  fontSize: 13,
                  fontFamily: "Georgia,serif",
                  cursor: "pointer"
                },
                children: "🏠 Home"
              }, void 0, false)
            }, void 0, false), [["write", "✍️ Write"], ["analytics", "📊 Insights"]].map(([v, lbl]) => /*#__PURE__*/_jsxDEV("button", {
              className: "nav-pill",
              onClick: () => setView(v),
              style: {
                padding: "7px 16px",
                borderRadius: 99,
                border: `1.5px solid ${view === v ? "#5DCAA5" : "#C0E0C840"}`,
                background: view === v ? "rgba(93,202,165,.15)" : "transparent",
                color: view === v ? "#0F6E56" : "#888780",
                fontSize: 13,
                fontFamily: "Georgia,serif",
                cursor: "pointer",
                transition: "all .2s"
              },
              children: lbl
            }, v, false)), /*#__PURE__*/_jsxDEV("button", {
              onClick: exportPDF,
              style: {
                padding: "7px 16px",
                borderRadius: 99,
                border: "1.5px solid #FAC77560",
                background: "rgba(250,199,117,.12)",
                color: "#854F0B",
                fontSize: 13,
                fontFamily: "Georgia,serif",
                cursor: "pointer"
              },
              children: "📄 Export PDF"
            }, void 0, false), /*#__PURE__*/_jsxDEV("a", {
              href: "/profile",
              style: {
                textDecoration: "none"
              },
              children: /*#__PURE__*/_jsxDEV("button", {
                className: "nav-pill",
                style: {
                  padding: "7px 16px",
                  borderRadius: 99,
                  border: "1.5px solid #C0E0C840",
                  background: "transparent",
                  color: "#888780",
                  fontSize: 13,
                  fontFamily: "Georgia,serif",
                  cursor: "pointer"
                },
                children: "👤 Profile"
              }, void 0, false)
            }, void 0, false)]
          }, void 0, true)]
        }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
          style: {
            display: "flex",
            gap: 6,
            marginTop: 14,
            paddingBottom: 1,
            overflowX: "auto"
          },
          children: last7.map(d => {
            const e = entries[d];
            const m = e ? getMood(e.mood) : null;
            const isSel = d === selDate;
            return /*#__PURE__*/_jsxDEV("button", {
              className: "day-chip",
              onClick: () => {
                setSelDate(d);
                setView("write");
              },
              style: {
                flexShrink: 0,
                padding: "8px 12px",
                borderRadius: 12,
                border: `${isSel ? "2px solid #5DCAA5" : "1.5px solid #C0E0C830"}`,
                background: isSel ? "white" : "rgba(255,255,255,.5)",
                cursor: "pointer",
                textAlign: "center",
                transition: "all .2s",
                boxShadow: isSel ? "0 2px 14px rgba(93,202,165,.18)" : "none"
              },
              children: [/*#__PURE__*/_jsxDEV("div", {
                style: {
                  fontSize: 18
                },
                children: m ? m.emoji : "·"
              }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
                style: {
                  fontSize: 11,
                  color: isSel ? "#0F6E56" : "#888780",
                  marginTop: 2
                },
                children: short(d)
              }, void 0, false)]
            }, d, true);
          })
        }, void 0, false)]
      }, void 0, true)
    }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
      style: {
        maxWidth: 780,
        margin: "0 auto",
        padding: "24px 24px 60px",
        position: "relative",
        zIndex: 1
      },
      children: [view === "write" && /*#__PURE__*/_jsxDEV("div", {
        className: "page",
        children: [/*#__PURE__*/_jsxDEV("h2", {
          style: {
            margin: "0 0 4px",
            fontSize: 19,
            color: "#0F6E56",
            fontWeight: 600
          },
          children: fmt(selDate)
        }, void 0, false), /*#__PURE__*/_jsxDEV("p", {
          style: {
            margin: "0 0 20px",
            color: "#5DCAA5",
            fontSize: 14,
            fontStyle: "italic"
          },
          children: prompt
        }, void 0, false), /*#__PURE__*/_jsxDEV("p", {
          style: {
            margin: "0 0 10px",
            fontSize: 12,
            color: "#888780",
            letterSpacing: ".08em"
          },
          children: "HOW ARE YOU FEELING?"
        }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
          style: {
            display: "flex",
            gap: 8,
            flexWrap: "wrap",
            marginBottom: 20
          },
          children: MOODS.map(m => /*#__PURE__*/_jsxDEV("button", {
            className: "mood-pill",
            onClick: () => setMood(m.value),
            style: {
              padding: "7px 15px",
              borderRadius: 99,
              cursor: "pointer",
              border: `${mood === m.value ? `2px solid ${m.color}` : `1.5px solid ${m.border}`}`,
              background: mood === m.value ? m.bg : "white",
              display: "flex",
              alignItems: "center",
              gap: 6,
              transition: "all .2s",
              boxShadow: mood === m.value ? `0 2px 14px ${m.color}35` : "none"
            },
            children: [/*#__PURE__*/_jsxDEV("span", {
              style: {
                fontSize: 18
              },
              children: m.emoji
            }, void 0, false), /*#__PURE__*/_jsxDEV("span", {
              style: {
                fontSize: 13,
                color: mood === m.value ? m.color : "#888780",
                fontWeight: mood === m.value ? 600 : 400
              },
              children: m.label
            }, void 0, false)]
          }, m.value, true))
        }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
          style: {
            background: "white",
            borderRadius: 20,
            border: "0.5px solid #E1F5EE",
            boxShadow: "0 4px 28px rgba(93,202,165,.07)",
            position: "relative",
            overflow: "hidden",
            minHeight: 260,
            marginBottom: 16
          },
          children: [/*#__PURE__*/_jsxDEV("div", {
            style: {
              position: "absolute",
              inset: 0,
              backgroundImage: "repeating-linear-gradient(to bottom,transparent,transparent 31px,#E1F5EE50 31px,#E1F5EE50 32px)",
              backgroundPosition: "0 48px",
              pointerEvents: "none"
            }
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              position: "absolute",
              left: 52,
              top: 0,
              bottom: 0,
              width: 1,
              background: "#F4C0D160"
            }
          }, void 0, false), /*#__PURE__*/_jsxDEV("textarea", {
            value: text,
            onChange: e => setText(e.target.value),
            placeholder: "Begin writing here, dear friend... let your thoughts flow like water 💧",
            style: {
              width: "100%",
              minHeight: 260,
              padding: "22px 22px 28px 68px",
              fontSize: 16,
              lineHeight: "32px",
              color: "#2C2C2A",
              boxSizing: "border-box",
              fontFamily: "Georgia,serif"
            }
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              position: "absolute",
              bottom: 10,
              right: 14,
              fontSize: 12,
              color: "#B4B2A9",
              display: "flex",
              alignItems: "center",
              gap: 10
            },
            children: [text.trim().split(/\s+/).filter(Boolean).length, " words", /*#__PURE__*/_jsxDEV("button", {
              onClick: toggleVoice,
              title: isVoiceRec ? 'Stop recording' : 'Voice input',
              style: {
                width: 32,
                height: 32,
                borderRadius: '50%',
                border: 'none',
                cursor: 'pointer',
                background: isVoiceRec ? '#E74C3C' : 'linear-gradient(135deg,#EF9F27,#f0c060)',
                color: 'white',
                fontSize: 14,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                boxShadow: isVoiceRec ? '0 0 0 4px rgba(231,76,60,.2)' : '0 2px 8px rgba(239,159,39,.3)',
                animation: isVoiceRec ? 'pulse 1.5s infinite' : 'none',
                transition: 'all .2s'
              },
              children: isVoiceRec ? '⏹' : '🎙️'
            }, void 0, false)]
          }, void 0, true)]
        }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
          style: {
            marginBottom: 16
          },
          children: [/*#__PURE__*/_jsxDEV("p", {
            style: {
              margin: "0 0 8px",
              fontSize: 12,
              color: "#888780",
              letterSpacing: ".08em"
            },
            children: "PHOTOS"
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 10,
              flexWrap: "wrap",
              alignItems: "flex-start"
            },
            children: [photos.map((p, i) => /*#__PURE__*/_jsxDEV(PhotoThumb, {
              url: p.url,
              onRemove: () => setPhotos(prev => prev.filter((_, j) => j !== i))
            }, i, false)), /*#__PURE__*/_jsxDEV("button", {
              onClick: () => fileInputRef.current?.click(),
              disabled: uploading,
              style: {
                width: 80,
                height: 80,
                borderRadius: 10,
                border: "1.5px dashed #9FE1CB",
                background: "#f5fcf9",
                color: "#5DCAA5",
                fontSize: 24,
                cursor: "pointer",
                flexShrink: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center"
              },
              children: uploading ? "⏳" : "+"
            }, void 0, false), /*#__PURE__*/_jsxDEV("input", {
              ref: fileInputRef,
              type: "file",
              accept: "image/*",
              multiple: true,
              onChange: handleFileChange
            }, void 0, false)]
          }, void 0, true)]
        }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
          style: {
            marginBottom: 20
          },
          children: [/*#__PURE__*/_jsxDEV("p", {
            style: {
              margin: "0 0 8px",
              fontSize: 12,
              color: "#888780",
              letterSpacing: ".08em"
            },
            children: "TAGS"
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
              marginBottom: 8
            },
            children: tags.map(t => /*#__PURE__*/_jsxDEV(TagPill, {
              tag: t,
              onRemove: () => setTags(prev => prev.filter(x => x !== t))
            }, t, false))
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
              marginBottom: 8
            },
            children: SUGGESTED_TAGS.filter(t => !tags.includes(t)).slice(0, 8).map(t => /*#__PURE__*/_jsxDEV("button", {
              onClick: () => addTag(t),
              style: {
                padding: "3px 10px",
                borderRadius: 99,
                border: "1px dashed #9FE1CB60",
                background: "transparent",
                color: "#888780",
                fontSize: 12,
                cursor: "pointer",
                fontFamily: "Georgia,serif"
              },
              children: ["+", t]
            }, t, true))
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 8
            },
            children: [/*#__PURE__*/_jsxDEV("input", {
              value: tagInput,
              onChange: e => setTagInput(e.target.value),
              onKeyDown: e => {
                if ((e.key === "Enter" || e.key === ",") && tagInput.trim()) {
                  e.preventDefault();
                  addTag(tagInput);
                }
              },
              placeholder: "Add custom tag...",
              style: {
                padding: "6px 14px",
                borderRadius: 99,
                border: "1.5px solid #D3D1C760",
                fontSize: 13,
                fontFamily: "Georgia,serif",
                color: "#2C2C2A",
                width: 180,
                outline: "none",
                background: "white"
              }
            }, void 0, false), /*#__PURE__*/_jsxDEV("button", {
              onClick: () => addTag(tagInput),
              style: {
                padding: "6px 14px",
                borderRadius: 99,
                border: "1.5px solid #9FE1CB",
                background: "transparent",
                color: "#0F6E56",
                fontSize: 13,
                cursor: "pointer",
                fontFamily: "Georgia,serif"
              },
              children: "Add"
            }, void 0, false)]
          }, void 0, true)]
        }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
          style: {
            display: "flex",
            gap: 12,
            alignItems: "center",
            flexWrap: "wrap"
          },
          children: [/*#__PURE__*/_jsxDEV("button", {
            onClick: saveEntry,
            disabled: !text.trim() || mood === null || saving,
            style: {
              padding: "11px 30px",
              borderRadius: 99,
              border: "1.5px solid #5DCAA5",
              background: saved ? "#5DCAA5" : "transparent",
              color: saved ? "white" : "#0F6E56",
              fontSize: 15,
              fontFamily: "Georgia,serif",
              cursor: !text.trim() || mood === null || saving ? "not-allowed" : "pointer",
              opacity: !text.trim() || mood === null ? .5 : 1,
              transition: "all .25s"
            },
            children: saving ? "Saving..." : saved ? "✓ Saved ✨" : "Save this entry 🌿"
          }, void 0, false), entries[selDate] && /*#__PURE__*/_jsxDEV("span", {
            style: {
              fontSize: 13,
              color: "#9FE1CB",
              fontStyle: "italic"
            },
            children: "Entry exists for this day"
          }, void 0, false), saved && /*#__PURE__*/_jsxDEV("button", {
            onClick: () => setChatOpen(true),
            style: {
              padding: "11px 20px",
              borderRadius: 99,
              border: "1.5px solid #0F6E56",
              background: "linear-gradient(135deg,#0F6E56,#1D9E75)",
              color: "white",
              fontSize: 13,
              fontFamily: "Georgia,serif",
              cursor: "pointer",
              animation: "fadeUp .4s ease"
            },
            children: "🌿 Chat about it"
          }, void 0, false)]
        }, void 0, true)]
      }, void 0, true), view === "analytics" && /*#__PURE__*/_jsxDEV("div", {
        className: "page",
        children: [/*#__PURE__*/_jsxDEV("div", {
          style: {
            display: "flex",
            justifyContent: "space-between",
            alignItems: "flex-start",
            marginBottom: 20,
            flexWrap: "wrap",
            gap: 10
          },
          children: [/*#__PURE__*/_jsxDEV("div", {
            children: [/*#__PURE__*/_jsxDEV("h2", {
              style: {
                margin: "0 0 4px",
                color: "#0F6E56",
                fontSize: 19,
                fontWeight: 600
              },
              children: "Your Mood Journey 🌊"
            }, void 0, false), /*#__PURE__*/_jsxDEV("p", {
              style: {
                margin: 0,
                color: "#5DCAA5",
                fontSize: 14,
                fontStyle: "italic"
              },
              children: "A gentle look at your emotional landscape"
            }, void 0, false)]
          }, void 0, true), /*#__PURE__*/_jsxDEV("button", {
            onClick: exportPDF,
            style: {
              padding: "8px 18px",
              borderRadius: 99,
              border: "1.5px solid #FAC77570",
              background: "rgba(250,199,117,.1)",
              color: "#854F0B",
              fontSize: 13,
              cursor: "pointer",
              fontFamily: "Georgia,serif"
            },
            children: "📄 Export Full Diary"
          }, void 0, false)]
        }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
          style: {
            display: "grid",
            gridTemplateColumns: "repeat(3,1fr)",
            gap: 12,
            marginBottom: 20
          },
          children: [{
            icon: "📖",
            val: analytics?.total_entries ?? totalEntries,
            lbl: "Total Entries"
          }, {
            icon: "🔥",
            val: analytics?.streak ?? "—",
            lbl: "Day Streak"
          }, {
            icon: "🌸",
            val: analytics?.avg_mood ? `${analytics.avg_mood}/5` : "—",
            lbl: "Avg Mood"
          }].map(s => /*#__PURE__*/_jsxDEV("div", {
            style: {
              background: "white",
              borderRadius: 16,
              border: "0.5px solid #E1F5EE",
              padding: "14px 18px",
              textAlign: "center",
              boxShadow: "0 2px 14px rgba(93,202,165,.05)"
            },
            children: [/*#__PURE__*/_jsxDEV("div", {
              style: {
                fontSize: 24,
                marginBottom: 4
              },
              children: s.icon
            }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
              style: {
                fontSize: 22,
                fontWeight: 700,
                color: "#0F6E56"
              },
              children: s.val
            }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
              style: {
                fontSize: 12,
                color: "#888780",
                marginTop: 2
              },
              children: s.lbl
            }, void 0, false)]
          }, s.lbl, true))
        }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
          style: {
            background: "white",
            borderRadius: 20,
            border: "0.5px solid #E1F5EE",
            padding: "18px 22px",
            marginBottom: 16,
            boxShadow: "0 2px 14px rgba(93,202,165,.05)"
          },
          children: [/*#__PURE__*/_jsxDEV("h3", {
            style: {
              margin: "0 0 14px",
              fontSize: 14,
              color: "#0F6E56",
              fontWeight: 600
            },
            children: "Last 7 Days"
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 10,
              alignItems: "flex-end",
              height: 120
            },
            children: last7.map(d => {
              const e = entries[d];
              const m = e ? getMood(e.mood) : null;
              const h = m ? m.value / 5 * 100 : 0;
              return /*#__PURE__*/_jsxDEV("div", {
                style: {
                  flex: 1,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  gap: 5
                },
                children: [/*#__PURE__*/_jsxDEV("div", {
                  style: {
                    fontSize: 16,
                    height: 22
                  },
                  children: m ? m.emoji : ""
                }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
                  style: {
                    width: "100%",
                    background: "#F1EFE8",
                    borderRadius: 8,
                    height: 80,
                    display: "flex",
                    alignItems: "flex-end",
                    overflow: "hidden"
                  },
                  children: /*#__PURE__*/_jsxDEV("div", {
                    style: {
                      width: "100%",
                      height: `${h}%`,
                      background: m ? m.color : "transparent",
                      borderRadius: 8,
                      transition: "height .5s ease",
                      opacity: .8
                    }
                  }, void 0, false)
                }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
                  style: {
                    fontSize: 10,
                    color: "#888780",
                    textAlign: "center"
                  },
                  children: short(d)
                }, void 0, false)]
              }, d, true);
            })
          }, void 0, false)]
        }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
          style: {
            background: "white",
            borderRadius: 20,
            border: "0.5px solid #E1F5EE",
            padding: "18px 22px",
            marginBottom: 16,
            boxShadow: "0 2px 14px rgba(93,202,165,.05)"
          },
          children: [/*#__PURE__*/_jsxDEV("h3", {
            style: {
              margin: "0 0 14px",
              fontSize: 14,
              color: "#0F6E56",
              fontWeight: 600
            },
            children: "Mood Breakdown"
          }, void 0, false), MOODS.map(m => {
            const count = dist[m.value] || 0;
            const pct = analytics?.total_entries > 0 ? Math.round(count / analytics.total_entries * 100) : 0;
            return /*#__PURE__*/_jsxDEV("div", {
              style: {
                display: "flex",
                alignItems: "center",
                gap: 10,
                marginBottom: 9
              },
              children: [/*#__PURE__*/_jsxDEV("span", {
                style: {
                  width: 22,
                  fontSize: 17
                },
                children: m.emoji
              }, void 0, false), /*#__PURE__*/_jsxDEV("span", {
                style: {
                  width: 58,
                  fontSize: 13,
                  color: "#5F5E5A"
                },
                children: m.label
              }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
                style: {
                  flex: 1,
                  height: 9,
                  background: "#F1EFE8",
                  borderRadius: 99,
                  overflow: "hidden"
                },
                children: /*#__PURE__*/_jsxDEV("div", {
                  style: {
                    height: "100%",
                    width: `${pct}%`,
                    background: m.color,
                    borderRadius: 99,
                    transition: "width .6s ease"
                  }
                }, void 0, false)
              }, void 0, false), /*#__PURE__*/_jsxDEV("span", {
                style: {
                  width: 36,
                  fontSize: 12,
                  color: "#888780",
                  textAlign: "right"
                },
                children: [count, "×"]
              }, void 0, true)]
            }, m.value, true);
          })]
        }, void 0, true), analytics?.top_tags?.length > 0 && /*#__PURE__*/_jsxDEV("div", {
          style: {
            background: "white",
            borderRadius: 20,
            border: "0.5px solid #E1F5EE",
            padding: "18px 22px",
            marginBottom: 16,
            boxShadow: "0 2px 14px rgba(93,202,165,.05)"
          },
          children: [/*#__PURE__*/_jsxDEV("h3", {
            style: {
              margin: "0 0 12px",
              fontSize: 14,
              color: "#0F6E56",
              fontWeight: 600
            },
            children: "Your Most-Used Tags 🏷️"
          }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              gap: 8,
              flexWrap: "wrap"
            },
            children: analytics.top_tags.map(([tag, count]) => /*#__PURE__*/_jsxDEV("div", {
              style: {
                display: "flex",
                alignItems: "center",
                gap: 4
              },
              children: [/*#__PURE__*/_jsxDEV(TagPill, {
                tag: tag
              }, void 0, false), /*#__PURE__*/_jsxDEV("span", {
                style: {
                  fontSize: 11,
                  color: "#B4B2A9"
                },
                children: [count, "×"]
              }, void 0, true)]
            }, tag, true))
          }, void 0, false)]
        }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
          style: {
            background: "linear-gradient(135deg,#E1F5EE,#FBEAF0)",
            borderRadius: 20,
            padding: "18px 22px",
            border: "0.5px solid #9FE1CB40",
            marginBottom: 16
          },
          children: [/*#__PURE__*/_jsxDEV("div", {
            style: {
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: 10,
              flexWrap: "wrap",
              gap: 8
            },
            children: [/*#__PURE__*/_jsxDEV("h3", {
              style: {
                margin: 0,
                fontSize: 14,
                color: "#0F6E56",
                fontWeight: 600
              },
              children: "✨ Gentle AI Reflection"
            }, void 0, false), /*#__PURE__*/_jsxDEV("button", {
              onClick: analyzeWithAI,
              disabled: aiLoading,
              style: {
                padding: "6px 16px",
                borderRadius: 99,
                border: "1.5px solid #5DCAA5",
                background: "white",
                color: "#0F6E56",
                fontSize: 12,
                fontFamily: "Georgia,serif",
                cursor: aiLoading ? "wait" : "pointer",
                opacity: aiLoading ? .7 : 1
              },
              children: aiLoading ? "Thinking... 🌿" : "Analyze my entries ✨"
            }, void 0, false)]
          }, void 0, true), aiInsight ? /*#__PURE__*/_jsxDEV("p", {
            style: {
              margin: 0,
              fontSize: 14,
              lineHeight: 1.8,
              color: "#0F6E56",
              fontStyle: "italic",
              animation: "fadeUp .5s ease"
            },
            children: aiInsight
          }, void 0, false) : /*#__PURE__*/_jsxDEV("p", {
            style: {
              margin: 0,
              fontSize: 13,
              color: "#5DCAA5",
              fontStyle: "italic"
            },
            children: "Click \"Analyze my entries\" for a warm reflection on your mood journey 🌊"
          }, void 0, false)]
        }, void 0, true), totalEntries > 0 && /*#__PURE__*/_jsxDEV("div", {
          children: [/*#__PURE__*/_jsxDEV("h3", {
            style: {
              margin: "0 0 12px",
              fontSize: 14,
              color: "#0F6E56",
              fontWeight: 600
            },
            children: "Recent Pages 📖"
          }, void 0, false), Object.values(entries).sort((a, b) => b.date.localeCompare(a.date)).slice(0, 6).map(e => {
            const m = getMood(e.mood);
            return /*#__PURE__*/_jsxDEV("div", {
              className: "entry-row",
              onClick: () => {
                setSelDate(e.date);
                setView("write");
              },
              style: {
                display: "flex",
                gap: 12,
                padding: "11px 14px",
                borderRadius: 14,
                cursor: "pointer",
                marginBottom: 8,
                transition: "background .2s",
                border: "0.5px solid #E1F5EE",
                background: "white"
              },
              children: [/*#__PURE__*/_jsxDEV("span", {
                style: {
                  fontSize: 20
                },
                children: m.emoji
              }, void 0, false), /*#__PURE__*/_jsxDEV("div", {
                style: {
                  flex: 1,
                  minWidth: 0
                },
                children: [/*#__PURE__*/_jsxDEV("div", {
                  style: {
                    display: "flex",
                    alignItems: "center",
                    gap: 8,
                    flexWrap: "wrap"
                  },
                  children: [/*#__PURE__*/_jsxDEV("span", {
                    style: {
                      fontSize: 13,
                      color: "#0F6E56",
                      fontWeight: 600
                    },
                    children: fmt(e.date)
                  }, void 0, false), (e.tags || []).slice(0, 2).map(t => /*#__PURE__*/_jsxDEV(TagPill, {
                    tag: t
                  }, t, false)), (e.photos || []).length > 0 && /*#__PURE__*/_jsxDEV("span", {
                    style: {
                      fontSize: 11,
                      color: "#B4B2A9"
                    },
                    children: ["📷 ", e.photos.length]
                  }, void 0, true)]
                }, void 0, true), /*#__PURE__*/_jsxDEV("div", {
                  style: {
                    fontSize: 13,
                    color: "#888780",
                    marginTop: 3,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap"
                  },
                  children: [(e.text || "").slice(0, 90), (e.text || "").length > 90 ? "…" : ""]
                }, void 0, true)]
              }, void 0, true), /*#__PURE__*/_jsxDEV("span", {
                style: {
                  fontSize: 12,
                  color: m.color,
                  fontWeight: 600,
                  alignSelf: "center",
                  flexShrink: 0
                },
                children: m.label
              }, void 0, false)]
            }, e.date, true);
          })]
        }, void 0, true)]
      }, void 0, true)]
    }, void 0, true)]
  }, void 0, true);
}
