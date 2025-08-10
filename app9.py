#!/usr/bin/env python3
import os
import sqlite3
from pathlib import Path
from datetime import datetime
from dotenv import load_dotenv
from flask import Flask, request, jsonify, send_from_directory, abort, make_response
from flask_cors import CORS

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

load_dotenv()

APP_DIR = Path(__file__).parent.resolve()
MEDIA_ROOT = APP_DIR / "media"
MUSIC_ROOT = MEDIA_ROOT / "music"

for m in ("happy", "neutral", "sad", "surprised", "angry"):
    (MUSIC_ROOT / m).mkdir(parents=True, exist_ok=True)

DB_PATH = APP_DIR / "moodmix.db"

# Load secrets from environment variables (set these locally in your .env file)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_SECRET = os.getenv("OPENAI_SECRET")

SPOTIFY_PLAYLISTS = {
    "happy": "https://open.spotify.com/playlist/37i9dQZF1DXdPec7aLTmlC",
    "neutral": "https://open.spotify.com/playlist/37i9dQZF1DX3Ogo9pFvBkY",
    "sad": "https://open.spotify.com/playlist/37i9dQZF1DX7qK8ma5wgG1",
    "surprised": "https://open.spotify.com/playlist/37i9dQZF1DX1mtPaXXY7dB",
    "angry": "https://open.spotify.com/playlist/37i9dQZF1DX3YSRoSdA634"
}

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        """CREATE TABLE IF NOT EXISTS mood_event (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            mood TEXT NOT NULL,
            score REAL DEFAULT 1.0,
            created_at TEXT NOT NULL
        );"""
    )
    conn.commit()
    conn.close()

init_db()

app = Flask(__name__)
app.config["SECRET_KEY"] = SECRET_KEY
CORS(app)

def db_insert_mood(mood, score=1.0):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO mood_event (mood, score, created_at) VALUES (?, ?, ?)",
        (mood, float(score), datetime.utcnow().isoformat()),
    )
    conn.commit()
    conn.close()

def list_local_music_for_mood(mood):
    folder = MUSIC_ROOT / mood
    if not folder.exists():
        return []
    files = [f for f in sorted(os.listdir(folder)) if f.lower().endswith(('.mp3', '.wav', '.ogg'))]
    return [f"/media/music/{mood}/{f}" for f in files]

@app.route("/api/playlist", methods=["GET"])
def api_playlist():
    mood = request.args.get("mood", "neutral")
    mood = mood if mood in ("happy","neutral","sad","surprised","angry") else "neutral"
    url = SPOTIFY_PLAYLISTS.get(mood, "")
    local_files = list_local_music_for_mood(mood)
    return jsonify({
        "mood": mood,
        "spotify_url": url,
        "local_files": local_files,
    })

