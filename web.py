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
CLINIC_NAME = os.environ.get("CLINIC_NAME", "Clinic Appointment App")

STATUSES = ["Scheduled", "Done", "No-show", "Cancelled"]

MAX_FAILS = 5
LOCK_SECONDS = 600


def env_number(name, default, low, high):
    try:
        value = int(os.environ.get(name, str(default)))
    except ValueError:
        return default
    return max(low, min(high, value))


# One session takes this many minutes. Two sessions of the same doctor cannot overlap.
SESSION_MINUTES = env_number("CLINIC_SESSION_MIN", 30, 5, 240)
# How many patients one doctor can treat at the same moment (helpers working in parallel).
PARALLEL = env_number("CLINIC_PARALLEL", 1, 1, 20)
MAX_COURSE_DAYS = 60
MAX_SESSIONS_PER_DAY = 5

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

# Colours live here, in one place. Dark teal theme.
THEME_CSS = """
  :root {
    color-scheme: dark;
    --bg: #0b1514;
    --surface: #142523;
    --field: #1b302d;
    --border: #2f4d49;
    --text: #eef5f3;
    --muted: #a9c0bc;
    --accent: #2fbfae;
    --accent-hover: #5fd3c4;
    --on-accent: #04201c;
    --danger: #c0392b;
    --danger-hover: #a93226;
    --error-text: #ff7b72;
  }
"""

COMMON_STYLE = (
    """
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ clinic_name }}</title>
<style>
"""
    + THEME_CSS
    + """
  body { font-family: Arial, sans-serif; max-width: 1100px; margin: 30px auto; padding: 0 15px; background: var(--bg); color: var(--text); }
  h1 { color: var(--accent); }
  h2 { margin-top: 30px; }
  a { color: var(--accent); }
  form p { margin: 8px 0; }
  input, select { padding: 8px 10px; border: 1px solid var(--border); border-radius: 4px; font-size: 16px; background: var(--field); color: var(--text); }
  option { background: var(--field); color: var(--text); }
  input::placeholder { color: var(--muted); }
  input:focus, select:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
  button { padding: 8px 14px; border: none; border-radius: 4px; background: var(--accent); color: var(--on-accent); font-weight: bold; cursor: pointer; font-size: 15px; }
  button:hover { background: var(--accent-hover); }
  .red { background: var(--danger); color: white; }
  .red:hover { background: var(--danger-hover); }
  .error { color: var(--error-text); }
  .message { border: 2px solid var(--accent); background: var(--surface); padding: 10px; margin: 10px 0; }
  .message-text { white-space: pre-wrap; }
  table { border-collapse: collapse; width: 100%; background: var(--surface); }
  th { background: var(--accent); color: var(--on-accent); }
  th, td { border: 1px solid var(--border); padding: 8px; text-align: left; }
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
    tr { margin-bottom: 14px; border: 1px solid var(--border); border-radius: 6px; background: var(--surface); }
    td { display: flex; justify-content: space-between; gap: 12px; border: none; border-bottom: 1px solid var(--border); padding: 8px 12px; }
    td::before { content: attr(data-label); font-weight: bold; color: var(--muted); }
    td:last-child { border-bottom: none; }
    td.actions { display: block; }
    td.actions::before { content: none; }
  }
</style>
"""
)

LOGIN_PAGE = (
    """
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{{ clinic_name }}</title>
<style>
"""
    + THEME_CSS
    + """
  body { font-family: Arial, sans-serif; max-width: 400px; margin: 80px auto; padding: 0 15px; background: var(--bg); color: var(--text); }
  h1 { color: var(--accent); }
  input { padding: 8px 10px; border: 1px solid var(--border); border-radius: 4px; width: 100%; box-sizing: border-box; font-size: 16px; background: var(--field); color: var(--text); }
  input:focus { outline: 2px solid var(--accent); outline-offset: 1px; }
  button { margin-top: 12px; padding: 10px 14px; border: none; border-radius: 4px; background: var(--accent); color: var(--on-accent); font-weight: bold; cursor: pointer; font-size: 15px; }
  button:hover { background: var(--accent-hover); }
  .error { color: var(--error-text); }
</style>
"""
    + """
<h1>{{ clinic_name }}</h1>
<p>Staff login</p>
{% if no_users %}
<p class="error">There are no users yet. Run create_user.py first.</p>
{% endif %}
{% if error %}
<p class="error">{{ error }}</p>
{% endif %}
<form method="post" action="/login">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <p>Username:</p>
  <input name="username" autocomplete="username" autofocus>
  <p>Password:</p>
  <input type="password" name="password" autocomplete="current-password">
  <button type="submit">Log in</button>
</form>
""")

