import os
import jinja2
from flask import Flask, render_template, request, redirect, session, url_for, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, static_folder='pictures', static_url_path='/pictures')
app.secret_key = 'carvow_secret_key_123'

@app.after_request
def add_cors_headers(response):
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,X-Admin-Auth'
    response.headers['Access-Control-Allow-Methods'] = 'GET,PUT,POST,DELETE,OPTIONS'
    return response

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'carvow.db')

# Separate template loaders: customer portal from 'templates', admin portal from 'admin_portal'
app.jinja_loader = jinja2.ChoiceLoader([
    jinja2.FileSystemLoader(os.path.join(BASE_DIR, 'templates')),
    jinja2.FileSystemLoader(os.path.join(BASE_DIR, 'admin_portal'))
])


# --- EMAIL & SMTP CONFIGURATION ---
# To send real emails, enter your Gmail account and a Gmail App Password below.
# If these are left blank, all sent email notifications will be logged to
# 'sent_emails.txt' inside this folder instead of raising error messages.
SMTP_SERVER = 'smtp.gmail.com'
SMTP_PORT = 587
SMTP_USER = ''          # Enter your Gmail address (e.g. user@gmail.com)
SMTP_PASSWORD = ''      # Enter your Gmail App Password
OWNER_EMAIL = 'carvowservice@gmail.com'

def send_email(to_email, subject, body):
    import smtplib
    from email.mime.text import MIMEText
    
    # 1. Always log locally to 'sent_emails.txt' as a fail-safe audit log
    log_path = os.path.join(BASE_DIR, 'sent_emails.txt')
    try:
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(f"\n========================================\n")
            f.write(f"TO: {to_email}\n")
            f.write(f"SUBJECT: {subject}\n")
            f.write(f"CONTENT:\n{body}\n")
            f.write(f"========================================\n")
    except Exception as log_error:
        print(f"Failed to log email locally: {log_error}")

    # 2. Print alert to console safely
    try:
        print(f"[EMAIL NOTIFICATION] to {to_email} | Subject: {subject}")
    except Exception:
        safe_sub = subject.encode('ascii', 'replace').decode('ascii')
        print(f"[EMAIL NOTIFICATION] to {to_email} | Subject: {safe_sub}")

    # 3. If credentials are set, attempt SMTP send
    if SMTP_USER and SMTP_PASSWORD:
        try:
            msg = MIMEText(body)
            msg['Subject'] = subject
            msg['From'] = SMTP_USER
            msg['To'] = to_email
            
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, to_email, msg.as_string())
            server.quit()
            print(f"[SMTP SUCCESS] Real email sent to {to_email}")
        except Exception as smtp_error:
            print(f"[SMTP ERROR] Failed to send email via SMTP: {smtp_error}")


def get_db():
    return sqlite3.connect(DB_PATH)


