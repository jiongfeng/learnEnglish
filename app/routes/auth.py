from flask import Blueprint, render_template, request, redirect, url_for
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user
from ..extensions import db, login_manager
from ..models import User, Settings

bp = Blueprint('auth', __name__)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

@bp.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        pw = request.form.get('password') or ''
        user = User.query.filter_by(email=email).first()
        if not user or not check_password_hash(user.password_hash, pw):
            return render_template('auth.html', title='登录', btn='登录', mode='login', error='邮箱或密码错误')
        login_user(user)
        return redirect(url_for('pages.index'))
    return render_template('auth.html', title='登录', btn='登录', mode='login', error=None)

@bp.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        pw = request.form.get('password') or ''
        if not email or not pw:
            return render_template('auth.html', title='注册', btn='注册', mode='register', error='请填写邮箱和密码')
        if User.query.filter_by(email=email).first():
            return render_template('auth.html', title='注册', btn='注册', mode='register', error='邮箱已存在')
        user = User(email=email, password_hash=generate_password_hash(pw))
        db.session.add(user)
        db.session.commit()
        db.session.add(Settings(user_id=user.id, daily_new_limit=20, hide_answer=True))
        db.session.commit()
        login_user(user)
        return redirect(url_for('pages.index'))
    return render_template('auth.html', title='注册', btn='注册', mode='register', error=None)

@bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.login'))