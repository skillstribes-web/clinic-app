from datetime import datetime

from flask import Flask, redirect, render_template_string, request

web = Flask(__name__)

PAGE = """
<h1>Clinic Appointment App</h1>

<h2>Naya appointment</h2>
{% if galti %}
<p style="color: red;">{{ galti }}</p>
{% endif %}
<form method="post">
  <p>Patient ka naam: <input name="naam"></p>
  <p>Doctor ka naam: <input name="doctor"></p>
  <p>Tareekh (jaise 05-11-2026): <input name="tareekh"></p>
  <p>Waqt (jaise 5 baje shaam): <input name="waqt"></p>
  <button type="submit">Save karo</button>
</form>

<h2>Saari appointments</h2>
{% if appointments %}
<table border="1" cellpadding="8">
  <tr><th>Patient</th><th>Doctor</th><th>Tareekh</th><th>Waqt</th><th></th></tr>
  {% for a in appointments %}
  <tr>
    <td>{{ a[0] }}</td>
    <td>{{ a[1] }}</td>
    <td>{{ a[2] }}</td>
    <td>{{ a[3] }}</td>
    <td>
      <form method="post" action="/hatao" style="margin: 0;">
        <input type="hidden" name="naam" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="tareekh" value="{{ a[2] }}">
        <input type="hidden" name="waqt" value="{{ a[3] }}">
        <button type="submit">Hatao</button>
      </form>
    </td>
  </tr>
  {% endfor %}
</table>
{% else %}
<p>Abhi koi appointment save nahi hai</p>
{% endif %}
"""


def appointments_parho():
    appointments = []
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                hisse = line.strip().split(",")
                if len(hisse) == 4:
                    appointments.append(hisse)
    except FileNotFoundError:
        pass
    return appointments


def galti_dhoondo(naam, doctor, tareekh, waqt):
    if naam == "" or doctor == "" or tareekh == "" or waqt == "":
        return "Galti: koi bhi cheez khali nahi honi chahiye"

    if "," in naam or "," in doctor or "," in tareekh or "," in waqt:
        return "Galti: comma (,) mat likho"

    try:
        datetime.strptime(tareekh, "%d-%m-%Y")
    except ValueError:
        return "Galti: tareekh aise likho: 05-11-2026"

    for n, d, t, w in appointments_parho():
        if d.lower() == doctor.lower() and t == tareekh and w.lower() == waqt.lower():
            return "Galti: is doctor ki us tareekh aur waqt par pehle se appointment hai"

    return ""


@web.route("/", methods=["GET", "POST"])
def home():
    galti = ""
    if request.method == "POST":
        naam = request.form["naam"].strip()
        doctor = request.form["doctor"].strip()
        tareekh = request.form["tareekh"].strip()
        waqt = request.form["waqt"].strip()
        galti = galti_dhoondo(naam, doctor, tareekh, waqt)
        if galti == "":
            with open("appointments.txt", "a") as f:
                f.write(naam + "," + doctor + "," + tareekh + "," + waqt + "\n")
            return redirect("/")
    return render_template_string(PAGE, appointments=appointments_parho(), galti=galti)


@web.route("/hatao", methods=["POST"])
def hatao():
    cheez = (
        request.form["naam"] + ","
        + request.form["doctor"] + ","
        + request.form["tareekh"] + ","
        + request.form["waqt"]
    )
    try:
        with open("appointments.txt", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        return redirect("/")

    with open("appointments.txt", "w") as f:
        for line in lines:
            if line.strip() != cheez:
                f.write(line)
    return redirect("/")


web.run(debug=True)