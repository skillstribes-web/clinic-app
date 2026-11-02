# seed_demo.py - puts NAMELESS demo data and a "demo" login into clinic.db.
# Every patient is made up and has "(Demo)" in the name. Run it only on the demo server.
import sys
import types
from datetime import timedelta
from werkzeug.security import generate_password_hash

# The console may not have the "groq" package (the website has it, the console does not).
# This script never uses the AI, so a harmless empty stand-in is enough.
try:
    import groq  # noqa: F401
except ImportError:
    fake = types.ModuleType("groq")
    fake.Groq = object
    sys.modules["groq"] = fake

import web

DEMO_USER = "demo"
DEMO_PASSWORD = sys.argv[1] if len(sys.argv) > 1 else ""
if len(DEMO_PASSWORD) < 8:
    print("Usage: python seed_demo.py YOUR_DEMO_PASSWORD   (at least 8 characters)")
    sys.exit(1)

DOCTORS = ["Dr. Demo A", "Dr. Demo B"]
# name, gender, age, phone, doctor, days (sessions), start offset in working days from today, times
PATIENTS = [
    ("Ahmed Khan (Demo)",   "Male",   45, "03000000001", DOCTORS[0], 10, -4, ["3:00 PM"]),
    ("Sara Bibi (Demo)",    "Female", 38, "03000000002", DOCTORS[0], 42, -9, ["3:30 PM"]),
    ("Bilal Raza (Demo)",   "Male",   29, "03000000003", DOCTORS[1], 14, -3, ["4:00 PM"]),
    ("Nadia Malik (Demo)",  "Female", 52, "03000000004", DOCTORS[1], 10, -2, ["4:30 PM"]),
    ("Usman Ali (Demo)",    "Male",   33, "03000000005", DOCTORS[0], 21, -6, ["4:00 PM", "5:00 PM"]),
    ("Hina Tariq (Demo)",   "Female", 41, "03000000006", DOCTORS[1], 10,  0, ["5:00 PM"]),
]


def working_days(start, count):
    out = []
    day = start
    while len(out) < count:
        if day.weekday() != 6:
            out.append(day)
        day += timedelta(days=1)
    return out


def back_working_days(today, n):
    day = today
    left = n
    while left > 0:
        day -= timedelta(days=1)
        if day.weekday() != 6:
            left -= 1
    return day


web.init_db()
conn = web.connect()
cur = conn.cursor()
today = web.clinic_now().date()

cur.execute("INSERT OR REPLACE INTO users (id, username, password_hash) VALUES "
            "((SELECT id FROM users WHERE username = ?), ?, ?)",
            (DEMO_USER, DEMO_USER, generate_password_hash(DEMO_PASSWORD)))
for d in DOCTORS:
    cur.execute("INSERT OR IGNORE INTO doctors (name) VALUES (?)", (d,))

# remove an older demo set, so the script can be run again safely
cur.execute("SELECT id FROM patients WHERE name LIKE '%(Demo)'")
old = [r[0] for r in cur.fetchall()]
for pid in old:
    cur.execute("DELETE FROM appointments WHERE patient_id = ?", (pid,))
    cur.execute("DELETE FROM patients WHERE id = ?", (pid,))

cur.execute("SELECT COALESCE(MAX(course_id), 0) FROM appointments")
course_id = cur.fetchone()[0]
count = 0
for name, gender, age, phone, doctor, days, offset, times in PATIENTS:
    pid = web.find_or_add_patient(cur, name, age, gender, phone)
    course_id += 1
    if offset < 0:
        start = back_working_days(today, -offset)
    else:
        start = today if today.weekday() != 6 else today + timedelta(days=1)
    for day_no, day in enumerate(working_days(start, days), start=1):
        for t in times:
            if day < today:
                # a few sessions in the past: most came, one did not come
                status = "No-show" if (name.startswith("Bilal") and day_no == 2) else "Done"
            else:
                status = "Scheduled"
            cur.execute(
                "INSERT INTO appointments (patient_id, doctor, date, time, status, course_id, day_no, days_total) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (pid, doctor, day.strftime("%Y-%m-%d"), web.time_to_db(t), status, course_id, day_no, days))
            count += 1
conn.commit()
conn.close()
print("Done. Demo login:  username = demo   password = (the one you typed)")
print("Demo sessions added:", count)
