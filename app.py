import requests  # <--- tambahkan ini di atas, di bagian import
import os
import json
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from dotenv import load_dotenv
import google.generativeai as genai

# Load environment variables
load_dotenv()

# Configure Gemini API
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))
model = genai.GenerativeModel('gemini-2.0-flash')
SPOTIFY_TOKEN = os.getenv("SPOTIFY_ACCESS_TOKEN", "")

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "secret-key")

KNOWLEDGE_FILE = "knowledge.json"

def load_knowledge():
    if os.path.exists(KNOWLEDGE_FILE):
        with open(KNOWLEDGE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"base_knowledge": "", "link_knowledge": []}

def save_knowledge(data):
    with open(KNOWLEDGE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_spotify_link(song_name):
    """Cari link Spotify berdasarkan judul lagu"""
    if not SPOTIFY_TOKEN:
        return None, None

    query = song_name.replace(" ", "%20")
    url = f"https://api.spotify.com/v1/search?q={query}&type=track&limit=1"
    headers = {"Authorization": f"Bearer {SPOTIFY_TOKEN}"}

    try:
        response = requests.get(url, headers=headers)
        data = response.json()
        if data.get("tracks") and data["tracks"]["items"]:
            track = data["tracks"]["items"][0]
            track_name = track["name"]
            artist_name = track["artists"][0]["name"]
            track_id = track["id"]
            spotify_link = f"https://open.spotify.com/track/{track_id}"
            return f"{track_name} - {artist_name}", spotify_link
    except Exception:
        pass

    return None, None

@app.route("/", methods=["GET"])
def home():
    return redirect(url_for("chat"))

@app.route("/chat", methods=["GET", "POST"])
def chat():
    if "history" not in session:
        session["history"] = []
    knowledge = load_knowledge()
    error = None
    if request.method == "POST":
        user_message = request.form.get("message", "")
        # Gabungkan knowledge + history + pesan user
        prompt = ""
        if knowledge.get("base_knowledge"):
            prompt += f"{knowledge['base_knowledge']}\n"
        if knowledge.get("link_knowledge"):
            prompt += f"Referensi: {', '.join(knowledge['link_knowledge'])}\n"
        # Tambahkan history
        for h in session["history"]:
            prompt += f"User: {h['user']}\nBot: {h['bot']}\n"
        prompt += f"User: {user_message}\nBot:"

        try:
            response = model.generate_content(prompt)
            bot_message = response.text.strip()
        except Exception as e:
            bot_message = ""
            error = f"Error: {str(e)}"
        # Simpan ke history
        session["history"].append({"user": user_message, "bot": bot_message})
        session.modified = True

    return render_template("chat.html", history=session.get("history", []), error=error)

@app.route("/settings", methods=["GET", "POST"])
def settings():
    knowledge = load_knowledge()
    if request.method == "POST":
        base_knowledge = request.form.get("base_knowledge", "")
        link_knowledge = request.form.get("link_knowledge", "")
        links = [l.strip() for l in link_knowledge.splitlines() if l.strip()]
        knowledge = {
            "base_knowledge": base_knowledge,
            "link_knowledge": links
        }
        save_knowledge(knowledge)
        return redirect(url_for("settings"))
    return render_template("settings.html", knowledge=knowledge)

@app.route("/reset", methods=["POST"])
def reset():
    session.pop("history", None)
    return redirect(url_for("chat"))

if __name__ == "__main__":
    app.run(debug=True , port=5100)