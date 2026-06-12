from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required, login_user, logout_user
from werkzeug.security import check_password_hash, generate_password_hash

from models import Trek, User, db


auth_bp = Blueprint('auth', __name__)


def dashboard_for(role):
    if role == 'admin':
        return 'admin.dashboard'
    if role == 'staff':
        return 'staff.dashboard'
    return 'user.dashboard'


@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for(dashboard_for(current_user.role)))
    return redirect(url_for('auth.login'))


@auth_bp.route('/treks')
def treks():
    all_treks = Trek.query.order_by(Trek.start_date.asc()).all()
    return render_template('home.html', treks=all_treks)


@auth_bp.route('/trek/<int:trek_id>')
def trek_detail(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    return render_template('trek_detail.html', trek=trek)


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for(dashboard_for(current_user.role)))

    if request.method == 'POST':
        attempts = session.get('login_attempts', 0)

        if attempts >= 5:
            flash('Too many failed attempts. Try again later.', 'danger')
            return render_template('auth/login.html')

        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            session['login_attempts'] = attempts + 1
            flash('Invalid username or password.', 'danger')
            return render_template('auth/login.html')

        if not user.is_active:
            if user.role == 'staff':
                flash('Your account is pending admin approval.', 'warning')
            else:
                flash('Your account has been deactivated.', 'danger')
            return render_template('auth/login.html')

        session.pop('login_attempts', None)
        remember = request.form.get('remember') == 'on'
        login_user(user, remember=remember)
        next_page = request.args.get('next')
        return redirect(next_page or url_for(dashboard_for(user.role)))

    return render_template('auth/login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for(dashboard_for(current_user.role)))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        name = request.form.get('name', '').strip()
        phone = request.form.get('phone', '').strip()
        role = request.form.get('role', 'trekker')

        if role not in ('trekker', 'staff'):
            role = 'trekker'

        if not username or not email or not password or not name:
            flash('Name, username, email, and password are required.', 'danger')
            return render_template('auth/register.html')

        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(username=username).first():
            flash('Username already taken.', 'danger')
            return render_template('auth/register.html')

        if User.query.filter_by(email=email).first():
            flash('Email already registered.', 'danger')
            return render_template('auth/register.html')

        user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role=role,
            name=name,
            phone=phone or None,
            is_active=role != 'staff',
        )
        db.session.add(user)
        db.session.commit()

        if role == 'staff':
            flash('Registration submitted. Wait for admin approval before logging in.', 'info')
        else:
            flash('Account created. Please log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'success')
    return redirect(url_for('auth.login'))