PAGE = COMMON_STYLE + """
<form method="post" action="/logout" style="float: right; margin: 0;">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <span style="margin-right: 8px;">{{ current_user }}</span>
  <button type="submit">Log out</button>
</form>
<h1>{{ clinic_name }}</h1>
<p><a href="/patients">Patients</a> &nbsp;|&nbsp; <a href="/doctors">Doctors</a> &nbsp;|&nbsp; <a href="/course">New course</a></p>

{% if reminder %}
<div class="message">
  <b>Message:</b><br><span class="message-text">{{ reminder }}</span>
  {% if whatsapp_link %}
  <p><a href="{{ whatsapp_link }}" target="_blank">Open in WhatsApp</a></p>
  {% endif %}
</div>
{% endif %}

<h2>Today's appointments ({{ today_text }})</h2>
{% if today_appointments %}
<table>
  <thead>
  <tr><th>Time</th><th>Patient</th><th>Age</th><th>Doctor</th><th>Phone</th><th>Status</th><th></th></tr>
  </thead>
  <tbody>
  {% for a in today_appointments %}
  <tr>
    <td data-label="Time">{{ a[3] }}</td>
    <td data-label="Patient"><span>{{ a[0] }}{% if a[11] %}<br><small>Day {{ a[10] }} of {{ a[11] }}</small>{% endif %}</span></td>
    <td data-label="Age">{{ a[5] }}</td>
    <td data-label="Doctor">{{ a[1] }}</td>
    <td data-label="Phone">{{ a[6] }}</td>
    <td data-label="Status">{{ a[8] }}</td>
    <td class="actions">
      <form method="post" action="/status" class="inline-form keep-scroll">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ a[7] }}">
        <input type="hidden" name="status" value="Done">
        <button type="submit">Came</button>
      </form>
      <form method="post" action="/status" class="inline-form keep-scroll">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ a[7] }}">
        <input type="hidden" name="status" value="No-show">
        <button type="submit" class="red">Did not come</button>
      </form>
    </td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p>No appointments today</p>
{% endif %}

{% if missed %}
<h3>Did not come today</h3>
<ul>
  {% for m in missed %}
  <li>{{ m[0] }} ({{ m[1] }}) &nbsp; <a href="{{ m[2] }}" target="_blank">Message on WhatsApp</a></li>
  {% endfor %}
</ul>
{% endif %}

<h2>New appointment</h2>
{% if error %}
<p class="error">{{ error }}</p>
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
  <p>Doctor:
    {% if doctors %}
    <select name="doctor">
      {% for d in doctors %}
      <option>{{ d }}</option>
      {% endfor %}
    </select>
    {% else %}
    <span class="error">No doctors yet.</span> <a href="/doctors">Add a doctor first</a>
    {% endif %}
  </p>
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
{% if hidden %}
<p>{{ hidden }} later course sessions are hidden. Search for a patient's name to see all of their sessions.</p>
{% endif %}

{% if appointments %}
<table>
  <thead>
  <tr><th>Patient</th><th>Age</th><th>Gender</th><th>Phone</th><th>Doctor</th><th>Date</th><th>Time</th><th>Status</th><th></th></tr>
  </thead>
  <tbody>
  {% for a in appointments %}
  <tr>
    <td data-label="Patient"><span>{{ a[0] }}{% if a[11] %}<br><small>Day {{ a[10] }} of {{ a[11] }}</small>{% endif %}</span></td>
    <td data-label="Age">{{ a[5] }}</td>
    <td data-label="Gender">{{ a[4] }}</td>
    <td data-label="Phone">{{ a[6] }}</td>
    <td data-label="Doctor">{{ a[1] }}</td>
    <td data-label="Date">{{ a[2] }}</td>
    <td data-label="Time">{{ a[3] }}</td>
    <td data-label="Status">{{ a[8] }}</td>
    <td class="actions">
      <form method="post" action="/reschedule" class="inline-form">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ a[7] }}">
        <button type="submit">Reschedule</button>
      </form>
      <form method="post" action="/status" class="inline-form keep-scroll">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ a[7] }}">
        <select name="status">
          {% for s in statuses %}
          <option{% if s == a[8] %} selected{% endif %}>{{ s }}</option>
          {% endfor %}
        </select>
        <button type="submit">Set status</button>
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
      {% if a[9] %}
      <form method="post" action="/course/stop" class="inline-form keep-scroll" onsubmit="return confirm('Cancel all remaining sessions of this course, from today?')">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ a[7] }}">
        <button type="submit" class="red">Stop course</button>
      </form>
      {% endif %}
      <form method="post" action="/delete" class="inline-form keep-scroll" onsubmit="return confirm('Are you sure you want to delete this appointment?')">
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

<script>
// After Delete or Set status the page reloads; put the reader back where they were.
(function () {
  try {
    var saved = sessionStorage.getItem("scrollY");
    if (saved !== null) {
      sessionStorage.removeItem("scrollY");
      window.scrollTo(0, parseInt(saved, 10));
    }
    document.addEventListener("submit", function (e) {
      if (e.defaultPrevented) { return; }
      if (e.target.classList && e.target.classList.contains("keep-scroll")) {
        sessionStorage.setItem("scrollY", String(window.scrollY));
      }
    });
  } catch (err) {}
})();
</script>
"""

