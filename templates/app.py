from flask import Flask, render_template, request, redirect, session, url_for
import sqlite3

app = Flask(__name__, template_folder='templates', static_folder='pictures', static_url_path='/pictures')
app.secret_key = 'carvow_secret_key_123'

# Create database tables
def init_db():
    conn = sqlite3.connect('booking.php')
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

        conn = sqlite3.connect('booking.php')
        cursor = conn.cursor()
        try:
            cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
            conn.commit()
            conn.close()
            # Redirect to login page upon success
            return redirect('/LOGIN PAGE.html')
        except sqlite3.IntegrityError:
            conn.close()
            return render_template('Sign up page.html', error="Email is already registered!")
            
    return render_template('Sign up page.html')

# Login routes matching filename
@app.route('/LOGIN PAGE.html', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        name = request.form.get('name')
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password')

        if not email or not password:
            return render_template('LOGIN PAGE.html', error="Please fill all fields.")

        conn = sqlite3.connect('booking.php')
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE email = ? AND password = ?", (email, password))
        user = cursor.fetchone()
        conn.close()

        if user:
            session['user_email'] = email
            session['user_name'] = name or user[1]
            return redirect('/booking page.html')
        else:
            return render_template('LOGIN PAGE.html', error="Invalid Email or Password!")

    return render_template('LOGIN PAGE.html')

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

    conn = sqlite3.connect('booking.php')
    cursor = conn.cursor()
    cursor.execute("""
    INSERT INTO appointments
    (name, phone, car, service, date, time, user_email)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (name, phone, car, service, date, time, user_email))
    conn.commit()
    conn.close()

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

    conn = sqlite3.connect('booking.php')
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, phone, car, service, date, time FROM appointments WHERE user_email = ?", (user_email,))
    appointments = cursor.fetchall()
    conn.close()

    return render_template('history.html', appointments=appointments)

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
    conn = sqlite3.connect('booking.php')
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM appointments")
    data = cursor.fetchall()
    conn.close()
    return str(data)

if __name__ == '__main__':
    app.run(debug=True)