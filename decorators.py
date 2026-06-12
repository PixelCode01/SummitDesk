from functools import wraps

from flask import abort, flash, redirect, url_for
from flask_login import current_user, logout_user


def _active_or_logout():
    if current_user.is_active:
        return True

    flash('Your account has been deactivated.', 'danger')
    logout_user()
    return False


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            abort(403)
        if not _active_or_logout():
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated


def staff_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'staff':
            abort(403)
        if not _active_or_logout():
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated


def trekker_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'trekker':
            abort(403)
        if not _active_or_logout():
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)

    return decorated