@app.route("/api/mood-event", methods=["POST"])
def api_mood_event():
    data = request.get_json() or {}
    mood = data.get("mood", "neutral")
    score = data.get("score", 1.0)
    try:
        db_insert_mood(mood, score)
        return jsonify({"status":"ok","mood":mood,"score":score}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/api/generate-lyrics", methods=["POST"])
def api_generate_lyrics():
    if not OPENAI_API_KEY:
        return jsonify({"error":"OpenAI API key not configured"}), 400
    if not OPENAI_AVAILABLE:
        return jsonify({"error":"OpenAI python library not installed"}), 500
    body = request.get_json() or {}
    mood = body.get("mood", "neutral")
    prompt = f"Write a short 4-line uplifting poem or chorus about feeling {mood}. Keep it simple and positive."
    try:
        openai.api_key = OPENAI_API_KEY
        resp = openai.Completion.create(
            engine="text-davinci-003",
            prompt=prompt,
            max_tokens=120,
            temperature=0.8,
        )
        text = resp.choices[0].text.strip()
        return jsonify({"lyrics": text})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/media/<path:filename>")
def media_serve(filename):
    requested = (MEDIA_ROOT / filename).resolve()
    if not str(requested).startswith(str(MEDIA_ROOT.resolve())) or not requested.exists():
        abort(404)
    directory = requested.parent
    return send_from_directory(directory, requested.name, conditional=True)

@app.route('/weights/<path:filename>')
def serve_weights(filename):
    weights_dir = APP_DIR / 'weights'
    requested = (weights_dir / filename).resolve()
    if not str(requested).startswith(str(weights_dir.resolve())) or not requested.exists():
        abort(404)
    return send_from_directory(weights_dir, filename)

@app.route("/", methods=["GET"])
def index():
    html = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>MoodMix</title>
  <style>
    body{margin:0;font-family:system-ui,Segoe UI,Roboto,Arial;background:#111;color:#fff}
    header{padding:14px;background:linear-gradient(90deg,#0b3d91,#2b6be6)}
    main{display:flex;gap:12px;padding:12px}
    #visual{flex:1}
    #controls{width:360px}
    #webcam{width:320px;height:240px;border-radius:8px;border:2px solid rgba(255,255,255,0.08)}
    #mood-label{font-size:18px;margin-top:10px}
    #play-btn{
      display:inline-block;padding:10px 14px;margin-top:10px;background:#1db954;border:none;border-radius:6px;color:#fff;cursor:pointer;
    }
    #lyrics-area{margin-top:12px;white-space:pre-wrap;background:rgba(255,255,255,0.04);padding:8px;border-radius:6px}
    canvas{width:100%;height:auto;border-radius:6px;display:block}
    .small{font-size:0.85rem;color:#ddd}
  </style>
</head>
<body>
  <header><h1 style="margin:0">MoodMix — single-file web app</h1></header>
  <main>
    <div id="visual">
      <canvas id="canvas" width="960" height="540"></canvas>
      <div class="small" style="padding:8px">Visuals react to detected mood</div>
    </div>
    <div id="controls">
      <video id="webcam" autoplay muted playsinline></video>
      <div id="mood-label">Mood: <strong id="mood-val">neutral</strong></div>
      <button id="play-btn">Play Playlist</button>
      <div id="lyrics-area">Lyrics will appear here when available.</div>
      <div class="small" style="margin-top:8px">Tip: Add .mp3 files to media/music/&lt;mood&gt;/ to use local playback</div>
    </div>
  </main>

  <script src="https://cdn.jsdelivr.net/npm/face-api.js@0.22.2/dist/face-api.min.js"></script>

  <script>
  (async function(){
    const video = document.getElementById('webcam');
    const moodVal = document.getElementById('mood-val');
    const playBtn = document.getElementById('play-btn');
    const lyricsArea = document.getElementById('lyrics-area');
    const canvas = document.getElementById('canvas');
    const ctx = canvas.getContext('2d');

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
      video.srcObject = stream;
    } catch(err) {
      alert('Camera access denied or unavailable. Please allow camera access for this site.');
      console.error(err);
      return;
    }

    try {
      await faceapi.nets.tinyFaceDetector.loadFromUri('/weights');
      await faceapi.nets.faceExpressionNet.loadFromUri('/weights');
    } catch(e) {
      console.warn('face-api model load failure:', e);
    }

    let lastMood = 'neutral';
    const buff = [];
    const buffLen = 6;

    async function tick() {
      if(video.readyState < 2) {
        requestAnimationFrame(tick);
        return;
      }
      let detection = null;
      try {
        detection = await faceapi.detectSingleFace(video, new faceapi.TinyFaceDetectorOptions()).withFaceExpressions();
      } catch(e) {
        detection = null;
      }
      let mood = 'neutral';
      if(detection && detection.expressions) {
        const exps = detection.expressions;
        const sorted = Object.entries(exps).sort((a,b) => b[1] - a[1]);
        const label = sorted[0][0];
        if(label==='happy') mood='happy';
        else if(label==='surprised') mood='surprised';
        else if(label==='angry') mood='angry';
        else if(label==='sad') mood='sad';
        else mood='neutral';
      }
      buff.push(mood);
      if(buff.length > buffLen) buff.shift();
      const counts = {};
      buff.forEach(m => counts[m] = (counts[m]||0) + 1);
      const smoothed = Object.keys(counts).reduce((a,b) => counts[a] > counts[b] ? a : b);
      if(smoothed !== lastMood) {
        lastMood = smoothed;
        moodVal.textContent = smoothed;
        fetch('/api/mood-event', {
          method:'POST',
          headers:{'Content-Type':'application/json'},
          body: JSON.stringify({mood: smoothed, score: 1.0})
        }).catch(() => {});
      }
      drawVisual(smoothed);
      requestAnimationFrame(tick);
    }

    function drawVisual(mood) {
      const map = {
        'happy': ['#FFD76B','#FF8A00'],
        'neutral': ['#9FB1FF','#6C8CE3'],
        'sad': ['#2B5AA8','#12224B'],
        'surprised': ['#D6A3FF','#7C4DFF'],
        'angry': ['#FF6B6B','#8E0C0C']
      };
      const cols = map[mood] || map['neutral'];
      const g = ctx.createLinearGradient(0,0,canvas.width,canvas.height);
      g.addColorStop(0, cols[0]);
      g.addColorStop(1, cols[1]);
      ctx.fillStyle = g;
      ctx.fillRect(0,0,canvas.width,canvas.height);

      const t = Date.now() / 1000;
      for(let i=0; i<8; i++) {
        const x = (i*130 + (t*30*(i%3+1))) % canvas.width;
        const y = canvas.height/2 + Math.sin(t*(0.3 + i*0.12)) * 120;
        const r = 40 + (i % 4) * 10;
        ctx.beginPath();
        ctx.globalAlpha = 0.12;
        ctx.fillStyle = '#FFFFFF';
        ctx.arc(x, y, r, 0, Math.PI*2);
        ctx.fill();
        ctx.globalAlpha = 1;
      }

      try {
        const ww = 200, hh = 150;
        ctx.drawImage(video, canvas.width - ww - 12, canvas.height - hh - 12, ww, hh);
        ctx.strokeStyle = 'rgba(255,255,255,0.6)';
        ctx.strokeRect(canvas.width - ww - 12, canvas.height - hh - 12, ww, hh);
      } catch(e) {}
    }

    playBtn.addEventListener('click', async () => {
      const mood = lastMood || 'neutral';
      console.log("Play button clicked. Current mood:", mood);
      const win = window.open('', '_blank');
      if (!win) {
        alert("Please enable popups for this site");
        return;
      }
      try {
        const res = await fetch(`/api/playlist?mood=${encodeURIComponent(mood)}`);
        if(!res.ok) {
          console.error("API /api/playlist failed:", res.status);
          alert("Failed to get playlist from server");
          win.close();
          return;
        }
        const j = await res.json();
        console.log("Playlist API response:", j);
        if(j.spotify_url) {
          console.log("Opening Spotify URL:", j.spotify_url);
          win.location = j.spotify_url;
          return;
        }
        if(j.local_files && j.local_files.length > 0) {
          const f = j.local_files[Math.floor(Math.random() * j.local_files.length)];
          console.log("Opening local file:", f);
          win.location = f;
        } else {
          alert('No playlist configured for mood: ' + mood);
          win.close();
        }
      } catch(e) {
        console.error("Error fetching playlist:", e);
        alert("Error fetching playlist");
        win.close();
      }
    });

    async function fetchLyricsIfWanted() {
      if(!lastMood || lastMood === 'neutral') return;
      try {
        const r = await fetch('/api/generate-lyrics', {
          method: 'POST',
          headers: {'Content-Type': 'application/json'},
          body: JSON.stringify({mood: lastMood})
        });
        if(r.ok) {
          const j = await r.json();
          if(j.lyrics) lyricsArea.textContent = j.lyrics;
        }
      } catch(e) {}
    }
    setInterval(fetchLyricsIfWanted, 30000);

    tick();
  })();
  </script>
</body>
</html>
"""
    resp = make_response(html)
    resp.headers["Content-Type"] = "text/html; charset=utf-8"
    return resp

if __name__ == "__main__":
    print(f"Starting MoodMix app at http://0.0.0.0:5000")
    if OPENAI_API_KEY:
        print("OpenAI API key found — lyrics endpoint enabled.")
    else:
        print("OpenAI API key NOT found — lyrics disabled.")
    app.run(host="0.0.0.0", port=5000, debug=True)
