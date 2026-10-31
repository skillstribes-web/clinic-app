import hmac
import os
import secrets
from datetime import datetime
from urllib.parse import quote

from flask import Flask, redirect, render_template_string, request, session
from groq import Groq

web = Flask(__name__)
web.secret_key = secrets.token_hex(32)
web.config["SESSION_COOKIE_SAMESITE"] = "Lax"

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

LOGIN_PAGE = """
<style>
  body { font-family: Arial, sans-serif; max-width: 400px; margin: 80px auto; padding: 0 15px; background: #f4f7fa; color: #222; }
  h1 { color: #0b6e4f; }
  input { padding: 6px 8px; border: 1px solid #bbb; border-radius: 4px; width: 100%; box-sizing: border-box; }
  button { margin-top: 12px; padding: 8px 14px; border: none; border-radius: 4px; background: #0b6e4f; color: white; cursor: pointer; }
  button:hover { background: #095a40; }
</style>

<h1>Clinic Login</h1>
{% if error %}
<p style="color: red;">{{ error }}</p>
{% endif %}
<form method="post" action="/login">
  <p>Password:</p>
  <input type="password" name="password" autofocus>
  <button type="submit">Log in</button>
</form>
"""

PAGE = """
<style>
  body { font-family: Arial, sans-serif; max-width: 1000px; margin: 30px auto; padding: 0 15px; background: #f4f7fa; color: #222; }
  h1 { color: #0b6e4f; }
  h2 { margin-top: 30px; }
  form p { margin: 8px 0; }
  input, select { padding: 6px 8px; border: 1px solid #bbb; border-radius: 4px; }
  button { padding: 6px 12px; border: none; border-radius: 4px; background: #0b6e4f; color: white; cursor: pointer; }
  button:hover { background: #095a40; }
  .red { background: #c0392b; }
  .red:hover { background: #962d22; }
  table { border-collapse: collapse; width: 100%; background: white; }
  th { background: #0b6e4f; color: white; }
  th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
</style>

<form method="post" action="/logout" style="float: right; margin: 0;">
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

<h2>New appointment</h2>
{% if error %}
<p style="color: red;">{{ error }}</p>
{% endif %}
<form method="post" action="/">
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
  <p>Time:
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
{% if appointments %}
<table>
  <tr><th>Patient</th><th>Age</th><th>Gender</th><th>Phone</th><th>Doctor</th><th>Date</th><th>Time</th><th></th></tr>
  {% for a in appointments %}
  <tr>
    <td>{{ a[0] }}</td>
    <td>{{ a[5] }}</td>
    <td>{{ a[4] }}</td>
    <td>{{ a[6] }}</td>
    <td>{{ a[1] }}</td>
    <td>{{ a[2] }}</td>
    <td>{{ a[3] }}</td>
    <td>
      <form method="post" action="/delete" style="margin: 0; display: inline;" onsubmit="return confirm('Are you sure you want to delete this appointment?')">
        <input type="hidden" name="name" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="date" value="{{ a[2] }}">
        <input type="hidden" name="time" value="{{ a[3] }}">
        <input type="hidden" name="gender" value="{{ a[4] }}">
        <input type="hidden" name="age" value="{{ a[5] }}">
        <input type="hidden" name="phone" value="{{ a[6] }}">
        <button type="submit" class="red">Delete</button>
      </form>
      <form method="post" action="/reminder" style="margin: 0; display: inline;">
        <input type="hidden" name="name" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="date" value="{{ a[2] }}">
        <input type="hidden" name="time" value="{{ a[3] }}">
        <input type="hidden" name="phone" value="{{ a[6] }}">
        <button type="submit">Reminder (AI)</button>
      </form>
      <form method="post" action="/unavailable" style="margin: 0; display: inline;">
        <input type="hidden" name="name" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="date" value="{{ a[2] }}">
        <input type="hidden" name="time" value="{{ a[3] }}">
        <input type="hidden" name="phone" value="{{ a[6] }}">
        <button type="submit">Doctor unavailable</button>
      </form>
    </td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p>No appointments saved yet</p>
{% endif %}
"""


def read_appointments():
    appointments = []
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 7:
                    appointments.append(parts)
    except FileNotFoundError:
        pass
    return appointments


