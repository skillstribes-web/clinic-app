from flask import Flask, render_template_string

web = Flask(__name__)

PAGE = """
<h1>Clinic Appointment App</h1>
<h2>Saari appointments</h2>
{% if appointments %}
<table border="1" cellpadding="8">
  <tr><th>Patient</th><th>Doctor</th><th>Tareekh</th><th>Waqt</th></tr>
  {% for a in appointments %}
  <tr><td>{{ a[0] }}</td><td>{{ a[1] }}</td><td>{{ a[2] }}</td><td>{{ a[3] }}</td></tr>
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


@web.route("/")
def home():
    return render_template_string(PAGE, appointments=appointments_parho())


web.run(debug=True)