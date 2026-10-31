import os
from datetime import datetime

from flask import Flask, redirect, render_template_string, request
from groq import Groq

web = Flask(__name__)

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

PAGE = """
<style>
  body { font-family: Arial, sans-serif; max-width: 900px; margin: 30px auto; padding: 0 15px; background: #f4f7fa; color: #222; }
  h1 { color: #0b6e4f; }
  h2 { margin-top: 30px; }
  form p { margin: 8px 0; }
  input { padding: 6px 8px; border: 1px solid #bbb; border-radius: 4px; }
  button { padding: 6px 12px; border: none; border-radius: 4px; background: #0b6e4f; color: white; cursor: pointer; }
  button:hover { background: #095a40; }
  table { border-collapse: collapse; width: 100%; background: white; }
  th { background: #0b6e4f; color: white; }
  th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
</style><h1>Clinic Appointment App</h1>

{% if reminder %}
<div style="border: 2px solid green; padding: 10px; margin: 10px 0; white-space: pre-wrap;">
  <b>Reminder message:</b><br>{{ reminder }}
</div>
{% endif %}

<h2>Naya appointment</h2>
{% if galti %}
<p style="color: red;">{{ galti }}</p>
{% endif %}
<form method="post" action="/">
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
      <form method="post" action="/hatao" style="margin: 0; display: inline;">
        <input type="hidden" name="naam" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="tareekh" value="{{ a[2] }}">
        <input type="hidden" name="waqt" value="{{ a[3] }}">
        <button type="submit">Hatao</button>
      </form>
      <form method="post" action="/reminder" style="margin: 0; display: inline;">
        <input type="hidden" name="naam" value="{{ a[0] }}">
        <input type="hidden" name="doctor" value="{{ a[1] }}">
        <input type="hidden" name="tareekh" value="{{ a[2] }}">
        <input type="hidden" name="waqt" value="{{ a[3] }}">
        <button type="submit">Reminder (AI)</button>
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
    return render_template_string(
        PAGE, appointments=appointments_parho(), galti=galti, reminder=""
    )


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


@web.route("/reminder", methods=["POST"])
def reminder():
    sawal = (
        "Is appointment ke liye patient ko ek chhota, shaista reminder "
        "message likho. Patient: " + request.form["naam"]
        + ", Doctor: " + request.form["doctor"]
        + ", Tareekh: " + request.form["tareekh"]
        + ", Waqt: " + request.form["waqt"]
    )
    try:
        jawab = client.chat.completions.create(
            messages=[
                {"role": "system", "content": "Tum ek clinic ke madadgaar ho. Hamesha Roman Urdu mein jawab do, Hindi mein nahi. Urdu lafz istemal karo (meharbani, shukriya). Sirf wohi maloomat likho jo di gayi hai, apni taraf se waqt ya koi aur cheez mat jodo. Sirf message likho, medical salah mat do."},
                {"role": "user", "content": sawal},
            ],
            model="openai/gpt-oss-20b",
        )
        message = jawab.choices[0].message.content
    except Exception:
        message = "AI se jawab nahi mila, thori der baad koshish karo"

    return render_template_string(
        PAGE, appointments=appointments_parho(), galti="", reminder=message
    )


web.run(debug=True)