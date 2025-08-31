from __future__ import annotations
from .extensions import db
from flask_login import UserMixin
from datetime import datetime

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