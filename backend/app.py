from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, jwt_required, create_access_token, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash
import sqlite3
from datetime import timedelta
import os
from dotenv import load_dotenv
from api_routes import api
from ai_timetable import TimetableGenerator
from enhanced_admin_routes import enhanced_admin_bp
from enhanced_staff_routes import staff_bp

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'your-secret-key-change-in-production')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=24)

jwt = JWTManager(app)
CORS(app, resources={r"/api/*": {"origins": "*"}}, supports_credentials=True)

# Register Blueprints
app.register_blueprint(api)
app.register_blueprint(enhanced_admin_bp)
app.register_blueprint(staff_bp)

# Initialize the database
def init_db():
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL CHECK (role IN ('main_admin', 'dept_admin', 'staff')),
            department_id INTEGER,
            staff_role TEXT CHECK (staff_role IN ('assistant_professor', 'professor', 'hod')),
            subjects_selected TEXT,
            subjects_locked BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            code TEXT NOT NULL,
            department_id INTEGER NOT NULL,
            credits INTEGER DEFAULT 3,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS classrooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            capacity INTEGER NOT NULL,
            department_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS timetables (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER NOT NULL,
            day TEXT NOT NULL,
            time_slot TEXT NOT NULL,
            subject_id INTEGER NOT NULL,
            staff_id INTEGER NOT NULL,
            classroom_id INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id),
            FOREIGN KEY (subject_id) REFERENCES subjects (id),
            FOREIGN KEY (staff_id) REFERENCES users (id),
            FOREIGN KEY (classroom_id) REFERENCES classrooms (id)
        )
    ''')

    cursor.execute('''
        CREATE TABLE IF NOT EXISTS constraints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            department_id INTEGER,
            role TEXT NOT NULL CHECK (role IN ('assistant_professor', 'professor', 'hod')),
            subject_type TEXT NOT NULL CHECK (subject_type IN ('theory', 'lab', 'both')),
            max_subjects INTEGER NOT NULL DEFAULT 1,
            max_hours INTEGER NOT NULL DEFAULT 8,
            created_by INTEGER NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments (id),
            FOREIGN KEY (created_by) REFERENCES users (id)
        )
    ''')
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS staff_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        employee_id TEXT NOT NULL,
        college TEXT NOT NULL,
        faculty TEXT NOT NULL,
        campus TEXT NOT NULL,
        contact_number TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        username TEXT UNIQUE,
        password TEXT,
        staff_role TEXT CHECK (
            staff_role IN (
                'hod',
                'associate_professor',
                'assistant_professor',
                'professor',
                'professor_sg',
                'vp',
                'dean'
            )
        ),
        registered BOOLEAN DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
''')

    

    conn.commit()
    conn.close()

# Health Check
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'message': 'SRM Timetable AI Backend is running'}), 200

# AUTH ROUTES
@app.route('/api/auth/login', methods=['POST'])
def login():
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        print(f"📥 Login attempt with email: {email}")

        if not email or not password:
            print("❌ Missing email or password")
            return jsonify({'success': False, 'error': 'Email and password are required'}), 400

        conn = sqlite3.connect('timetable.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT u.id, u.name, u.email, u.password_hash, u.role, u.department_id,
                   u.staff_role, u.subjects_selected, u.subjects_locked, d.name as department_name
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE u.email = ?
        ''', (email,))
        user_data = cursor.fetchone()
        conn.close()

        if not user_data:
            print("❌ User not found in DB")
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        user_id, name, db_email, db_password_hash, role, dept_id, staff_role, selected_subjects, locked, dept_name = user_data

        print(f"✅ User record found: {db_email}")
        password_match = check_password_hash(db_password_hash, password)
        print(f"🔐 Password match: {password_match}")

        if not password_match:
            return jsonify({'success': False, 'error': 'Invalid email or password'}), 401

        user = {
            'id': str(user_id),
            'name': name,
            'email': db_email,
            'role': role,
            'department_id': str(dept_id) if dept_id else None,
            'staff_role': staff_role,
            'subjects_selected': selected_subjects.split(',') if selected_subjects else [],
            'subjects_locked': bool(locked),
            'department_name': dept_name
        }

        access_token = create_access_token(identity=str(user_id))
        print(f"🎟️ Token issued for {db_email}")

        return jsonify({'success': True, 'data': {'user': user, 'token': access_token}}), 200

    except Exception as e:
        print("🔥 Login Exception:", str(e))
        return jsonify({'success': False, 'error': 'Login failed'}), 500


@app.route('/api/auth/verify', methods=['GET'])
@jwt_required()
def verify_token():
    try:
        current_user_id = get_jwt_identity()
        conn = sqlite3.connect('timetable.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT u.id, u.name, u.email, u.role, u.department_id,
                   u.staff_role, u.subjects_selected, u.subjects_locked, d.name as department_name
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            WHERE u.id = ?
        ''', (current_user_id,))

        user_data = cursor.fetchone()
        conn.close()

        if not user_data:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        user = {
            'id': str(user_data[0]),
            'name': user_data[1],
            'email': user_data[2],
            'role': user_data[3],
            'department_id': str(user_data[4]) if user_data[4] else None,
            'staff_role': user_data[5],
            'subjects_selected': user_data[6].split(',') if user_data[6] else [],
            'subjects_locked': bool(user_data[7]),
            'department_name': user_data[8]
        }

        return jsonify({'success': True, 'data': {'user': user}}), 200

    except Exception as e:
        return jsonify({'success': False, 'error': 'Token verification failed'}), 401


