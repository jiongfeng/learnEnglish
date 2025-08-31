from __future__ import annotations
from flask import Flask, render_template_string, request, jsonify, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import (
    LoginManager, UserMixin, login_user, logout_user,
    login_required, current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os, json, requests

# ---------------------------- App & DB ----------------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-change-me')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///app.db')
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {"pool_pre_ping": True}
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

# API 未登录时返回 JSON 401
@login_manager.unauthorized_handler
def _unauth_handler():
    if request.path.startswith('/api'):
        return jsonify({"ok": False, "error": "unauthorized"}), 401
    return redirect(url_for('login'))

# ---------------------------- Models ----------------------------
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, unique=True)
    daily_new_limit = db.Column(db.Integer, default=20)
    hide_answer = db.Column(db.Boolean, default=True)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Card(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    word = db.Column(db.String(255), nullable=False)
    translation = db.Column(db.Text, nullable=False)
    example = db.Column(db.Text, default='')
    phonetic = db.Column(db.String(255), default='')
    audio_url = db.Column(db.String(1024), default='')
    image_url = db.Column(db.String(1024), default='')
    status = db.Column(db.String(20), default='new')  # new|learning|review
    repetitions = db.Column(db.Integer, default=0)
    interval = db.Column(db.Integer, default=0)  # days
    ease = db.Column(db.Float, default=2.5)
    next_review = db.Column(db.Date, nullable=True)
    first_learned_at = db.Column(db.DateTime)
    last_reviewed_at = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (db.UniqueConstraint('user_id', 'word', name='uq_user_word'),)

with app.app_context():
    db.create_all()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ----------------------- External Integrations -----------------------\NDICT_API = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"
PIXABAY_KEY = os.getenv('PIXABAY_KEY', '').strip()
LIBRETRANSLATE_URL = os.getenv('LIBRETRANSLATE_URL', '').strip()

def fetch_dictionary(word: str):
    try:
        r = requests.get(DICT_API.format(word), timeout=10)
        if r.status_code != 200:
            return {}
        data = r.json()
        if not isinstance(data, list) or not data:
            return {}
        entry = data[0]
        phonetic = entry.get('phonetic') or ''
        audio = ''
        for ph in entry.get('phonetics', []) or []:
            if ph.get('audio'):
                audio = ph['audio']
                if not phonetic:
                    phonetic = ph.get('text', '')
                break
        meaning_text = ''
        example = ''
        for m in entry.get('meanings', []) or []:
            defs = m.get('definitions') or []
            if defs:
                meaning_text = defs[0].get('definition', '')
                example = defs[0].get('example', '') or ''
                if meaning_text:
                    break
        return {"definition_en": meaning_text, "example_en": example, "phonetic": phonetic, "audio": audio}
    except Exception:
        return {}

def translate_to_zh(text: str) -> str:
    text = (text or '').strip()
    if not text:
        return ''
    if not LIBRETRANSLATE_URL:
        return text
    try:
        url = LIBRETRANSLATE_URL.rstrip('/') + '/translate'
        payload = {"q": text, "source": "en", "target": "zh", "format": "text"}
        r = requests.post(url, json=payload, timeout=10)
        if r.status_code == 200:
            out = r.json()
            return out.get('translatedText', text)
        return text
    except Exception:
        return text

def fetch_image(word: str) -> str:
    if not PIXABAY_KEY:
        return ''
    try:
        params = {'key': PIXABAY_KEY, 'q': word, 'image_type': 'photo', 'per_page': 3, 'safesearch': 'true'}
        r = requests.get('https://pixabay.com/api/', params=params, timeout=10)
        if r.status_code == 200:
            hits = r.json().get('hits', [])
            if hits:
                return hits[0].get('webformatURL') or hits[0].get('previewURL') or ''
        return ''
    except Exception:
        return ''