def find_error(name, doctor, date, time, gender, age, phone):
    if name == "" or doctor == "" or date == "" or time == "" or gender == "" or age == "" or phone == "":
        return "Error: no field can be empty"

    for value in (name, doctor, date, time, gender, age, phone):
        if "," in value:
            return "Error: please do not use commas (,)"

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

    try:
        datetime.strptime(date, "%d-%m-%Y")
    except ValueError:
        return "Error: write the date like this: 05-11-2026"

    try:
        datetime.strptime(time, "%I:%M %p")
    except ValueError:
        return "Error: please choose a valid time"

    for n, d, dt, t, g, a, p in read_appointments():
        if d.lower() == doctor.lower() and dt == date and t.lower() == time.lower():
            return "Error: this doctor already has an appointment at that date and time"

    return ""


@web.before_request
def require_login():
    if request.endpoint in ("login", "static"):
        return None
    if not session.get("logged_in"):
        return redirect("/login")
    return None


@web.route("/login", methods=["GET", "POST"])
def login():
    error = ""
    if request.method == "POST":
        real_password = os.environ.get("CLINIC_PASSWORD", "")
        typed_password = request.form["password"]
        if real_password == "":
            error = "No password is set on this computer"
        elif hmac.compare_digest(typed_password.encode(), real_password.encode()):
            session["logged_in"] = True
            return redirect("/")
        else:
            error = "Wrong password"
    return render_template_string(LOGIN_PAGE, error=error)


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
        time = (
            request.form["hour"] + ":" + request.form["minute"]
            + " " + request.form["ampm"]
        )
        gender = request.form["gender"].strip()
        age = request.form["age"].strip()
        phone = request.form["phone"].strip()
        error = find_error(name, doctor, date, time, gender, age, phone)
        if error == "":
            with open("appointments.txt", "a") as f:
                f.write(
                    name + "," + doctor + "," + date + "," + time
                    + "," + gender + "," + age + "," + phone + "\n"
                )
            return redirect("/")
    return render_template_string(
        PAGE, appointments=read_appointments(), error=error,
        reminder="", whatsapp_link=""
    )


@web.route("/delete", methods=["POST"])
def delete():
    target = (
        request.form["name"] + ","
        + request.form["doctor"] + ","
        + request.form["date"] + ","
        + request.form["time"] + ","
        + request.form["gender"] + ","
        + request.form["age"] + ","
        + request.form["phone"]
    )
    try:
        with open("appointments.txt", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return redirect("/")

    with open("appointments.txt", "w") as f:
        for line in lines:
            if line.strip() != target:
                f.write(line)
    return redirect("/")


@web.route("/reminder", methods=["POST"])
def reminder():
    question = (
        "Write a short, polite reminder message for this appointment. "
        "Patient: " + request.form["name"]
        + ", Doctor: " + request.form["doctor"]
        + ", Date: " + request.form["date"]
        + ", Time: " + request.form["time"]
    )
    whatsapp_link = ""
    try:
        answer = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful clinic assistant. Always reply in English. Use only the information given, do not add any time, date or other details yourself. Write only the message and give no medical advice."},
                {"role": "user", "content": question},
            ],
            model="openai/gpt-oss-20b",
        )
        message = answer.choices[0].message.content
        whatsapp_link = "https://wa.me/" + request.form["phone"] + "?text=" + quote(message)
    except Exception:
        message = "Could not get a reply from the AI, please try again later"

    return render_template_string(
        PAGE, appointments=read_appointments(), error="",
        reminder=message, whatsapp_link=whatsapp_link
    )


@web.route("/unavailable", methods=["POST"])
def unavailable():
    question = (
        "Write a short, polite message telling a patient that the doctor is "
        "not available for this appointment and asking them to contact the "
        "clinic to reschedule. Patient: " + request.form["name"]
        + ", Doctor: " + request.form["doctor"]
        + ", Date: " + request.form["date"]
        + ", Time: " + request.form["time"]
    )
    whatsapp_link = ""
    try:
        answer = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "You are a helpful clinic assistant. Always reply in English. Use only the information given. Do not invent a new date, time, phone number or reason. Write only the message and give no medical advice."},
                {"role": "user", "content": question},
            ],
            model="openai/gpt-oss-20b",
        )
        message = answer.choices[0].message.content
        whatsapp_link = "https://wa.me/" + request.form["phone"] + "?text=" + quote(message)
    except Exception:
        message = "Could not get a reply from the AI, please try again later"

    return render_template_string(
        PAGE, appointments=read_appointments(), error="",
        reminder=message, whatsapp_link=whatsapp_link
    )


web.run(debug=True)