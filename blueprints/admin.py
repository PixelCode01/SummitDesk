from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for, current_app
from flask_login import current_user, login_required

from decorators import admin_required
from models import Booking, Trek, User, db
import os
from werkzeug.utils import secure_filename

UPLOAD_FOLDER = os.path.join('static', 'img', 'treks')
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
from sqlalchemy import func


admin_bp = Blueprint('admin', __name__)

VALID_TRANSITIONS = {
    'Pending': ['Approved'],
    'Approved': ['Open', 'Closed'],
    'Open': ['Closed', 'Completed'],
    'Closed': ['Open', 'Completed'],
    'Completed': ['Open', 'Closed'],
}


def active_staff_query():
    return User.query.filter_by(role='staff', is_active=True).order_by(User.name.asc())


def parse_trek_form(trek=None):
    name = request.form.get('name', '').strip()
    location = request.form.get('location', '').strip()
    difficulty = request.form.get('difficulty')
    description = request.form.get('description', '').strip() or None
    assigned_staff = request.form.get('assigned_staff') or None

    if not name:
        raise ValueError('Trek name is required.')
    if not location:
        raise ValueError('Location is required.')
    if difficulty not in ('Easy', 'Moderate', 'Hard'):
        raise ValueError('Choose a valid difficulty.')

    duration_days = int(request.form.get('duration_days', 0))
    total_slots = int(request.form.get('total_slots', 0))
    if duration_days < 1:
        raise ValueError('Duration must be at least 1 day.')
    if total_slots < 1:
        raise ValueError('Total slots must be at least 1.')

    start_date = date.fromisoformat(request.form.get('start_date', ''))
    end_date = date.fromisoformat(request.form.get('end_date', ''))
    if end_date < start_date:
        raise ValueError('End date cannot be before start date.')

    data = {
        'name': name,
        'location': location,
        'difficulty': difficulty,
        'duration_days': duration_days,
        'total_slots': total_slots,
        'start_date': start_date,
        'end_date': end_date,
        'description': description,
        'assigned_staff': int(assigned_staff) if assigned_staff else None,
    }

    if trek:
        # Preserve already-booked seats when admin changes capacity.
        slot_diff = total_slots - trek.total_slots
        data['available_slots'] = max(0, trek.available_slots + slot_diff)
    else:
        data['available_slots'] = total_slots

    return data


@admin_bp.route('/', strict_slashes=False)
@login_required
@admin_required
def dashboard():
    trek_count = Trek.query.count()
    user_count = User.query.filter_by(role='trekker').count()
    staff_count = User.query.filter_by(role='staff').count()
    booking_count = Booking.query.count()
    pending_staff_count = User.query.filter_by(role='staff', is_active=False).count()
    # bookings per trek (top 8)
    results = db.session.query(
        Trek.name,
        func.count(Booking.id).label('count')
    ).join(Booking, Booking.trek_id == Trek.id)
    results = results.group_by(Trek.id).order_by(func.count(Booking.id).desc()).limit(8).all()

    chart_labels = [r.name for r in results]
    chart_data = [r.count for r in results]

    statuses = ['Pending', 'Approved', 'Open', 'Closed', 'Completed']
    status_counts = [Trek.query.filter_by(status=s).count() for s in statuses]
    return render_template(
        'admin/dashboard.html',
        trek_count=trek_count,
        user_count=user_count,
        staff_count=staff_count,
        booking_count=booking_count,
        pending_staff_count=pending_staff_count,
        chart_labels=chart_labels,
        chart_data=chart_data,
        statuses=statuses,
        status_counts=status_counts,
    )


@admin_bp.route('/treks')
@login_required
@admin_required
def treks():
    q = request.args.get('q', '').strip()
    query = Trek.query

    if q:
        if q.isdigit():
            query = query.filter((Trek.name.ilike(f'%{q}%')) | (Trek.id == int(q)))
        else:
            query = query.filter(Trek.name.ilike(f'%{q}%'))

    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(Trek.created_at.desc()).paginate(page=page, per_page=20, error_out=False)
    staff_list = active_staff_query().all()
    return render_template(
        'admin/treks.html',
        treks=pagination.items,
        pagination=pagination,
        staff_list=staff_list,
        transitions=VALID_TRANSITIONS,
        q=q,
    )


@admin_bp.route('/treks/new', methods=['GET', 'POST'])
@login_required
@admin_required
def trek_new():
    staff_list = active_staff_query().all()

    if request.method == 'POST':
        try:
            data = parse_trek_form()
        except (TypeError, ValueError) as error:
            flash(str(error) or 'Please enter valid trek details.', 'danger')
            return render_template('admin/trek_form.html', trek=None, staff_list=staff_list)

        # handle image upload
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_name = f"{data['name'].replace(' ', '_')}_{filename}"
            save_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
            os.makedirs(save_dir, exist_ok=True)
            file.save(os.path.join(save_dir, save_name))
            data['image_filename'] = save_name

        trek = Trek(status='Pending', created_by=current_user.id, **data)
        db.session.add(trek)
        db.session.commit()
        flash('Trek created.', 'success')
        return redirect(url_for('admin.treks'))

    return render_template('admin/trek_form.html', trek=None, staff_list=staff_list)