# Create database tables
def init_db():
    conn = get_db()
    cursor = conn.cursor()

    # Table for appointments
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS appointments(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        phone TEXT,
        car TEXT,
        service TEXT,
        date TEXT,
        time TEXT,
        user_email TEXT,
        status TEXT DEFAULT 'Pending',
        admin_note TEXT DEFAULT ''
    )
    """)

    # Try to add missing columns for existing database migrations
    try:
        cursor.execute("ALTER TABLE appointments ADD COLUMN user_email TEXT")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE appointments ADD COLUMN status TEXT DEFAULT 'Pending'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE appointments ADD COLUMN admin_note TEXT DEFAULT ''")
    except sqlite3.OperationalError:
        pass

    # Table for user authentication
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT UNIQUE,
        password TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# Predefined Service Slots
DEFAULT_SLOTS = ["09:00 AM", "10:30 AM", "12:00 PM", "02:00 PM", "03:30 PM", "05:00 PM"]
SLOT_CAPACITY = 2

# Main landing page routes
@app.route('/')
@app.route('/appointment login.html')
def home():
    return render_template('appointment login.html')

# Selection page route
@app.route('/LOGIN.html')
def login_selection():
    return render_template('LOGIN.html')


# Signup routes matching filename
@app.route('/Sign up page.html', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            return render_template('Sign up page.html', error="Please fill all fields.")

        username = email.split('@')[0]
        hashed_password = generate_password_hash(password)

        conn = get_db()
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, hashed_password))
            conn.commit()
            conn.close()
            
            # Send registration welcome email
            subject = "Welcome to Carvow Car Service!"
            body = f"Hello {username},\n\nYour account has been registered successfully with the email {email}.\n\nYou can now log in and schedule your car maintenance service appointments online.\n\nBest regards,\nCarvow Service Team"
            send_email(email, subject, body)

            # Auto login the user upon successful signup
            session['user_email'] = email
            session['user_name'] = username
            return redirect('/booking page.html')
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('Sign up page.html', error="Email is already registered!")

    return render_template('Sign up page.html')


ADMIN_EMAIL = 'carvowservice@gmail.com'
ADMIN_PASSWORD = 'admin123'

ALLOWED_ADMIN_EMAILS = ['carvowservice@gmail.com', 'admin@carvow.com', 'admin']

# Admin Login Route
@app.route('/admin/login', methods=['GET', 'POST'])
@app.route('/admin_login.html', methods=['GET', 'POST'])
@app.route('/admin_portal/admin_login.html', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        if request.is_json:
            data = request.get_json() or {}
            email = data.get('email', '').strip().lower()
            password = data.get('password', '')
        else:
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')

        is_valid = False
        if (email in ALLOWED_ADMIN_EMAILS or email == OWNER_EMAIL) and password == ADMIN_PASSWORD:
            is_valid = True
        else:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT password FROM users WHERE email = ?", (email,))
            row = cursor.fetchone()
            conn.close()
            if row and check_password_hash(row[0], password) and (email in ALLOWED_ADMIN_EMAILS or email == OWNER_EMAIL):
                is_valid = True

        if is_valid:
            session['user_email'] = email
            session['user_name'] = 'Administrator'
            session['is_admin'] = True

            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {"success": True, "redirect": "/admin"}
            return redirect('/admin')
        else:
            if request.is_json or request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return {"success": False, "error": "Invalid Admin Email or Password!"}, 401
            return render_template('admin_login.html', error="Invalid Admin Email or Password!", email=email)

    return render_template('admin_login.html')

# Dedicated Admin Logout Route
@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect('/admin/login')

# Login routes matching filename
@app.route('/LOGIN PAGE.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            return render_template('LOGIN PAGE.html', error="Please fill all fields.")

        # 1. Check if Admin credentials were submitted through Customer Login
        if (email in ALLOWED_ADMIN_EMAILS or email == OWNER_EMAIL) and password == ADMIN_PASSWORD:
            session['user_email'] = email
            session['user_name'] = 'Administrator'
            session['is_admin'] = True
            return redirect('/admin')

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            # Check if this registered user has an admin email
            if email in ALLOWED_ADMIN_EMAILS or email == OWNER_EMAIL:
                session['user_email'] = email
                session['user_name'] = 'Administrator'
                session['is_admin'] = True
                return redirect('/admin')

            # Regular customer login: strictly customer portal access
            session['user_email'] = email
            session['user_name'] = user[1]
            session['is_admin'] = False

            # Send login notification email
            subject = "Carvow Login Alert"
            body = f"Hello {user[1]},\n\nThis is a notification that your Carvow account was accessed successfully.\n\nIf you did not perform this login, please contact support or reset your password immediately.\n\nBest regards,\nCarvow Service Team"
            send_email(email, subject, body)

            return redirect('/booking page.html')
        else:
            return render_template('LOGIN PAGE.html', error="Invalid Email or Password!")

    return render_template('LOGIN PAGE.html')


# Forgot Password routes matching filename
@app.route('/forgot password.html', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        new_password = request.form.get('password')

        if not email or not new_password:
            return render_template('forgot password.html', error="Please fill all fields.")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()

        if user:
            # Update password
            hashed_password = generate_password_hash(new_password)
            cursor.execute("UPDATE users SET password = ? WHERE email = ?", (hashed_password, email))
            conn.commit()
            conn.close()
            
            # Send password reset notification email
            subject = "Carvow Password Reset Confirmed"
            body = f"Hello {user[1]},\n\nYour password has been reset successfully.\n\nYou can now schedule your service appointments online.\n\nBest regards,\nCarvow Service Team"
            send_email(email, subject, body)

            # Auto login the user upon successful reset
            session['user_email'] = email
            session['user_name'] = user[1]
            return redirect('/booking page.html')
        else:
            conn.close()
            return render_template('forgot password.html', error="Email is not registered!")

    return render_template('forgot password.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect('/appointment login.html')

# API Route: Check Slot Availability
@app.route('/api/available-slots')
def get_available_slots():
    date = request.args.get('date', '').strip()
    if not date:
        return {"error": "Date is required"}, 400

    conn = get_db()
    cursor = conn.cursor()
    # Count active bookings (Pending or Accepted) per time slot on that date
    cursor.execute("""
        SELECT time, COUNT(*) 
        FROM appointments 
        WHERE date = ? AND (status IS NULL OR status != 'Declined')
        GROUP BY time
    """, (date,))
    
    rows = cursor.fetchall()
    conn.close()

    booked_counts = {row[0]: row[1] for row in rows}

    slots_data = []
    for slot in DEFAULT_SLOTS:
        booked = booked_counts.get(slot, 0)
        remaining = max(0, SLOT_CAPACITY - booked)
        slots_data.append({
            "slot": slot,
            "booked": booked,
            "capacity": SLOT_CAPACITY,
            "remaining": remaining,
            "available": remaining > 0
        })

    return {"date": date, "slots": slots_data}

# Booking page route
@app.route('/booking page.html')
def booking():
    if 'user_email' not in session:
        return redirect('/LOGIN.html')
    return render_template('booking page.html', slots=DEFAULT_SLOTS)

# Book post action
@app.route('/book', methods=['POST'])
def book():
    if 'user_email' not in session:
        return redirect('/LOGIN.html')

    name = request.form.get('name')
    phone = request.form.get('phone')
    car = request.form.get('car')
    service = request.form.get('service')
    date = request.form.get('date')
    time = request.form.get('time')
    user_email = session.get('user_email')

    # Check slot availability
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT COUNT(*) FROM appointments 
        WHERE date = ? AND time = ? AND (status IS NULL OR status != 'Declined')
    """, (date, time))
    booked_count = cursor.fetchone()[0]

    if booked_count >= SLOT_CAPACITY:
        conn.close()
        return render_template('booking page.html', error=f"The slot {time} on {date} is already full! Please select another time slot.", slots=DEFAULT_SLOTS)

    cursor.execute("""
    INSERT INTO appointments
    (name, phone, car, service, date, time, user_email, status, admin_note)
    VALUES (?, ?, ?, ?, ?, ?, ?, 'Pending', '')
    """, (name, phone, car, service, date, time, user_email))
    conn.commit()
    conn.close()

    # Send booking confirmation email notification
    subject = "Carvow Booking Request Received [Pending Approval]"
    body = f"Hello {name},\n\nYour car service appointment request has been submitted successfully and is currently PENDING approval by Carvow Team.\n\nRequest Details:\n- Name: {name}\n- Phone: {phone}\n- Car Model: {car}\n- Service Type: {service}\n- Date: {date}\n- Time Slot: {time}\n- Status: Pending Approval\n\nWe will notify you once your request is accepted or reviewed.\n\nThank you for choosing Carvow Car Service.\n\nBest regards,\nCarvow Service Team"
    send_email(user_email, subject, body)

    # Send alert to Admin
    send_email(OWNER_EMAIL, f"New Booking Request from {name}", f"New booking pending approval:\nCustomer: {name} ({user_email})\nCar: {car}\nService: {service}\nDate: {date} at {time}")

    return redirect('/sucess.html')