COURSE_PAGE = COMMON_STYLE + """
<form method="post" action="/logout" style="float: right; margin: 0;">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <span style="margin-right: 8px;">{{ current_user }}</span>
  <button type="submit">Log out</button>
</form>
<h1>New course</h1>
<p><a href="/">&larr; Back to appointments</a></p>
<p>Books the same time every day for one patient. Sundays are skipped. Each session takes {{ session_minutes }} minutes.
If the doctor is busy on any day, nothing is saved.</p>
{% if error %}
<p class="error">{{ error }}</p>
{% endif %}
<form method="post" action="/course">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <p>Patient name: <input name="name" value="{{ f.get('name', '') }}"></p>
  <p>Age: <input name="age" type="number" min="0" max="120" value="{{ f.get('age', '') }}"></p>
  <p>Gender:
    <select name="gender">
      <option{% if f.get('gender') == 'Male' %} selected{% endif %}>Male</option>
      <option{% if f.get('gender') == 'Female' %} selected{% endif %}>Female</option>
    </select>
  </p>
  <p>Phone (country code first, digits only): <input name="phone" placeholder="e.g. 15551234567" value="{{ f.get('phone', '') }}"></p>
  <p>Doctor:
    {% if doctors %}
    <select name="doctor">
      {% for d in doctors %}
      <option{% if f.get('doctor') == d %} selected{% endif %}>{{ d }}</option>
      {% endfor %}
    </select>
    {% else %}
    <span class="error">No doctors yet.</span> <a href="/doctors">Add a doctor first</a>
    {% endif %}
  </p>
  <p>Start date (e.g. 05-11-2026): <input name="start" value="{{ f.get('start', '') }}"></p>
  <p>Number of days (1 to {{ max_days }}): <input name="days" type="number" min="1" max="{{ max_days }}" value="{{ f.get('days', '') }}"></p>

  <div id="times">
    {% for t in times %}
    <p class="time-row session-row">
      <span class="session-label">{{ "First session time" if loop.first else "Session " ~ loop.index ~ " time" }}</span><br>
      <select name="hour">
        {% for h in hours %}<option{% if t[0] == h %} selected{% endif %}>{{ h }}</option>{% endfor %}
      </select>
      :
      <select name="minute">
        {% for m in minutes %}<option{% if t[1] == m %} selected{% endif %}>{{ m }}</option>{% endfor %}
      </select>
      <select name="ampm">
        {% for x in ampms %}<option{% if t[2] == x %} selected{% endif %}>{{ x }}</option>{% endfor %}
      </select>
      {% if not loop.first %}<button type="button" class="red remove-session">Remove</button>{% endif %}
    </p>
    {% endfor %}
  </div>
  <p><button type="button" id="add-session">+ Add session</button></p>

  <button type="submit">Book course</button>
</form>

<script>
// "+ Add session" adds one more time row (next one starts 45 minutes later).
(function () {
  var box = document.getElementById("times");
  var add = document.getElementById("add-session");
  var MAX = {{ max_sessions }};

  function renumber() {
    var rows = box.querySelectorAll(".session-row");
    for (var i = 0; i < rows.length; i++) {
      rows[i].querySelector(".session-label").textContent =
        i === 0 ? "First session time" : "Session " + (i + 1) + " time";
    }
    add.style.display = rows.length >= MAX ? "none" : "";
  }

  add.addEventListener("click", function () {
    var rows = box.querySelectorAll(".session-row");
    var last = rows[rows.length - 1];
    var h = parseInt(last.querySelector("[name=hour]").value, 10) % 12;
    var m = parseInt(last.querySelector("[name=minute]").value, 10);
    if (last.querySelector("[name=ampm]").value === "PM") { h += 12; }
    var total = (h * 60 + m + 45) % 1440;
    var h24 = Math.floor(total / 60);
    var copy = last.cloneNode(true);
    copy.querySelector("[name=hour]").value = String(h24 % 12 === 0 ? 12 : h24 % 12);
    copy.querySelector("[name=minute]").value = (total % 60 < 10 ? "0" : "") + (total % 60);
    copy.querySelector("[name=ampm]").value = h24 >= 12 ? "PM" : "AM";
    if (!copy.querySelector(".remove-session")) {
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "red remove-session";
      btn.textContent = "Remove";
      copy.appendChild(document.createTextNode(" "));
      copy.appendChild(btn);
    }
    box.appendChild(copy);
    renumber();
  });

  box.addEventListener("click", function (e) {
    if (e.target.classList.contains("remove-session")) {
      e.target.closest(".session-row").remove();
      renumber();
    }
  });

  renumber();
})();
</script>
"""

