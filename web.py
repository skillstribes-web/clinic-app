import hmac
import os
import secrets
import sqlite3
import time
from datetime import datetime, timedelta
from urllib.parse import quote
from zoneinfo import ZoneInfo

from flask import Flask, redirect, render_template_string, request, session
from groq import Groq
from werkzeug.security import check_password_hash, generate_password_hash

DB_FILE = "clinic.db"
CLINIC_TZ = os.environ.get("CLINIC_TZ", "Asia/Karachi")
AI_ENABLED = os.environ.get("CLINIC_AI") == "1"

MAX_FAILS = 5
LOCK_SECONDS = 600

failed_logins = {}


def get_secret_key():
    from_env = os.environ.get("CLINIC_SECRET_KEY", "")
    if from_env != "":
        return from_env
    if os.path.exists("secret.key"):
        with open("secret.key", "r") as f:
            saved = f.read().strip()
        if saved != "":
            return saved
    new_key = secrets.token_hex(32)
    with open("secret.key", "w") as f:
        f.write(new_key)
    return new_key


web = Flask(__name__)
web.secret_key = get_secret_key()
web.config["SESSION_COOKIE_SAMESITE"] = "Lax"
web.config["SESSION_COOKIE_HTTPONLY"] = True
web.config["SESSION_COOKIE_SECURE"] = os.environ.get("CLINIC_HTTPS") == "1"
web.permanent_session_lifetime = timedelta(hours=8)

DUMMY_HASH = generate_password_hash("dummy password for timing")

client = None
if AI_ENABLED:
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

