from flask import Flask, render_template, request
import sqlite3
import os
import smtplib
from email.mime.text import MIMEText
from email.utils import formataddr

app = Flask(__name__)

# --- Email and database configuration ---
DB_PATH = 'database.db'
FEEDBACK_NOTIFY_EMAIL = os.getenv('FEEDBACK_NOTIFY_EMAIL', 'chaitanyabakhal99@gmail.com')
SMTP_HOST = os.getenv('SMTP_HOST')
SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
SMTP_USER = os.getenv('SMTP_USER')
SMTP_PASS = os.getenv('SMTP_PASS')
SMTP_FROM = os.getenv('SMTP_FROM', SMTP_USER or 'no-reply@localhost')


def ensure_db():
    """Ensure the users table exists and has a created_at column for retention."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    # Create table if it doesn't exist (SQLite ignores schema differences on IF NOT EXISTS)
    cur.execute(
        'CREATE TABLE IF NOT EXISTS users (name TEXT, email TEXT, message TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP)'
    )
    # Ensure created_at column exists; add if missing
    cur.execute('PRAGMA table_info(users)')
    columns = [row[1] for row in cur.fetchall()]
    if 'created_at' not in columns:
        cur.execute("ALTER TABLE users ADD COLUMN created_at TEXT DEFAULT CURRENT_TIMESTAMP")
        # Backfill existing rows where created_at is NULL
        try:
            cur.execute("UPDATE users SET created_at = datetime('now') WHERE created_at IS NULL")
        except sqlite3.OperationalError:
            # In case some SQLite versions treat new column as non-nullable default only for new rows
            pass
    conn.commit()
    conn.close()


def cleanup_feedback():
    """Delete feedback entries older than 10 days based on created_at."""
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("DELETE FROM users WHERE datetime(created_at) < datetime('now','-10 days')")
    conn.commit()
    conn.close()


def send_feedback_email(full_name: str, sender_email: str, message: str) -> bool:
    """Send feedback details to the notify email. Returns True on success."""
    # If SMTP is not configured, log and skip
    if not (SMTP_HOST and SMTP_USER and SMTP_PASS and FEEDBACK_NOTIFY_EMAIL):
        print("Email not configured; skipping send. Set SMTP_HOST/SMTP_USER/SMTP_PASS and FEEDBACK_NOTIFY_EMAIL.")
        return False

    body = (
        f"New feedback submission\n\n"
        f"Name: {full_name}\n"
        f"Email: {sender_email}\n\n"
        f"Message:\n{message}\n"
    )
    msg = MIMEText(body)
    msg['Subject'] = 'New Feedback Submission'
    msg['From'] = formataddr(('Counseling Website', SMTP_FROM))
    msg['To'] = FEEDBACK_NOTIFY_EMAIL

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASS)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"Error sending feedback email: {e}")
        return False

_db_inited = False
@app.before_request
def init_db_once():
    """Ensure database schema exists for all deployments (e.g., gunicorn)."""
    global _db_inited
    if not _db_inited:
        try:
            ensure_db()
            _db_inited = True
        except Exception as e:
            print(f"DB init error: {e}")

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

@app.route('/members')
def members():
    return render_template('members.html')

@app.route('/contactus')
def contactus():
    return render_template('contactus.html')

@app.route('/education')
def education():
    return render_template('education.html')

@app.route('/feedback', methods=['GET', 'POST'])
def feedback():
    if request.method == 'POST':
        # Support both old and new field names
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        fallback_name = request.form.get('name', '').strip()
        full_name = (first_name + ' ' + last_name).strip() if (first_name or last_name) else fallback_name

        email = request.form.get('email', '').strip()
        message = request.form.get('message', '').strip()

        if not full_name or not email or not message:
            return render_template('feedback.html', error='Please fill out all fields')

        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute('INSERT INTO users (name, email, message, created_at) VALUES (?, ?, ?, datetime("now"))', (full_name, email, message))
        conn.commit()
        conn.close()

        # Send email notification (best-effort)
        email_ok = send_feedback_email(full_name, email, message)
        # Perform retention cleanup
        cleanup_feedback()

        success_msg = 'Message sent successfully!'
        if email_ok:
            success_msg += ' Notification email sent.'
        else:
            success_msg += ' (Notification email not configured.)'

        return render_template('feedback.html', success=success_msg)

    return render_template('feedback.html')

if __name__ == '__main__':
    # Ensure DB schema is ready before serving
    ensure_db()
    # Bind to all interfaces for LAN access; allow env override
    host = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    port = int(os.getenv('PORT', '5000'))
    app.run(host=host, port=port, debug=True)