PATIENTS_PAGE = COMMON_STYLE + """
<form method="post" action="/logout" style="float: right; margin: 0;">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <span style="margin-right: 8px;">{{ current_user }}</span>
  <button type="submit">Log out</button>
</form>
<h1>Patients</h1>
<p><a href="/">&larr; Back to appointments</a></p>

<form method="get" action="/patients" style="margin-bottom: 12px;">
  <input name="q" value="{{ q }}" placeholder="Search by name or phone" size="40">
  <button type="submit">Search</button>
  {% if q %}
  &nbsp; <a href="/patients">Clear</a>
  {% endif %}
</form>
<p>Showing {{ patients|length }} of {{ total }} patients</p>

{% if patients %}
<table>
  <thead>
  <tr><th>Patient</th><th>Age</th><th>Gender</th><th>Phone</th><th>Appointments</th><th>Last appointment</th></tr>
  </thead>
  <tbody>
  {% for p in patients %}
  <tr>
    <td data-label="Patient">{{ p[1] }}</td>
    <td data-label="Age">{{ p[2] }}</td>
    <td data-label="Gender">{{ p[3] }}</td>
    <td data-label="Phone">{{ p[4] }}</td>
    <td data-label="Appointments">{{ p[5] }}</td>
    <td data-label="Last appointment">{{ p[6] }}</td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p>No patients found.</p>
{% endif %}
"""

