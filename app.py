import os
from flask import Flask, render_template, request, redirect, session, url_for, send_file
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__, template_folder='templates', static_folder='pictures', static_url_path='/pictures')
app.secret_key = 'carvow_secret_key_123'

# --- FIX: anchor the database to this script's folder, not the current
# working directory. Using a bare relative filename like 'booking.php'
# meant the app could open/create a DIFFERENT file each time depending on
# how it was launched (double-clicking run.bat vs running from an IDE vs
# a terminal in another folder). That's why signups seemed to "disappear"
# and logins kept failing with a correct password: they were reading from
# a different, empty database file. Anchoring to the script's own folder
# guarantees the app always uses the same file, every time. ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'carvow.db')


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

    # 2. Print alert to console
    print(f"[EMAIL NOTIFICATION] to {to_email} | Subject: {subject}")

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
        user_email TEXT
    )
    """)

    # Try to add user_email column for existing database migrations
    try:
        cursor.execute("ALTER TABLE appointments ADD COLUMN user_email TEXT")
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


# Login routes matching filename
@app.route('/LOGIN PAGE.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            return render_template('LOGIN PAGE.html', error="Please fill all fields.")

        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user[3], password):
            session['user_email'] = email
            session['user_name'] = user[1]

            # Send login notification email
            subject = "Carvow Login Alert"
            body = f"Hello {user[1]},\n\nThis is a notification that your Carvow account was accessed successfully.\n\nIf you did not perform this login, please contact support or reset your password immediately.\n\nBest regards,\nCarvow Service Team"
            send_email(email, subject, body)

            if email == OWNER_EMAIL:
                return redirect('/admin.html')
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

# Booking page route
@app.route('/booking page.html')
def booking():
    if 'user_email' not in session:
        return redirect('/LOGIN.html')
    return render_template('booking page.html')

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

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO appointments
    (name, phone, car, service, date, time, user_email)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, phone, car, service, date, time, user_email))
    conn.commit()
    conn.close()

    # Send booking confirmation email notification
    subject = "Carvow Booking Confirmation"
    body = f"Hello,\n\nYour car service appointment has been scheduled successfully!\n\nBooking Details:\n- Name: {name}\n- Phone: {phone}\n- Car Model: {car}\n- Service Type: {service}\n- Date: {date}\n- Time: {time}\n\nThank you for choosing Carvow Car Service.\n\nBest regards,\nCarvow Service Team"
    send_email(user_email, subject, body)

    return redirect('/sucess.html')

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

    is_owner = (user_email == OWNER_EMAIL)

    if is_owner:
        # Owner sees all columns including customer email
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email FROM appointments")
    else:
        # Regular user only sees their own appointments
        cursor.execute("SELECT id, name, phone, car, service, date, time, user_email FROM appointments WHERE user_email = ?", (user_email,))
        
    appointments = cursor.fetchall()
    conn.close()

    return render_template('history.html', appointments=appointments, is_owner=is_owner)

# Admin Dashboard Routes
@app.route('/admin')
@app.route('/admin.html')
def admin():
    if 'user_email' not in session or session.get('user_email') != OWNER_EMAIL:
        return redirect('/LOGIN.html')

    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT id, name, phone, car, service, date, time, user_email FROM appointments ORDER BY id DESC")
    appointments = cursor.fetchall()
    
    cursor.execute("SELECT COUNT(*) FROM appointments")
    total_bookings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM users")
    total_users = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(DISTINCT service) FROM appointments")
    total_services = cursor.fetchone()[0]
    
    conn.close()

    return render_template('admin.html', appointments=appointments, total_bookings=total_bookings, total_users=total_users, total_services=total_services)

@app.route('/admin/delete/<int:id>')
def delete_appointment(id):
    if 'user_email' not in session or session.get('user_email') != OWNER_EMAIL:
        return redirect('/LOGIN.html')

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM appointments WHERE id = ?", (id,))
    conn.commit()
    conn.close()

    return redirect('/admin.html')

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
    app.run(debug=True, port=5001)

