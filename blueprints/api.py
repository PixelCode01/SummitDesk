from flask import Blueprint, jsonify, request
from models import db, Trek, Booking, User
from datetime import date

api_bp = Blueprint('api', __name__)


def trek_to_dict(trek):
    return {
        'id': trek.id,
        'name': trek.name,
        'location': trek.location,
        'difficulty': trek.difficulty,
        'duration_days': trek.duration_days,
        'available_slots': trek.available_slots,
        'total_slots': trek.total_slots,
        'status': trek.status,
        'start_date': trek.start_date.isoformat() if trek.start_date else None,
        'end_date': trek.end_date.isoformat() if trek.end_date else None,
        'description': trek.description,
    }


@api_bp.route('/treks', methods=['GET'])
def treks_list():
    treks = Trek.query.all()
    return jsonify([trek_to_dict(t) for t in treks])


@api_bp.route('/treks/<int:trek_id>', methods=['GET'])
def trek_detail(trek_id):
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error': 'Trek not found'}), 404
    return jsonify(trek_to_dict(trek))


@api_bp.route('/treks', methods=['POST'])
def trek_create():
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    name = (data.get('name') or '').strip()
    if not name:
        return jsonify({'error': 'name is required'}), 400

    required = ['name', 'location', 'difficulty', 'duration_days', 'total_slots', 'start_date', 'end_date']
    missing = [f for f in required if not data.get(f)]
    if missing:
        return jsonify({'error': f'Missing fields: {missing}'}), 400

    try:
        start = date.fromisoformat(data['start_date'])
        end = date.fromisoformat(data['end_date'])
    except Exception:
        return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400

    try:
        slots = int(data['total_slots'])
    except Exception:
        return jsonify({'error': 'total_slots must be an integer'}), 400

    trek = Trek(
        name=name,
        location=data['location'].strip(),
        difficulty=data['difficulty'],
        duration_days=int(data['duration_days']),
        total_slots=slots,
        available_slots=slots,
        start_date=start,
        end_date=end,
        description=data.get('description', ''),
        status=data.get('status', 'Pending'),
        created_by=data.get('created_by') or 1,
    )
    db.session.add(trek)
    db.session.commit()
    return jsonify({'message': 'Trek created', 'id': trek.id}), 201


@api_bp.route('/treks/<int:trek_id>', methods=['PUT'])
def trek_update(trek_id):
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error': 'Trek not found'}), 404
    data = request.get_json()
    if not data:
        return jsonify({'error': 'JSON body required'}), 400

    for field in ('name', 'location', 'difficulty', 'description', 'status'):
        if field in data:
            setattr(trek, field, data[field])

    if 'duration_days' in data:
        trek.duration_days = int(data['duration_days'])
    if 'total_slots' in data:
        trek.total_slots = int(data['total_slots'])
    if 'available_slots' in data:
        trek.available_slots = int(data['available_slots'])
    if 'start_date' in data:
        try:
            trek.start_date = date.fromisoformat(data['start_date'])
        except Exception:
            return jsonify({'error': 'Invalid start_date format'}), 400
    if 'end_date' in data:
        try:
            trek.end_date = date.fromisoformat(data['end_date'])
        except Exception:
            return jsonify({'error': 'Invalid end_date format'}), 400

    db.session.commit()
    return jsonify({'message': 'Trek updated'})


@api_bp.route('/treks/<int:trek_id>', methods=['DELETE'])
def trek_delete(trek_id):
    trek = Trek.query.get(trek_id)
    if not trek:
        return jsonify({'error': 'Trek not found'}), 404
    Booking.query.filter_by(trek_id=trek_id).delete()
    db.session.delete(trek)
    db.session.commit()
    return jsonify({'message': 'Trek deleted'})


@api_bp.route('/bookings', methods=['GET'])
def bookings_list():
    bookings = Booking.query.all()
    return jsonify([{
        'id': b.id,
        'user_id': b.user_id,
        'trek_id': b.trek_id,
        'status': b.status,
        'booked_at': b.booked_at.isoformat() if b.booked_at else None
    } for b in bookings])


@api_bp.route('/bookings/<int:booking_id>', methods=['GET'])
def booking_detail(booking_id):
    b = Booking.query.get(booking_id)
    if not b:
        return jsonify({'error': 'Not found'}), 404
    return jsonify({
        'id': b.id,
        'user': b.trekker.name if b.trekker else None,
        'trek': b.trek.name if b.trek else None,
        'status': b.status,
        'booked_at': b.booked_at.isoformat() if b.booked_at else None
    })


@api_bp.route('/users', methods=['GET'])
def users_list():
    users = User.query.filter_by(role='trekker').all()
    return jsonify([{
        'id': u.id,
        'name': u.name,
        'username': u.username,
        'is_active': u.is_active
    } for u in users])