DOCTORS_PAGE = COMMON_STYLE + """
<form method="post" action="/logout" style="float: right; margin: 0;">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <span style="margin-right: 8px;">{{ current_user }}</span>
  <button type="submit">Log out</button>
</form>
<h1>Doctors</h1>
<p><a href="/">&larr; Back to appointments</a></p>

<h2>Add a doctor</h2>
{% if error %}
<p class="error">{{ error }}</p>
{% endif %}
<form method="post" action="/doctors/add">
  <input type="hidden" name="csrf" value="{{ csrf }}">
  <p>Name as it should appear (e.g. Dr. Waseem Khan): <input name="name" maxlength="60"></p>
  <button type="submit">Add doctor</button>
</form>

<h2>Doctors in the list</h2>
{% if doctors %}
<table>
  <thead>
  <tr><th>Doctor</th><th>Appointments</th><th></th></tr>
  </thead>
  <tbody>
  {% for d in doctors %}
  <tr>
    <td data-label="Doctor">{{ d[1] }}</td>
    <td data-label="Appointments">{{ d[2] }}</td>
    <td class="actions">
      {% if d[2] == 0 %}
      <form method="post" action="/doctors/delete" class="inline-form" onsubmit="return confirm('Remove this doctor from the list?')">
        <input type="hidden" name="csrf" value="{{ csrf }}">
        <input type="hidden" name="id" value="{{ d[0] }}">
        <button type="submit" class="red">Remove</button>
      </form>
      {% else %}
      Has appointments
      {% endif %}
    </td>
  </tr>
  {% endfor %}
  </tbody>
</table>
{% else %}
<p>No doctors yet. Add the first one above.</p>
{% endif %}
"""

RESCHEDULE_PAGE = COMMON_STYLE + """
<h1>Reschedule appointment</h1>
<p><b>Patient:</b> {{ a[0] }} &nbsp; | &nbsp; <b>Doctor:</b> {{ a[1] }}</p>
<p><b>Current date and time:</b> {{ a[2] }} at {{ a[3] }}</p>

{% if error %}
<p class="error">{{ error }}</p>
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
    cur.execute("""
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE COLLATE NOCASE
    )
    """)
    cur.execute("SELECT COUNT(*) FROM doctors")
    if cur.fetchone()[0] == 0:
        cur.execute(
            "INSERT OR IGNORE INTO doctors (name) "
            "SELECT DISTINCT TRIM(doctor) FROM appointments WHERE TRIM(doctor) != ''"
        )
    cur.execute("PRAGMA table_info(appointments)")
    columns = [row[1] for row in cur.fetchall()]
    if "status" not in columns:
        cur.execute("ALTER TABLE appointments ADD COLUMN status TEXT DEFAULT 'Scheduled'")
    for column in ("course_id", "day_no", "days_total"):
        if column not in columns:
            cur.execute("ALTER TABLE appointments ADD COLUMN " + column + " INTEGER")
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
               patients.gender, patients.age, patients.phone, appointments.id,
               COALESCE(appointments.status, 'Scheduled'),
               appointments.course_id, appointments.day_no, appointments.days_total
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
               patients.gender, patients.age, patients.phone, appointments.id,
               COALESCE(appointments.status, 'Scheduled'),
               appointments.course_id, appointments.day_no, appointments.days_total
        FROM appointments
        JOIN patients ON appointments.patient_id = patients.id
        WHERE appointments.id = ?
    """, (appointment_id,))
    row = cur.fetchone()
    conn.close()
    if row is None:
        return None
    return row_to_show(row)


def find_or_add_patient(cur, name, age, gender, phone):
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
        return cur.lastrowid
    cur.execute(
        "UPDATE patients SET age = ?, gender = ? WHERE id = ?",
        (age, gender, found[0]),
    )
    return found[0]


def add_appointment(name, doctor, date, time, gender, age, phone):
    conn = connect()
    cur = conn.cursor()
    patient_id = find_or_add_patient(cur, name, age, gender, phone)
    cur.execute(
        "INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)",
        (patient_id, doctor, date_to_db(date), time_to_db(time)),
    )
    conn.commit()
    conn.close()


def add_course(name, doctor, visits, gender, age, phone, days_total):
    # visits is a list of (date, time, day_number). They are all saved together.
    conn = connect()
    cur = conn.cursor()
    patient_id = find_or_add_patient(cur, name, age, gender, phone)
    cur.execute("SELECT COALESCE(MAX(course_id), 0) + 1 FROM appointments")
    course_id = cur.fetchone()[0]
    for date, time, day_no in visits:
        cur.execute(
            "INSERT INTO appointments (patient_id, doctor, date, time, course_id, day_no, days_total) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (patient_id, doctor, date_to_db(date), time_to_db(time), course_id, day_no, days_total),
        )
    conn.commit()
    conn.close()