@app.route('/api/auth/logout', methods=['POST'])
@jwt_required()
def logout():
    return jsonify({'success': True, 'message': 'Logged out successfully'}), 200

# Get all users
@app.route('/api/users', methods=['GET'])
@jwt_required()
def get_users():
    try:
        conn = sqlite3.connect('timetable.db')
        cursor = conn.cursor()

        cursor.execute('''
            SELECT u.id, u.name, u.email, u.role, d.name as department_name
            FROM users u
            LEFT JOIN departments d ON u.department_id = d.id
            ORDER BY u.name
        ''')

        users_data = cursor.fetchall()
        conn.close()

        users_list = []
        for user in users_data:
            users_list.append({
                'id': str(user[0]),
                'name': user[1],
                'email': user[2],
                'role': user[3],
                'department_name': user[4]
            })

        return jsonify(users_list), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Timetable stats
@app.route('/api/timetables/stats', methods=['GET'])
@jwt_required()
def get_timetable_stats():
    try:
        conn = sqlite3.connect('timetable.db')
        cursor = conn.cursor()

        cursor.execute('SELECT COUNT(*) FROM timetables')
        total = cursor.fetchone()[0]
        conn.close()

        return jsonify({'total': total}), 200

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/api/admin/staff-registrations', methods=['GET'])
def list_registered_staff():
    conn = sqlite3.connect('timetable.db')
    cursor = conn.cursor()
    cursor.execute('SELECT name, email, staff_role, registered FROM staff_registrations ORDER BY created_at DESC')
    rows = cursor.fetchall()
    conn.close()

    result = [
        {
            'name': r[0],
            'email': r[1],
            'staff_role': r[2],
            'registered': bool(r[3])
        } for r in rows
    ]
    return jsonify(result), 200


@app.route('/api/admin/register-staff', methods=['POST'])
def register_staff():
    try:
        data = request.get_json()
        name = data.get('name')
        employee_id = data.get('employee_id')
        college = data.get('college')
        faculty = data.get('faculty')
        campus = data.get('campus')
        contact_number = data.get('contact_number')
        email = data.get('email')
        staff_role = data.get('staff_role')

        if not all([name, employee_id, college, faculty, campus, contact_number, email, staff_role]):
            return jsonify({'success': False, 'error': 'All fields are required'}), 400

        # Validate role
        valid_roles = [
            'hod',
            'associate_professor',
            'assistant_professor',
            'professor',
            'professor_sg',
            'vp',
            'dean'
        ]
        if staff_role not in valid_roles:
            return jsonify({'success': False, 'error': f'Invalid staff role: {staff_role}'}), 400

        # Generate credentials
        username = email.split('@')[0]
        password = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        conn = sqlite3.connect('timetable.db')
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO staff_registrations (
                name, employee_id, college, faculty, campus,
                contact_number, email, username, password, staff_role, registered
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            name, employee_id, college, faculty, campus,
            contact_number, email, username, password, staff_role, 0
        ))
        conn.commit()
        conn.close()

        return jsonify({
            'success': True,
            'message': 'Staff registered successfully',
            'credentials': {
                'username': username,
                'password': password
            }
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({'success': False, 'error': 'User already registered'}), 409
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500
    
# Run App
if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5000)
