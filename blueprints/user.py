from datetime import datetime

from flask import Blueprint, abort, flash, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from decorators import trekker_required
from models import Booking, Trek, User, Review, Waitlist, db


user_bp = Blueprint('user', __name__)


@user_bp.route('/', strict_slashes=False)
@login_required
@trekker_required
def dashboard():
    bookings = Booking.query.filter_by(user_id=current_user.id, status='Booked').order_by(Booking.booked_at.desc()).all()
    open_trek_count = Trek.query.filter_by(status='Open').count()
    return render_template('user/dashboard.html', bookings=bookings, open_trek_count=open_trek_count)


@user_bp.route('/treks')
@login_required
@trekker_required
def treks():
    q = request.args.get('q', '').strip()
    difficulty = request.args.get('difficulty', '').strip()
    location = request.args.get('location', '').strip()

    query = Trek.query.filter_by(status='Open')

    if q:
        query = query.filter(Trek.name.ilike(f'%{q}%'))
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if location:
        query = query.filter(Trek.location.ilike(f'%{location}%'))

    all_treks = query.order_by(Trek.start_date.asc()).all()
    return render_template(
        'user/treks.html',
        treks=all_treks,
        q=q,
        difficulty=difficulty,
        location=location,
    )


@user_bp.route('/treks/<int:trek_id>')
@login_required
@trekker_required
def trek_detail(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if trek.status != 'Open':
        flash('This trek is not available for booking.', 'warning')
        return redirect(url_for('user.treks'))

    existing = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id, status='Booked').first()
    can_review = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id, status='Completed').first() is not None
    on_waitlist = Waitlist.query.filter_by(user_id=current_user.id, trek_id=trek.id).first() is not None
    return render_template('user/trek_detail.html', trek=trek, already_booked=existing is not None, can_review=can_review, on_waitlist=on_waitlist)


@user_bp.route('/treks/<int:trek_id>/book', methods=['POST'])
@login_required
@trekker_required
def book(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if trek.status != 'Open':
        flash('This trek is not open for booking.', 'danger')
        return redirect(url_for('user.treks'))

    if trek.available_slots <= 0:
        flash('No slots available. Trek is fully booked.', 'danger')
        return redirect(url_for('user.treks'))

    existing = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id, status='Booked').first()
    if existing:
        flash('You already have a booking for this trek.', 'warning')
        return redirect(url_for('user.trek_detail', trek_id=trek.id))

    existing_cancelled = Booking.query.filter_by(user_id=current_user.id, trek_id=trek.id, status='Cancelled').first()
    if existing_cancelled:
        existing_cancelled.status = 'Booked'
        existing_cancelled.payment_status = 'Pending'
        existing_cancelled.booked_at = datetime.utcnow()
    else:
        booking = Booking(user_id=current_user.id, trek_id=trek.id, status='Booked')
        db.session.add(booking)

    trek.available_slots -= 1
    db.session.commit()

    flash('Trek booked successfully!', 'success')
    return redirect(url_for('user.bookings'))


@user_bp.route('/bookings')
@login_required
@trekker_required
def bookings():
    all_bookings = Booking.query.filter_by(user_id=current_user.id).order_by(Booking.booked_at.desc()).all()
    return render_template('user/bookings.html', bookings=all_bookings)


@user_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
@trekker_required
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.user_id != current_user.id:
        abort(403)

    if booking.status != 'Booked':
        flash('This booking cannot be cancelled.', 'warning')
        return redirect(url_for('user.bookings'))

    booking.status = 'Cancelled'
    if booking.trek.available_slots < booking.trek.total_slots:
        booking.trek.available_slots += 1

    # auto-assign next from waitlist if present
    next_in_line = Waitlist.query.filter_by(trek_id=booking.trek_id).order_by(Waitlist.joined_at.asc()).first()
    if next_in_line:
        new_booking = Booking(user_id=next_in_line.user_id, trek_id=booking.trek_id, status='Booked')
        db.session.add(new_booking)
        booking.trek.available_slots -= 1
        db.session.delete(next_in_line)

    db.session.commit()

    flash('Booking cancelled.', 'success')
    return redirect(url_for('user.bookings'))


@user_bp.route('/treks/<int:trek_id>/review', methods=['GET', 'POST'])
@login_required
@trekker_required
def review(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    completed = Booking.query.filter_by(user_id=current_user.id, trek_id=trek_id, status='Completed').first()
    if not completed:
        flash('You can only review treks you have completed.', 'warning')
        return redirect(url_for('user.bookings'))

    existing = Review.query.filter_by(user_id=current_user.id, trek_id=trek_id).first()
    if existing:
        flash('You have already reviewed this trek.', 'warning')
        return redirect(url_for('user.bookings'))

    if request.method == 'POST':
        try:
            rating = int(request.form.get('rating', 0))
        except Exception:
            rating = 0
        if rating < 1 or rating > 5:
            flash('Rating must be between 1 and 5.', 'danger')
            return render_template('user/review.html', trek=trek)

        review = Review(
            user_id=current_user.id,
            trek_id=trek_id,
            rating=rating,
            comment=request.form.get('comment', '').strip()
        )
        db.session.add(review)
        db.session.commit()
        flash('Review submitted.', 'success')
        return redirect(url_for('user.bookings'))

    return render_template('user/review.html', trek=trek)


@user_bp.route('/treks/<int:trek_id>/waitlist', methods=['POST'])
@login_required
@trekker_required
def join_waitlist(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if trek.available_slots > 0:
        flash('Slots are available. Book directly instead.', 'info')
        return redirect(url_for('user.trek_detail', trek_id=trek_id))
        
    already_booked = Booking.query.filter_by(user_id=current_user.id, trek_id=trek_id, status='Booked').first()
    if already_booked:
        flash('You already have a booking for this trek.', 'warning')
        return redirect(url_for('user.trek_detail', trek_id=trek_id))

    existing = Waitlist.query.filter_by(user_id=current_user.id, trek_id=trek_id).first()
    if existing:
        flash('You are already on the waitlist.', 'warning')
        return redirect(url_for('user.trek_detail', trek_id=trek_id))

    entry = Waitlist(user_id=current_user.id, trek_id=trek_id)
    db.session.add(entry)
    db.session.commit()
    flash('Added to waitlist. You will get the slot if someone cancels.', 'success')
    return redirect(url_for('user.trek_detail', trek_id=trek_id))


@user_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@trekker_required
def profile():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()

        if not name or not email:
            flash('Name and email are required.', 'danger')
            return render_template('user/profile.html')

        existing = User.query.filter_by(email=email).first()
        if existing and existing.id != current_user.id:
            flash('Email already in use by another account.', 'danger')
            return render_template('user/profile.html')

        current_user.name = name
        current_user.email = email
        current_user.phone = phone or None
        db.session.commit()

        flash('Profile updated.', 'success')
        return redirect(url_for('user.profile'))

    return render_template('user/profile.html')