@admin_bp.route('/treks/<int:trek_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def trek_edit(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    staff_list = active_staff_query().all()

    if request.method == 'POST':
        try:
            data = parse_trek_form(trek)
        except (TypeError, ValueError) as error:
            flash(str(error) or 'Please enter valid trek details.', 'danger')
            return render_template('admin/trek_form.html', trek=trek, staff_list=staff_list)
        # handle image upload
        file = request.files.get('image')
        if file and file.filename and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_name = f"{data['name'].replace(' ', '_')}_{filename}"
            save_dir = os.path.join(current_app.root_path, UPLOAD_FOLDER)
            os.makedirs(save_dir, exist_ok=True)
            file.save(os.path.join(save_dir, save_name))
            data['image_filename'] = save_name

        for key, value in data.items():
            setattr(trek, key, value)
        db.session.commit()
        flash('Trek updated.', 'success')
        return redirect(url_for('admin.treks'))

    return render_template('admin/trek_form.html', trek=trek, staff_list=staff_list)


@admin_bp.route('/treks/<int:trek_id>/delete')
@login_required
@admin_required
def trek_delete_confirm(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    return render_template('admin/trek_delete_confirm.html', trek=trek)


@admin_bp.route('/treks/<int:trek_id>/delete', methods=['POST'])
@login_required
@admin_required
def trek_delete(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    from models import Waitlist, Review
    Booking.query.filter_by(trek_id=trek.id).delete()
    Waitlist.query.filter_by(trek_id=trek.id).delete()
    Review.query.filter_by(trek_id=trek.id).delete()
    db.session.delete(trek)
    db.session.commit()
    flash('Trek deleted.', 'success')
    return redirect(url_for('admin.treks'))


@admin_bp.route('/treks/<int:trek_id>/status', methods=['POST'])
@login_required
@admin_required
def trek_status(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    new_status = request.form.get('status')

    if new_status not in VALID_TRANSITIONS.get(trek.status, []):
        flash(f'Cannot move from {trek.status} to {new_status}.', 'danger')
        return redirect(url_for('admin.treks'))

    if trek.status == 'Completed' and new_status in ['Open', 'Closed']:
        Booking.query.filter_by(trek_id=trek.id, status='Completed').update({'status': 'Booked'})
        
    if new_status == 'Completed':
        Booking.query.filter_by(trek_id=trek.id, status='Booked').update({'status': 'Completed'})

    trek.status = new_status
    db.session.commit()
    flash(f'Status updated to {new_status}.', 'success')
    return redirect(url_for('admin.treks'))


@admin_bp.route('/treks/<int:trek_id>/assign', methods=['POST'])
@login_required
@admin_required
def assign_staff(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    staff_id = request.form.get('staff_id')

    if staff_id:
        staff = User.query.filter_by(id=int(staff_id), role='staff', is_active=True).first()
        if not staff:
            flash('Choose an active staff member.', 'danger')
            return redirect(url_for('admin.treks'))
        trek.assigned_staff = staff.id
    else:
        trek.assigned_staff = None

    db.session.commit()
    flash('Staff assignment updated.', 'success')
    return redirect(url_for('admin.treks'))


@admin_bp.route('/staff')
@login_required
@admin_required
def staff():
    q = request.args.get('q', '').strip()
    query = User.query.filter_by(role='staff')

    if q:
        if q.isdigit():
            query = query.filter(
                (User.name.ilike(f'%{q}%'))
                | (User.username.ilike(f'%{q}%'))
                | (User.id == int(q))
            )
        else:
            query = query.filter(
                (User.name.ilike(f'%{q}%'))
                | (User.username.ilike(f'%{q}%'))
                | (User.email.ilike(f'%{q}%'))
            )

    staff_list = query.order_by(User.is_active.asc(), User.name.asc()).all()
    return render_template('admin/staff.html', staff_list=staff_list, q=q)


@admin_bp.route('/staff/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def staff_toggle(user_id):
    user = User.query.get_or_404(user_id)
    if user.role != 'staff':
        abort(404)

    user.is_active = not user.is_active
    db.session.commit()
    action = 'activated' if user.is_active else 'deactivated'
    flash(f'{user.name} {action}.', 'success')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/users')
@login_required
@admin_required
def users():
    q = request.args.get('q', '').strip()
    query = User.query.filter_by(role='trekker')

    if q:
        if q.isdigit():
            query = query.filter(
                (User.name.ilike(f'%{q}%'))
                | (User.username.ilike(f'%{q}%'))
                | (User.id == int(q))
            )
        else:
            query = query.filter(
                (User.name.ilike(f'%{q}%'))
                | (User.username.ilike(f'%{q}%'))
                | (User.email.ilike(f'%{q}%'))
            )

    page = request.args.get('page', 1, type=int)
    pagination = query.order_by(User.is_active.asc(), User.name.asc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/users.html', user_list=pagination.items, pagination=pagination, q=q)


@admin_bp.route('/users/<int:user_id>/toggle', methods=['POST'])
@login_required
@admin_required
def user_toggle(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'admin':
        flash('Cannot deactivate admin.', 'danger')
        return redirect(url_for('admin.users'))
    if user.role != 'trekker':
        abort(404)

    user.is_active = not user.is_active
    db.session.commit()
    action = 'blacklisted' if not user.is_active else 'restored'
    flash(f'{user.name} {action}.', 'success')
    return redirect(url_for('admin.users'))


@admin_bp.route('/bookings')
@login_required
@admin_required
def bookings():
    page = request.args.get('page', 1, type=int)
    pagination = Booking.query.order_by(Booking.booked_at.desc()).paginate(page=page, per_page=20, error_out=False)
    return render_template('admin/bookings.html', bookings=pagination.items, pagination=pagination)