def stop_course(course_id):
    # Cancels the sessions of this course from today onwards that are still Scheduled.
    today = clinic_now().strftime("%Y-%m-%d")
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE appointments SET status = 'Cancelled' "
        "WHERE course_id = ? AND date >= ? AND COALESCE(status, 'Scheduled') = 'Scheduled'",
        (course_id, today),
    )
    count = cur.rowcount
    conn.commit()
    conn.close()
    return count


def update_appointment_time(appointment_id, date, time):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE appointments SET date = ?, time = ? WHERE id = ?",
        (date_to_db(date), time_to_db(time), appointment_id),
    )
    conn.commit()
    conn.close()


def update_status(appointment_id, status):
    conn = connect()
    cur = conn.cursor()
    cur.execute(
        "UPDATE appointments SET status = ? WHERE id = ?",
        (status, appointment_id),
    )
    conn.commit()
    conn.close()


def delete_appointment(appointment_id):
    conn = connect()
    cur = conn.cursor()
    cur.execute("DELETE FROM appointments WHERE id = ?", (appointment_id,))
    conn.commit()
    conn.close()


def read_patients():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT patients.id, patients.name, patients.age, patients.gender, patients.phone,
               COUNT(appointments.id), MAX(appointments.date)
        FROM patients
        LEFT JOIN appointments ON appointments.patient_id = patients.id
        GROUP BY patients.id
        ORDER BY patients.name COLLATE NOCASE
    """)
    rows = cur.fetchall()
    conn.close()
    result = []
    for row in rows:
        p = list(row)
        if p[6] is None:
            p[6] = "-"
        else:
            p[6] = date_to_show(p[6])
        result.append(p)
    return result


def read_doctors():
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        SELECT doctors.id, doctors.name, COUNT(appointments.id)
        FROM doctors
        LEFT JOIN appointments ON appointments.doctor = doctors.name COLLATE NOCASE
        GROUP BY doctors.id
        ORDER BY doctors.name COLLATE NOCASE
    """)
    rows = cur.fetchall()
    conn.close()
    return rows


def add_doctor(name):
    conn = connect()
    cur = conn.cursor()
    try:
        cur.execute("INSERT INTO doctors (name) VALUES (?)", (name,))
        conn.commit()
        added = True
    except sqlite3.IntegrityError:
        added = False
    conn.close()
    return added


def delete_doctor(doctor_id):
    # Only a doctor with no appointments can be removed.
    conn = connect()
    cur = conn.cursor()
    cur.execute("""
        DELETE FROM doctors
        WHERE id = ?
        AND NOT EXISTS (
            SELECT 1 FROM appointments
            WHERE appointments.doctor = doctors.name COLLATE NOCASE
        )
    """, (doctor_id,))
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

    missed = []
    for a in today_appointments:
        if a[8] == "No-show":
            text = "Hello " + a[0] + ", we missed you at your session today. Please let us know when you can come."
            phone = "".join(ch for ch in a[6] if ch.isdigit())
            missed.append((a[0], a[6], "https://wa.me/" + phone + "?text=" + quote(text)))

    notice = session.pop("notice", "")

    # Course sessions that are more than 3 days away would fill the list, so they are
    # hidden until the reader searches (for example by the patient's name).
    last_shown_day = (clinic_now() + timedelta(days=3)).date()
    search = q.strip().lower()
    shown = []
    hidden = 0
    for a in all_appointments:
        text = " ".join([a[0], a[1], a[2], a[6], a[8]]).lower()
        if search not in text:
            continue
        if search == "" and a[9] is not None and datetime.strptime(a[2], "%d-%m-%Y").date() > last_shown_day:
            hidden += 1
            continue
        shown.append(a)

    return render_template_string(
        PAGE,
        appointments=shown,
        today_appointments=today_appointments,
        missed=missed,
        hidden=hidden,
        doctors=[d[1] for d in read_doctors()],
        today_text=today_text,
        total=len(all_appointments),
        q=q.strip(),
        error=error,
        reminder=reminder or notice,
        whatsapp_link=whatsapp_link,
    )


