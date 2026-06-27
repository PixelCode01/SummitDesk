from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import staff_required
from models import Booking, Trek, db
from sqlalchemy import func


staff_bp = Blueprint('staff', __name__)

STAFF_TRANSITIONS = {
    'Approved': ['Open'],
    'Open': ['Closed', 'Completed'],
    'Closed': ['Open', 'Completed'],
}


def get_assigned_trek_or_404(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    if trek.assigned_staff != current_user.id:
        abort(403)
    return trek


@staff_bp.route('/', strict_slashes=False)
@login_required
@staff_required
def dashboard():
    treks = Trek.query.filter_by(assigned_staff=current_user.id).order_by(Trek.start_date.asc()).all()

    chart_labels = [t.name for t in treks]
    chart_data = [Booking.query.filter_by(trek_id=t.id, status='Booked').count() for t in treks]

    return render_template('staff/dashboard.html', treks=treks, chart_labels=chart_labels, chart_data=chart_data)


@staff_bp.route('/treks/<int:trek_id>')
@login_required
@staff_required
def trek_detail(trek_id):
    trek = get_assigned_trek_or_404(trek_id)
    participants = Booking.query.filter_by(trek_id=trek.id, status='Booked').order_by(Booking.booked_at.desc()).all()
    return render_template(
        'staff/trek_detail.html',
        trek=trek,
        participants=participants,
        transitions=STAFF_TRANSITIONS,
    )


@staff_bp.route('/treks/<int:trek_id>/edit', methods=['POST'])
@login_required
@staff_required
def trek_edit(trek_id):
    trek = get_assigned_trek_or_404(trek_id)
    new_slots = request.form.get('available_slots', type=int)

    if new_slots is None or new_slots < 0:
        flash('Invalid slot count.', 'danger')
        return redirect(url_for('staff.trek_detail', trek_id=trek.id))

    if new_slots > trek.total_slots:
        flash(f'Cannot exceed total slots ({trek.total_slots}).', 'danger')
        return redirect(url_for('staff.trek_detail', trek_id=trek.id))

    trek.available_slots = new_slots
    db.session.commit()
    flash('Slots updated.', 'success')
    return redirect(url_for('staff.trek_detail', trek_id=trek.id))


@staff_bp.route('/treks/<int:trek_id>/status', methods=['POST'])
@login_required
@staff_required
def trek_status(trek_id):
    trek = get_assigned_trek_or_404(trek_id)
    new_status = request.form.get('status')

    if new_status not in STAFF_TRANSITIONS.get(trek.status, []):
        flash(f'Cannot change from {trek.status} to {new_status}.', 'danger')
        return redirect(url_for('staff.trek_detail', trek_id=trek.id))

    trek.status = new_status
    if new_status == 'Completed':
        Booking.query.filter_by(trek_id=trek.id, status='Booked').update({'status': 'Completed'})

    db.session.commit()
    flash(f'Trek marked as {new_status}.', 'success')
    return redirect(url_for('staff.trek_detail', trek_id=trek.id))
