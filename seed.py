from datetime import date

from app import create_app
from models import Trek, User, db
from werkzeug.security import generate_password_hash


app = create_app()


with app.app_context():
    db.create_all()

    admin = User.query.filter_by(role='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@summitdesk.local',
            password=generate_password_hash('admin123'),
            role='admin',
            name='Admin',
        )
        db.session.add(admin)
        db.session.commit()
        print('Admin user created.')
    else:
        print('Admin user already exists.')

    staff = User.query.filter_by(username='staff').first()
    if not staff:
        staff = User(
            username='staff',
            email='staff@summitdesk.local',
            password=generate_password_hash('staff123'),
            role='staff',
            name='Staff Member',
            phone='9876543210',
            is_active=True,
        )
        db.session.add(staff)
        db.session.commit()
        print('Staff user created.')
    else:
        print('Staff user already exists.')

    if not Trek.query.first():
        treks = [
            Trek(
                name='Valley of Flowers',
                location='Uttarakhand',
                difficulty='Easy',
                duration_days=6,
                total_slots=20,
                available_slots=20,
                status='Open',
                start_date=date(2026, 8, 12),
                end_date=date(2026, 8, 17),
                description='A scenic Himalayan trek through alpine meadows and river valleys.',
                created_by=admin.id,
                assigned_staff=staff.id,
            ),
            Trek(
                name='Hampta Pass',
                location='Himachal Pradesh',
                difficulty='Moderate',
                duration_days=5,
                total_slots=15,
                available_slots=15,
                status='Approved',
                start_date=date(2026, 9, 4),
                end_date=date(2026, 9, 8),
                description='A crossover trek with dramatic changes in terrain and mountain views.',
                created_by=admin.id,
                assigned_staff=staff.id,
            ),
        ]
        db.session.add_all(treks)
        db.session.commit()
        print('Sample treks created.')
    else:
        print('Sample treks already exist.')

    print('Done.')