def build_time(form):
    return form["hour"] + ":" + form["minute"] + " " + form["ampm"]


def to_minutes(time_text):
    t = datetime.strptime(time_text, "%I:%M %p")
    return t.hour * 60 + t.minute


def find_schedule_error(doctor, date, time, skip_id=None, existing=None):
    try:
        date = datetime.strptime(date, "%d-%m-%Y").strftime("%d-%m-%Y")
    except ValueError:
        return "Error: write the date like this: 05-11-2026"

    try:
        time = datetime.strptime(time, "%I:%M %p").strftime("%I:%M %p").lstrip("0")
    except ValueError:
        return "Error: please choose a valid time"

    start = to_minutes(time)
    end = start + SESSION_MINUTES

    if existing is None:
        existing = read_appointments()

    busy = []
    for a in existing:
        if a[1].lower() != doctor.lower() or a[2] != date:
            continue
        if a[7] == skip_id or a[8] == "Cancelled":
            continue
        try:
            s_start = to_minutes(a[3])
        except ValueError:
            continue
        busy.append((s_start, s_start + SESSION_MINUTES))

    # How many sessions run at the same moment? Look at the start of the new session
    # and at the start of every old session that begins while the new one is running.
    moments = [start] + [b[0] for b in busy if start < b[0] < end]
    for moment in moments:
        running = 1
        for b in busy:
            if b[0] <= moment < b[1]:
                running += 1
        if running > PARALLEL:
            return (
                "Error: this doctor is already busy at that time (each session takes "
                + str(SESSION_MINUTES) + " minutes)"
            )

    return ""


def find_patient_error(name, doctor, gender, age, phone):
    if name == "" or doctor == "" or gender == "" or age == "" or phone == "":
        return "Error: no field can be empty"

    if doctor.lower() not in [d[1].lower() for d in read_doctors()]:
        return "Error: please choose a doctor from the list"

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

    return ""


def find_error(name, doctor, date, time, gender, age, phone):
    if date == "" or time == "":
        return "Error: no field can be empty"

    error = find_patient_error(name, doctor, gender, age, phone)
    if error != "":
        return error

    return find_schedule_error(doctor, date, time)


def plan_course(doctor, start_text, days_text, times):
    # times is the list of session times of one day, like ["3:00 PM", "3:45 PM"].
    # Returns (visits, error). A visit is (date, time, day_number). Sundays are skipped.
    try:
        start = datetime.strptime(start_text, "%d-%m-%Y").date()
    except ValueError:
        return [], "Error: write the start date like this: 05-11-2026"
    if start < clinic_now().date():
        return [], "Error: the start date cannot be in the past"

    try:
        days = int(days_text)
    except ValueError:
        return [], "Error: the number of days must be a number"
    if days < 1 or days > MAX_COURSE_DAYS:
        return [], "Error: the number of days must be between 1 and " + str(MAX_COURSE_DAYS)

    if len(times) < 1 or len(times) > MAX_SESSIONS_PER_DAY:
        return [], "Error: choose 1 to " + str(MAX_SESSIONS_PER_DAY) + " sessions per day"
    try:
        minutes = [to_minutes(t) for t in times]
    except ValueError:
        return [], "Error: please choose valid times"
    for i in range(1, len(minutes)):
        if minutes[i] - minutes[i - 1] < SESSION_MINUTES:
            return [], (
                "Error: each session must start at least "
                + str(SESSION_MINUTES) + " minutes after the one before it"
            )

    visits = []
    day = start
    day_no = 0
    while day_no < days:
        if day.weekday() != 6:
            day_no += 1
            for t in times:
                visits.append((day.strftime("%d-%m-%Y"), t, day_no))
        day += timedelta(days=1)

    existing = read_appointments()
    clashes = []
    for date, t, day_no in visits:
        if find_schedule_error(doctor, date, t, existing=existing) != "":
            clashes.append(date + " " + t)
    if clashes:
        shown = ", ".join(clashes[:5])
        if len(clashes) > 5:
            shown += " and " + str(len(clashes) - 5) + " more"
        return [], "Error: the doctor is busy on " + shown + ". Nothing was saved. Try another time."

    return visits, ""


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
        "statuses": STATUSES,
        "clinic_name": CLINIC_NAME,
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
        doctor = request.form.get("doctor", "").strip()
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


