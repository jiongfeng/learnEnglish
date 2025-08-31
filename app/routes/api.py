from __future__ import annotations
from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from datetime import datetime, timedelta
from ..extensions import db
from ..models import Card, Settings
from ..services.external import fetch_dictionary, translate_to_zh, fetch_image

bp = Blueprint('api', __name__)

@bp.get('/cards')
@login_required
def cards():
    rows = Card.query.filter_by(user_id=current_user.id).all()
    return jsonify([{
        'id': c.id,
        'word': c.word,
        'translation': c.translation,
        'example': c.example,
        'phonetic': c.phonetic,
        'audioUrl': c.audio_url,
        'imageUrl': c.image_url,
        'status': c.status,
        'repetitions': c.repetitions,
        'interval': c.interval,
        'ease': c.ease,
        'nextReview': c.next_review.isoformat() if c.next_review else None,
    } for c in rows])

@bp.get('/enrich')
@login_required
def enrich():
    word = (request.args.get('word') or '').strip()
    if not word:
        return jsonify({"ok": False, "error": "缺少单词"}), 400

    d = fetch_dictionary(word)  # 仍然用于拿音标/读音/例句
    # ⬇️ 这里改动：直接翻译“单词本身”，而非英文释义
    translation = translate_to_zh(word)

    example = d.get('example_en', '') if d else ''
    phonetic = d.get('phonetic', '') if d else ''
    audio = d.get('audio', '') if d else ''
    image = fetch_image(word)

    return jsonify({
        "ok": True,
        "data": {
            "translation": translation,   # 现在一定是“单词→中文”的结果（若翻译服务可用）
            "example": example,
            "phonetic": phonetic,
            "audioUrl": audio,
            "imageUrl": image,
        }
    })

@bp.post('/add')
@login_required
def add():
    data = request.get_json(force=True, silent=True) or {}
    word = (data.get('word') or '').strip()
    translation = (data.get('translation') or '').strip()
    if not word:
        return jsonify({"error": "缺少字段: word"}), 400
    if not translation:
        return jsonify({"error": "缺少字段: translation（可点自动获取）"}), 400
    if Card.query.filter_by(user_id=current_user.id, word=word).first():
        return jsonify({"error": "该单词已存在"}), 400
    card = Card(
        user_id=current_user.id,
        word=word,
        translation=translation,
        example=(data.get('example') or '').strip(),
        phonetic=(data.get('phonetic') or '').strip(),
        audio_url=(data.get('audioUrl') or '').strip(),
        image_url=(data.get('imageUrl') or '').strip(),
        status='new', ease=2.5
    )
    db.session.add(card)
    db.session.commit()
    return jsonify({"ok": True, "id": card.id})

@bp.post('/update')
@login_required
def update():
    data = request.get_json(force=True, silent=True) or {}
    cid = data.get('id')
    if not cid:
        return jsonify({"error": "缺少字段: id"}), 400
    card = Card.query.filter_by(id=cid, user_id=current_user.id).first()
    if not card:
        return jsonify({"error": "not found"}), 404

    new_word = (data.get('word') or '').strip()
    new_translation = (data.get('translation') or '').strip()
    if not new_word or not new_translation:
        return jsonify({"error": "word/translation 不能为空"}), 400

    # 冲突检查（同用户+不同卡片+同单词）
    conflict = Card.query.filter(
        Card.user_id == current_user.id,
        Card.word == new_word,
        Card.id != card.id
    ).first()
    if conflict:
        return jsonify({"error": "该单词已存在"}), 400

    card.word = new_word
    card.translation = new_translation
    card.example = (data.get('example') or '').strip()
    card.phonetic = (data.get('phonetic') or '').strip()
    card.audio_url = (data.get('audioUrl') or '').strip()
    card.image_url = (data.get('imageUrl') or '').strip()
    db.session.commit()
    return jsonify({"ok": True})


@bp.post('/delete')
@login_required
def delete():
    data = request.get_json(force=True, silent=True) or {}
    cid = data.get('id')
    if not cid:
        return jsonify({"error": "缺少字段: id"}), 400
    card = Card.query.filter_by(id=cid, user_id=current_user.id).first()
    if not card:
        return jsonify({"error": "not found"}), 404
    db.session.delete(card)
    db.session.commit()
    return jsonify({"ok": True})


@bp.post('/review')
@login_required
def review():
    data = request.get_json(force=True, silent=True) or {}
    cid = data.get('id'); q = int(data.get('q', -1))
    card = Card.query.filter_by(id=cid, user_id=current_user.id).first()
    if not card:
        return jsonify({"error": "not found"}), 404
    if q < 0 or q > 5:
        return jsonify({"error": "q must be 0..5"}), 400
    today = datetime.utcnow().date()
    if q < 3:
        card.repetitions = 0
        card.interval = 1
    else:
        if card.repetitions == 0:
            card.interval = 1
        elif card.repetitions == 1:
            card.interval = 6
        else:
            card.interval = max(1, round(card.interval * card.ease))
        card.repetitions += 1
    card.ease = max(1.3, card.ease + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02)))
    card.next_review = today + timedelta(days=card.interval)
    card.last_reviewed_at = datetime.utcnow()
    card.status = 'review' if q >= 3 else 'learning'
    db.session.commit()
    return jsonify({"ok": True})

@bp.post('/introduce')
@login_required
def introduce():
    data = request.get_json(force=True, silent=True) or {}
    cid = data.get('id'); mode = data.get('mode', 'tomorrow')
    card = Card.query.filter_by(id=cid, user_id=current_user.id).first()
    if not card:
        return jsonify({"error": "not found"}), 404
    today = datetime.utcnow().date()
    card.status = 'learning'
    card.repetitions = 0
    card.interval = 0
    card.ease = 2.5
    if mode == 'short':
        card.next_review = today
    else:
        card.next_review = today + timedelta(days=1)
    card.first_learned_at = datetime.utcnow()
    db.session.commit()
    return jsonify({"ok": True})

@bp.route('/cfg', methods=['GET','POST'])
@login_required
def cfg():
    s = Settings.query.filter_by(user_id=current_user.id).first()
    if request.method == 'GET':
        if not s:
            s = Settings(user_id=current_user.id, daily_new_limit=20, hide_answer=True)
            db.session.add(s); db.session.commit()
        return jsonify({"dailyNewLimit": s.daily_new_limit, "hideAnswer": bool(s.hide_answer)})
    data = request.get_json(force=True, silent=True) or {}
    if not s:
        s = Settings(user_id=current_user.id)
        db.session.add(s)
    if 'dailyNewLimit' in data:
        try:
            s.daily_new_limit = max(0, int(data['dailyNewLimit']))
        except Exception:
            return jsonify({"error": "dailyNewLimit must be integer >=0"}), 400
    if 'hideAnswer' in data:
        s.hide_answer = bool(data['hideAnswer'])
    db.session.commit()
    return jsonify({"ok": True})