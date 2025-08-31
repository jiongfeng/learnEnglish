from __future__ import annotations
from flask import Flask
from .extensions import db, login_manager
import os

def create_app(test_config: dict | None = None) -> Flask:
    app = Flask(__name__, template_folder="../templates", static_folder="../static")

    # 基础配置
    app.config.update(
        SECRET_KEY=os.getenv('SECRET_KEY', 'dev-secret-change-me'),
        SQLALCHEMY_DATABASE_URI=os.getenv('DATABASE_URL', 'sqlite:///app.db'),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
    )
    if test_config:
        app.config.update(test_config)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'

    # 未登录 API -> 401 JSON，其它 -> 重定向登录
    @login_manager.unauthorized_handler
    def _unauth_handler():
        from flask import request, jsonify, redirect, url_for
        if request.path.startswith('/api'):
            return jsonify({"ok": False, "error": "unauthorized"}), 401
        return redirect(url_for('auth.login'))

    # 注册蓝图
    from .routes.pages import bp as pages_bp
    from .routes.api import bp as api_bp
    from .routes.auth import bp as auth_bp
    app.register_blueprint(pages_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp)

    return app