COMMON_STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: Arial, sans-serif; max-width: 1100px; margin: 30px auto; padding: 0 15px; background: #f4f7fa; color: #222; }
  h1 { color: #0b6e4f; }
  h2 { margin-top: 30px; }
  form p { margin: 8px 0; }
  input, select { padding: 8px 10px; border: 1px solid #bbb; border-radius: 4px; font-size: 16px; }
  button { padding: 8px 14px; border: none; border-radius: 4px; background: #0b6e4f; color: white; cursor: pointer; font-size: 15px; }
  button:hover { background: #095a40; }
  .red { background: #c0392b; }
  .red:hover { background: #962d22; }
  table { border-collapse: collapse; width: 100%; background: white; }
  th { background: #0b6e4f; color: white; }
  th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
  td[data-label="Date"], td[data-label="Time"] { white-space: nowrap; }
  .inline-form { margin: 0; display: inline-block; }
  .inline-form button { margin: 3px 3px 3px 0; }

  @media (max-width: 700px) {
    body { margin: 15px auto; }
    h1 { font-size: 24px; }
    form p input:not([type="hidden"]), form p select { display: block; width: 100%; box-sizing: border-box; margin-top: 4px; }
    form p.time-row select { display: inline-block; width: auto; min-width: 70px; }
    input[name="q"] { display: block; width: 100%; box-sizing: border-box; margin-bottom: 8px; }
    button { min-height: 42px; }
    table, thead, tbody, tr, td { display: block; }
    table { background: transparent; }
    thead { display: none; }
    tr { margin-bottom: 14px; border: 1px solid #ddd; border-radius: 6px; background: white; }
    td { display: flex; justify-content: space-between; gap: 12px; border: none; border-bottom: 1px solid #eee; padding: 8px 12px; }
    td::before { content: attr(data-label); font-weight: bold; color: #555; }
    td:last-child { border-bottom: none; }
    td.actions { display: block; }
    td.actions::before { content: none; }
  }
</style>
"""

LOGIN_PAGE = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  body { font-family: Arial, sans-serif; max-width: 400px; margin: 80px auto; padding: 0 15px; background: #f4f7fa; color: #222; }
  h1 { color: #0b6e4f; }
  input { padding: 8px 10px; border: 1px solid #bbb; border-radius: 4px; width: 100%; box-sizing: border-box; font-size: 16px; }
  button { margin-top: 12px; padding: 10px 14px; border: none; border-radius: 4px; background: #0b6e4f; color: white; cursor: pointer; font-size: 15px; }
  button:hover { background: #095a40; }
</style>

<h1>Clinic Login</h1>
{% if no_users %}
<p style="color: red;">There are no users yet. Run create_user.py first.</p>
{% endif %}
{% if error %}
<p style="color: red;">{{ error }}</p>
{% endif %}
<form method="post" action="/login">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <p>Username:</p>
  <input name="username" autocomplete="username" autofocus>
  <p>Password:</p>
  <input type="password" name="password" autocomplete="current-password">
  <button type="submit">Log in</button>
</form>
"""

PAGE = COMMON_STYLE + """
<form method="post" action="/logout" style="float: right; margin: 0;">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <span style="margin-right: 8px;">{{ current_user }}</span>
  <button type="submit">Log out</button>
</form>
<h1>Clinic Appointment App</h1>

{% if reminder %}
<div style="border: 2px solid green; padding: 10px; margin: 10px 0; white-space: pre-wrap;">
  <b>Message:</b><br>{{ reminder }}
  {% if whatsapp_link %}
  <p><a href="{{ whatsapp_link }}" target="_blank">Open in WhatsApp</a></p>
  {% endif %}
</div>
{% endif %}

<h2>Today's appointments ({{ today_text }})</h2>
{% if today_appointments %}
<table>
  <thead>
  <tr><th>Time</th><th>Patient</th><th>Age</th><th>Doctor</th><th>Phone</th></tr>
  </thead>
  <tbody>
  {% for a in today_appointments %}
  <tr>
    <td data-label="Time">{{ a[3] }}</td>
    <td data-label="Patient">{{ a[0] }}</td>
    <td data-label="Age">{{ a[5] }}</td>
    <td data-label="Doctor">{{ a[1] }}</td>
    <td data-label="Phone">{{ a[6] }}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p>No appointments today</p>
{% endif %}

<h2>New appointment</h2>
{% if error %}
<p style="color: red;">{{ error }}</p>
{% endif %}
<form method="post" action="/">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <p>Patient name: <input name="name"></p>
  <p>Age: <input name="age" type="number" min="0" max="120"></p>
  <p>Gender:
    <select name="gender">
      <option>Male</option>
      <option>Female</option>
    </select>
  </p>
  <p>Phone (country code first, digits only): <input name="phone" placeholder="e.g. 15551234567"></p>
  <p>Doctor name: <input name="doctor"></p>
  <p>Date (e.g. 05-11-2026): <input name="date"></p>
  <p class="time-row">Time:
    <select name="hour">
      <option>1</option>
      <option>2</option>
      <option>3</option>
      <option>4</option>
      <option>5</option>
      <option>6</option>
      <option>7</option>
      <option>8</option>
      <option>9</option>
      <option>10</option>
      <option>11</option>
      <option>12</option>
    </select>
    :
    <select name="minute">
      <option>00</option>
      <option>15</option>
      <option>30</option>
      <option>45</option>
    </select>
    <select name="ampm">
      <option>AM</option>
      <option>PM</option>
    </select>
  </p>
  <button type="submit">Save</button>
</form>

<h2>All appointments</h2>
<form method="get" action="/" style="margin-bottom: 12px;">
  <input name="q" value="{{ q }}" placeholder="Search by name, doctor, date or phone" size="40">
  <button type="submit">Search</button>
  {% if q %}
  &nbsp; <a href="/">Clear</a>
  {% endif %}
</form>
{% if q %}
<p>Showing {{ appointments|length }} of {{ total }} appointments</p>
{% endif %}

{% if appointments %}
<table>
  <thead>
  <tr><th>Patient</th><th>Age</th><th>Gender</th><th>Phone</th><th>Doctor</th><th>Date</th><th>Time</th><th></th></tr>
  </thead>
  <tbody>
  {% for a in appointments %}
  <tr>
    <td data-label="Patient">{{ a[0] }}</td>
    <td data-label="Age">{{ a[5] }}</td>
    <td data-label="Gender">{{ a[4] }}</td>
    <td data-label="Phone">{{ a[6] }}</td>
    <td data-label="Doctor">{{ a[1] }}</td>
    <td data-label="Date">{{ a[2] }}</td>
    <td data-label="Time">{{ a[3] }}</td>
    <td class="actions">
      <form method="post" action="/reschedule" class="inline-form">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ a[7] }}">
        <button type="submit">Reschedule</button>
      </form>
      <form method="post" action="/reminder" class="inline-form">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="name" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="date" value="{{ a[2] }}">
        <input type="hidden" name="time" value="{{ a[3] }}">
        <input type="hidden" name="phone" value="{{ a[6] }}">
        <button type="submit">{{ "Reminder (AI)" if ai_enabled else "Reminder" }}</button>
      </form>
      <form method="post" action="/unavailable" class="inline-form">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="name" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="date" value="{{ a[2] }}">
        <input type="hidden" name="time" value="{{ a[3] }}">
        <input type="hidden" name="phone" value="{{ a[6] }}">
        <button type="submit">Doctor unavailable</button>
      </form>
      <form method="post" action="/delete" class="inline-form" onsubmit="return confirm('Are you sure you want to delete this appointment?')">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ a[7] }}">
        <button type="submit" class="red">Delete</button>
      </form>
    </td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
  {% if q %}
  <p>No appointments match your search.</p>
  {% else %}
  <p>No appointments saved yet</p>
  {% endif %}
{% endif %}
"""

RESCHEDULE_PAGE = COMMON_STYLE + """
<h1>Reschedule appointment</h1>
<p><b>Patient:</b> {{ a[0] }} &nbsp; | &nbsp; <b>Doctor:</b> {{ a[1] }}</p>
<p><b>Current date and time:</b> {{ a[2] }} at {{ a[3] }}</p>

{% if error %}
<p style="color: red;">{{ error }}</p>
{% endif %}

<form method="post" action="/reschedule/save">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <input type="hidden" name="id" value="{{ a[7] }}">
  <p>New date (e.g. 05-11-2026): <input name="new_date" value="{{ a[2] }}"></p>
  <p class="time-row">New time:
    <select name="hour">
      <option>1</option>
      <option>2</option>
      <option>3</option>
      <option>4</option>
      <option>5</option>
      <option>6</option>
      <option>7</option>
      <option>8</option>
      <option>9</option>
      <option>10</option>
      <option>11</option>
      <option>12</option>
    </select>
    :
    <select name="minute">
      <option>00</option>
      <option>15</option>
      <option>30</option>
      <option>45</option>
    </select>
    <select name="ampm">
      <option>AM</option>
      <option>PM</option>
    </select>
  </p>
  <button type="submit">Save new date and time</button>
  &nbsp; <a href="/">Cancel</a>
</form>
"""


def connect():
    return sqlite3.connect(DB_FILE)


def clinic_now():
    return datetime.now(ZoneInfo(CLINIC_TZ))


def init_db():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        age TEXT,
        gender TEXT,
        phone TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS appointments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        patient_id INTEGER,
        doctor TEXT,
        date TEXT,
        time TEXT
    )
    """)
    cur.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE COLLATE NOCASE,
        password_hash TEXT
    )
    """)
    conn.commit()
    conn.close()


def date_to_db(text):
    return datetime.strptime(text, "%d-%m-%Y").strftime("%Y-%m-%d")


def date_to_show(text):
    try:
        return datetime.strptime(text, "%Y-%m-%d").strftime("%d-%m-%Y")
    except ValueError:
        return text


def time_to_db(text):
    return datetime.strptime(text, "%I:%M %p").strftime("%H:%M")


def time_to_show(text):
    try:
        return datetime.strptime(text, "%H:%M").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return text


def row_to_show(row):
    a = list(row)
    a[2] = date_to_show(a[2])
    a[3] = time_to_show(a[3])
    return a


def read_appointments():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT patients.name, appointments.doctor, appointments.date, appointments.time,
               patients.gender, patients.age, patients.phone, appointments.id
        FROM appointments
        JOIN patients ON appointments.patient_id = patients.id
        ORDER BY appointments.date, appointments.time
    """)
    rows = cur.fetchall()
    conn.close()
    return [row_to_show(row) for row in rows]


def get_appointment(appointment_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT patients.name, appointments.doctor, appointments.date, appointments.time,
               patients.gender, patients.age, patients.phone, appointments.id
        FROM appointments
        JOIN patients ON appointments.patient_id = patients.id
        WHERE appointments.id = ?
    """, (appointment_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return row_to_show(row)


def add_appointment(name, doctor, date, time, gender, age, phone):
    conn = connect()
    cur = conn.cursor()

    cur.execute(
        "SELECT id FROM patients WHERE LOWER(name) = LOWER(?) AND phone = ?",
        (name, phone),
    )
    found = cur.fetchone()
    if found is None:
        cur.execute(
            "INSERT INTO patients (name, age, gender, phone) VALUES (?, ?, ?, ?)",
            (name, age, gender, phone),
        )
        patient_id = cur.lastrowid
    else:
        patient_id = found[0]
        cur.execute(
            "UPDATE patients SET age = ?, gender = ? WHERE id = ?",
            (age, gender, patient_id),
        )

    cur.execute(
        "INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)",
        (patient_id, doctor, date_to_db(date), time_to_db(time)),
    )
    conn.commit()
    conn.close()


def update_appointment_time(appointment_id, date, time):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE appointments SET date = ?, time = ? WHERE id = ?",
        (date_to_db(date), time_to_db(time), appointment_id),
    )
    conn.commit()
    conn.close()


def delete_appointment(appointment_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()


def get_id(form):
    try:
        return int(form["id"])
    except (KeyError, ValueError):
        return None


def render_main(error="", reminder="", whatsapp_link="", q=""):
    all_appointments = read_appointments()

    today_text = clinic_now().strftime("%d-%m-%Y")
    today_appointments = []
    for a in all_appointments:
        if a[2] == today_text:
            today_appointments.append(a)

    search = q.strip().lower()
    shown = []
    for a in all_appointments:
        text = " ".join([a[0], a[1], a[2], a[6]]).lower()
        if search in text:
            shown.append(a)

    return render_template_string(
        PAGE,
        appointments=shown,
        today_appointments=today_appointments,
        today_text=today_text,
        total=len(all_appointments),
        q=q.strip(),
        error=error,
        reminder=reminder,
        whatsapp_link=whatsapp_link,
    )


def build_time(form):
    return form["hour"] + ":" + form["minute"] + " " + form["ampm"]


def find_schedule_error(doctor, date, time, skip_id=None):
    try:
        date = datetime.strptime(date, "%d-%m-%Y").strftime("%d-%m-%Y")
    except ValueError:
        return "Error: write the date like this: 05-11-2026"

    try:
        time = datetime.strptime(time, "%I:%M %p").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return "Error: please choose a valid time"

    for a in read_appointments():
        same_slot = (
            a[1].lower() == doctor.lower()
            and a[2] == date
            and a[3].lower() == time.lower()
        )
        if same_slot and a[7] != skip_id:
            return "Error: this doctor already has an appointment at that date and time"

    return ""


def find_error(name, doctor, date, time, gender, age, phone):
    if name == "" or doctor == "" or date == "" or time == "" or gender == "" or age == "" or phone == "":
        return "Error: no field can be empty"

    if gender not in ("Male", "Female"):
        return "Error: please choose Male or Female"

    try:
        age_number = int(age)
    except ValueError:
        return "Error: age must be a number"
    if age_number < 0 or age_number > 120:
        return "Error: age must be between 0 and 120"

    if not phone.isdigit() or len(phone) < 8 or len(phone) > 15:
        return "Error: phone must be 8 to 15 digits with the country code, no spaces, no + sign"

    return find_schedule_error(doctor, date, time)


def get_csrf():
    if "csrf" not in session:
        session["csrf"] = secrets.token_hex(16)
    return session["csrf"]


@web.context_processor
def add_to_templates():
    return {
        "csrf": get_csrf(),
        "current_user": session.get("user", ""),
        "ai_enabled": AI_ENABLED,
    }


@web.after_request
def add_safety_headers(response):
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    return response


@web.before_request
def protect():
    if request.endpoint == "static":
        return None

    if request.method == "POST":
        sent = request.form.get("csrf", "")
        real = session.get("csrf", "")
        if real == "" or not hmac.compare_digest(sent, real):
            return '<p>This page expired. <a href="/">Go back</a> and try again.</p>', 400

    if request.endpoint != "login" and not session.get("user"):
        return redirect("/login")
    return None


def is_locked(key):
    now = time.time()
    recent = [t for t in failed_logins.get(key, []) if now - t < LOCK_SECONDS]
    failed_logins[key] = recent
    return len(recent) >= MAX_FAILS


def record_failure(key):
    failed_logins.setdefault(key, []).append(time.time())


def count_users():
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM users")
    number = cur.fetchone()[0]
    conn.close()
    return number


def check_login(username, password):
    conn = connect()
    cur = conn.cursor()
    cur.execute("SELECT username, password_hash FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        check_password_hash(DUMMY_HASH, password)
        return None
    if check_password_hash(row[1], password):
        return row[0]
    return None


@web.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        key = (request.remote_addr or "unknown") + "|" + username.lower()
        if is_locked(key):
            error = "Too many wrong attempts. Please wait 10 minutes and try again."
        else:
            real_name = check_login(username, password)
            if real_name is not None:
                failed_logins.pop(key, None)
                session.clear()
                session["user"] = real_name
                session.permanent = True
                return redirect("/")
            record_failure(key)
            error = "Wrong username or password"
    return render_template_string(LOGIN_PAGE, error=error, no_users=(count_users() == 0))


@web.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect("/login")


@web.route("/", methods=["GET", "POST"])
def home():
    error = ""
    if request.method == "POST":
        name = request.form["name"].strip()
        doctor = request.form["doctor"].strip()
        date = request.form["date"].strip()
        time = build_time(request.form)
        gender = request.form["gender"].strip()
        age = request.form["age"].strip()
        phone = request.form["phone"].strip()
        error = find_error(name, doctor, date, time, gender, age, phone)
        if error == "":
            add_appointment(name, doctor, date, time, gender, age, phone)
            return redirect("/")
    return render_main(error=error, q=request.args.get("q", ""))


@web.route("/reschedule", methods=["POST"])
def reschedule():
    appointment_id = get_id(request.form)
    a = get_appointment(appointment_id)
    if a is None:
        return redirect("/")
    return render_template_string(RESCHEDULE_PAGE, a=a, error="")


@web.route("/reschedule/save", methods=["POST"])
def reschedule_save():
    appointment_id = get_id(request.form)
    a = get_appointment(appointment_id)
    if a is None:
        return redirect("/")

    new_date = request.form["new_date"].strip()
    new_time = build_time(request.form)

    error = find_schedule_error(a[1], new_date, new_time, skip_id=a[7])
    if error != "":
        return render_template_string(RESCHEDULE_PAGE, a=a, error=error)

    update_appointment_time(a[7], new_date, new_time)
    return redirect("/")


@web.route("/delete", methods=["POST"])
def delete():
    appointment_id = get_id(request.form)
    if appointment_id is not None:
        delete_appointment(appointment_id)
    return redirect("/")


def doctor_title(doctor):
    name = doctor.strip()
    low = name.lower()
    if low.startswith("dr.") or low.startswith("dr ") or low.startswith("doctor "):
        return name
    return "Dr. " + name


def plain_message(kind, name, doctor, date, time):
    doctor = doctor_title(doctor)
    if kind == "unavailable":
        return (
            "Hello " + name + ", we are sorry, " + doctor
            + " is not available for your appointment on " + date
            + " at " + time + ". Please contact the clinic to reschedule."
        )
    return (
        "Hello " + name + ", this is a reminder of your appointment with "
        + doctor + " on " + date + " at " + time
        + ". Please contact the clinic if you need to change it."
    )


def write_message(kind, name, doctor, date, time):
    fallback = plain_message(kind, name, doctor, date, time)
    doctor = doctor_title(doctor)
    if not AI_ENABLED or client is None:
        return fallback

    # The patient name is never sent to the AI. We send a marker and
    # put the real name back ourselves.
    marker = "[PATIENT]"
    if kind == "unavailable":
        task = (
            "Write a short, polite message telling a patient that the doctor is "
            "not available for this appointment and asking them to contact the "
            "clinic to reschedule."
        )
        rule = "Do not invent a new date, time, phone number or reason."
    else:
        task = "Write a short, polite reminder message for this appointment."
        rule = "Do not add any time, date or other details yourself."
    question = (
        task + " Start with the greeting 'Hello " + marker + "'. "
        "Doctor: " + doctor + ", Date: " + date + ", Time: " + time
    )
    system = (
        "You are a helpful clinic assistant. Always reply in English. "
        "Use only the information given. " + rule + " "
        "Write the text " + marker + " exactly as it is, it will be replaced later. "
        "Write only the message and give no medical advice."
    )
    try:
        answer = client.chat.completions.create(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": question},
            ],
            model="openai/gpt-oss-20b",
        )
        message = answer.choices[0].message.content
        if message is None or message.strip() == "":
            return fallback
        return message.replace(marker, name)
    except Exception:
        return fallback


def message_page(kind):
    f = request.form
    message = write_message(kind, f["name"], f["doctor"], f["date"], f["time"])
    phone = "".join(ch for ch in f["phone"] if ch.isdigit())
    whatsapp_link = "https://wa.me/" + phone + "?text=" + quote(message)
    return render_main(reminder=message, whatsapp_link=whatsapp_link)


@web.route("/reminder", methods=["POST"])
def reminder():
    return message_page("reminder")


@web.route("/unavailable", methods=["POST"])
def unavailable():
    return message_page("unavailable")


init_db()

if __name__ == "__main__":
    web.run(debug=True)