def render_doctors(error=""):
    return render_template_string(DOCTORS_PAGE, doctors=read_doctors(), error=error)


@web.route("/doctors")
def doctors():
    return render_doctors()


@web.route("/doctors/add", methods=["POST"])
def doctors_add():
    name = request.form.get("name", "").strip()
    if name == "":
        return render_doctors(error="Error: please write the doctor's name")
    if len(name) > 60:
        return render_doctors(error="Error: the name can be 60 letters at most")
    if not add_doctor(name):
        return render_doctors(error="Error: this doctor is already in the list")
    return redirect("/doctors")


@web.route("/doctors/delete", methods=["POST"])
def doctors_delete():
    doctor_id = get_id(request.form)
    if doctor_id is not None:
        delete_doctor(doctor_id)
    return redirect("/doctors")


@web.route("/patients")
def patients():
    all_patients = read_patients()
    q = request.args.get("q", "").strip()
    search = q.lower()
    shown = []
    for p in all_patients:
        text = (p[1] + " " + p[4]).lower()
        if search in text:
            shown.append(p)
    return render_template_string(
        PATIENTS_PAGE, patients=shown, total=len(all_patients), q=q
    )


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


@web.route("/status", methods=["POST"])
def status():
    appointment_id = get_id(request.form)
    new_status = request.form.get("status", "")
    if appointment_id is not None and new_status in STATUSES:
        update_status(appointment_id, new_status)
    return redirect("/")


@web.route("/delete", methods=["POST"])
def delete():
    appointment_id = get_id(request.form)
    if appointment_id is not None:
        delete_appointment(appointment_id)
    return redirect("/")


DEFAULT_SLOTS = [("3", "00", "PM")]


def render_course(error="", form=None, slots=None):
    f = {"gender": "Male", "days": "10"}
    if form:
        f.update(form)
    return render_template_string(
        COURSE_PAGE,
        f=f,
        error=error,
        times=slots or DEFAULT_SLOTS,
        doctors=[d[1] for d in read_doctors()],
        hours=[str(h) for h in range(1, 13)],
        minutes=["00", "15", "30", "45"],
        ampms=["AM", "PM"],
        max_days=MAX_COURSE_DAYS,
        max_sessions=MAX_SESSIONS_PER_DAY,
        session_minutes=SESSION_MINUTES,
    )


@web.route("/course", methods=["GET", "POST"])
def course():
    if request.method == "GET":
        return render_course(form={"start": clinic_now().strftime("%d-%m-%Y")})

    f = request.form
    name = f.get("name", "").strip()
    doctor = f.get("doctor", "").strip()
    gender = f.get("gender", "").strip()
    age = f.get("age", "").strip()
    phone = f.get("phone", "").strip()
    start = f.get("start", "").strip()
    days = f.get("days", "").strip()

    hours = f.getlist("hour")
    minutes = f.getlist("minute")
    ampms = f.getlist("ampm")
    slots = []
    if len(hours) == len(minutes) == len(ampms):
        slots = list(zip(hours, minutes, ampms))
    times = [h + ":" + m + " " + a for h, m, a in slots]

    error = find_patient_error(name, doctor, gender, age, phone)
    if error == "" and (start == "" or days == "" or not times):
        error = "Error: no field can be empty"
    visits = []
    if error == "":
        visits, error = plan_course(doctor, start, days, times)
    if error != "":
        return render_course(error=error, form=f.to_dict(), slots=slots)

    add_course(name, doctor, visits, gender, age, phone, int(days))
    session["notice"] = (
        "Course booked for " + name + ": " + days + " days, "
        + str(len(visits)) + " sessions, from " + visits[0][0] + " to " + visits[-1][0]
        + ". Sundays are skipped."
    )
    return redirect("/")


@web.route("/course/stop", methods=["POST"])
def course_stop():
    a = get_appointment(get_id(request.form))
    if a is not None and a[9] is not None:
        count = stop_course(a[9])
        session["notice"] = "Course stopped for " + a[0] + ": " + str(count) + " sessions cancelled."
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