# Admin Dashboard Route
@app.route('/admin')
@app.route('/admin.html')
@app.route('/admin_portal')
@app.route('/admin_portal/')
@app.route('/admin_portal/admin.html')
def admin_dashboard():
    # If logged in as admin or owner email, grant admin access
    if session.get('is_admin') or session.get('user_email') in [OWNER_EMAIL, ADMIN_EMAIL]:
        session['is_admin'] = True
    else:
        return redirect('/admin/login')

    conn = get_db()
    cursor = conn.cursor()

    # Filter status if requested
    status_filter = request.args.get('status', 'all')
    valid_filters = ['Pending', 'Accepted', 'In Progress', 'Completed', 'Declined']
    if status_filter in valid_filters:
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email, status, admin_note FROM appointments WHERE status = ? ORDER BY id DESC", (status_filter,))
    else:
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email, status, admin_note FROM appointments ORDER BY id DESC")
    
    rows = cursor.fetchall()

    # Get Metrics
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Pending' OR status IS NULL OR status = ''")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Accepted'")
    accepted_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'In Progress'")
    in_progress_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Completed'")
    completed_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Declined'")
    declined_count = cursor.fetchone()[0]

    conn.close()

    metrics = {
        "total": total_count,
        "pending": pending_count,
        "accepted": accepted_count,
        "in_progress": in_progress_count,
        "completed": completed_count,
        "declined": declined_count
    }

    appointments = []
    for r in rows:
        appointments.append({
            "id": r[0],
            "name": r[1] or '',
            "phone": r[2] or '',
            "car": r[3] or '',
            "service": r[4] or '',
            "date": r[5] or '',
            "time": r[6] or '',
            "user_email": r[7] or '',
            "status": r[8] if r[8] else 'Pending',
            "admin_note": r[9] if r[9] else ''
        })

    return render_template('admin.html', appointments=appointments, metrics=metrics, current_filter=status_filter, owner_email=OWNER_EMAIL)

