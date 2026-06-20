from flask import Flask, flash, redirect, render_template, request, session, url_for
from datetime import timedelta
from flask_login import LoginManager, logout_user

from models import User, db


def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = 'dev-secret-key-change-before-production'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///summitdesk.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['REMEMBER_COOKIE_DURATION'] = timedelta(days=30)

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'
    login_manager.session_protection = 'strong'
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    @login_manager.unauthorized_handler
    def unauthorized():
        user_id = session.get('_user_id')
        user = User.query.get(int(user_id)) if user_id else None
        if user and not user.is_active:
            flash('Your account has been deactivated.', 'danger')
            logout_user()
        else:
            flash('Please log in to access this page.', 'warning')
        return redirect(url_for('auth.login', next=request.full_path.rstrip('?')))

    from blueprints.admin import admin_bp
    from blueprints.auth import auth_bp
    from blueprints.staff import staff_bp
    from blueprints.user import user_bp
    from blueprints.api import api_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(user_bp, url_prefix='/user')
    app.register_blueprint(api_bp, url_prefix='/api')

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('errors/403.html'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('errors/404.html'), 404

    return app