# API Route for Real-Time Live Admin Data from carvow.db
@app.route('/api/admin/appointments')
def api_admin_appointments():
    auth_key = request.headers.get('X-Admin-Auth') or request.args.get('auth')
    if not (session.get('is_admin') or session.get('user_email') in [OWNER_EMAIL, ADMIN_EMAIL] or auth_key == 'admin123'):
        return {"error": "Unauthorized"}, 403

    status_filter = request.args.get('status', 'all')
    conn = get_db()
    cursor = conn.cursor()

    valid_filters = ['Pending', 'Accepted', 'In Progress', 'Completed', 'Declined']
    if status_filter in valid_filters:
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email, status, admin_note FROM appointments WHERE status = ? ORDER BY id DESC", (status_filter,))
    else:
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email, status, admin_note FROM appointments ORDER BY id DESC")
    
    rows = cursor.fetchall()

    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Pending' OR status IS NULL OR status = ''")
    pending_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Accepted'")
    accepted_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'In Progress'")
    in_progress_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Completed'")
    completed_count = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Declined'")
    declined_count = cursor.fetchone()[0]

    conn.close()

    metrics = {
        "total": total_count,
        "pending": pending_count,
        "accepted": accepted_count,
        "in_progress": in_progress_count,
        "completed": completed_count,
        "declined": declined_count
    }

    appointments = []
    for r in rows:
        appointments.append({
            "id": r[0],
            "name": r[1] or '',
            "phone": r[2] or '',
            "car": r[3] or '',
            "service": r[4] or '',
            "date": r[5] or '',
            "time": r[6] or '',
            "user_email": r[7] or '',
            "status": r[8] if r[8] else 'Pending',
            "admin_note": r[9] if r[9] else ''
        })

    return {"metrics": metrics, "appointments": appointments, "current_filter": status_filter}

# Admin Action: Universal Status Update (Accepted, In Progress, Completed, Declined)
@app.route('/admin/update-status/<int:appointment_id>', methods=['POST', 'GET'])
def admin_update_status(appointment_id):
    auth_key = request.headers.get('X-Admin-Auth') or request.args.get('auth')
    if not (session.get('is_admin') or session.get('user_email') in [OWNER_EMAIL, ADMIN_EMAIL] or auth_key == 'admin123'):
        return {"error": "Unauthorized"}, 403

    new_status = request.form.get('status', request.args.get('status', 'Accepted')).strip()
    admin_note = request.form.get('admin_note', request.args.get('admin_note', '')).strip()

    valid_statuses = ['Accepted', 'In Progress', 'Completed', 'Declined']
    if new_status not in valid_statuses:
        return {"error": "Invalid status"}, 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT name, user_email, car, service, date, time FROM appointments WHERE id = ?", (appointment_id,))
    app_data = cursor.fetchone()

    if app_data:
        name, cust_email, car, service, date, time = app_data

        if not admin_note:
            if new_status == 'Accepted': admin_note = 'Approved by Admin'
            elif new_status == 'In Progress': admin_note = 'Servicing underway by technicians'
            elif new_status == 'Completed': admin_note = 'Service completed. Ready for customer pickup.'
            elif new_status == 'Declined': admin_note = 'Slot full / unavailable'

        cursor.execute("UPDATE appointments SET status = ?, admin_note = ? WHERE id = ?", (new_status, admin_note, appointment_id))
        conn.commit()
        conn.close()

        # Send milestone email notification to customer
        if new_status == 'Accepted':
            subject = "🎉 Carvow Service Request APPROVED!"
            body = f"Hello {name},\n\nGreat news! Your car service booking request has been ACCEPTED by Carvow Service Team.\n\nConfirmed Details:\n- Customer: {name}\n- Car Model: {car}\n- Service Type: {service}\n- Scheduled Date: {date}\n- Confirmed Time Slot: {time}\n- Status: ACCEPTED\n- Admin Note: {admin_note}\n\nPlease arrive 10 minutes prior to your time slot.\n\nThank you for choosing Carvow!\n\nBest regards,\nCarvow Service Team"
        elif new_status == 'In Progress':
            subject = "🔧 Work Underway - Your Car Servicing Has Started!"
            body = f"Hello {name},\n\nLive Service Update: Our technicians have started servicing your vehicle!\n\nDetails:\n- Car Model: {car}\n- Service Type: {service}\n- Scheduled Time: {date} at {time}\n- Status: WORK STILL IN PROGRESS 🔧\n- Note: {admin_note}\n\nWe will inform you as soon as work is complete!\n\nBest regards,\nCarvow Service Team"
        elif new_status == 'Completed':
            subject = "🎉 Service Completed - Your Car Is Ready for Pickup!"
            body = f"Hello {name},\n\nGreat news! Servicing for your {car} is now FULLY COMPLETED!\n\nSummary:\n- Car Model: {car}\n- Service Type: {service}\n- Status: WORK COMPLETED - READY FOR PICKUP 🎉🚘\n- Note: {admin_note}\n\nPlease visit Carvow center to pick up your vehicle.\n\nThank you for choosing Carvow!\n\nBest regards,\nCarvow Service Team"
        elif new_status == 'Declined':
            subject = "Carvow Service Request Status Update"
            body = f"Hello {name},\n\nWe regret to inform you that your car service booking request for {date} at {time} ({service}) could not be accepted at this time.\n\nReason / Note from Admin:\n{admin_note}\n\nYour slot has been released. You are welcome to log in and select another available time slot or date.\n\nBest regards,\nCarvow Service Team"

        send_email(cust_email, subject, body)
    else:
        conn.close()

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest' or request.is_json:
        return {"success": True, "message": f"Status updated to {new_status}"}
    return redirect('/admin.html')

# Backward compatibility routes
@app.route('/admin/accept/<int:appointment_id>', methods=['POST', 'GET'])
def admin_accept(appointment_id):
    return admin_update_status(appointment_id)

@app.route('/admin/decline/<int:appointment_id>', methods=['POST', 'GET'])
def admin_decline(appointment_id):
    return admin_update_status(appointment_id)


# Success page route
@app.route('/sucess.html')
def success():
    if 'user_email' not in session:
        return redirect('/LOGIN.html')
    return render_template('sucess.html')

# History page route
@app.route('/history.html')
def history():
    if 'user_email' not in session:
        return redirect('/LOGIN.html')

    user_email = session.get('user_email')
    conn = get_db()
    cursor = conn.cursor()

    is_owner = (user_email == OWNER_EMAIL) or session.get('is_admin')

    if is_owner:
        # Owner sees all columns including customer email, status, note
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email, status, admin_note FROM appointments ORDER BY id DESC")
    else:
        # Regular user only sees their own appointments
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email, status, admin_note FROM appointments WHERE user_email = ? ORDER BY id DESC", (user_email,))
        
    appointments = cursor.fetchall()
    conn.close()

    return render_template('history.html', appointments=appointments, is_owner=is_owner)

# Static content pages
@app.route('/about.html')
def about():
    return render_template('about.html')

@app.route('/contact.html')
def contact():
    return render_template('contact.html')

# API test check route
@app.route('/check')
def check():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments")
    data = cursor.fetchall()
    conn.close()
    return str(data)



if __name__ == '__main__':
    import socket
    try:
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        print("\n=======================================================")
        print("  CARVOW CAR SERVICE - MULTI-DEVICE SERVER STARTED  ")
        print("=======================================================")
        print(f" Local Access (This PC):    http://127.0.0.1:5001/")
        print(f" Any Device on Wi-Fi/LAN:   http://{local_ip}:5001/")
        print("=======================================================\n")
    except Exception:
        pass
    app.run(host='0.0.0.0', port=5001, debug=True)


