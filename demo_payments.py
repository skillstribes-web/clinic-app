import random
import sqlite3
from datetime import datetime
from zoneinfo import ZoneInfo

# FOR THE DEMO APP ONLY. Never run this on a real clinic's copy.
# It adds made-up fees and payments to past demo appointments that have no fee yet,
# and a made-up diagnosis to demo patients that have none, so the Earnings page is not empty.

DB_FILE = "clinic.db"
CLINIC_TZ = "Asia/Karachi"

DIAGNOSES = [
    "Lower back pain",
    "Neck pain, cervical spondylosis",
    "Frozen shoulder (left)",
    "Knee pain, osteoarthritis",
    "Sciatica (right leg)",
    "Post-surgery rehab, knee replacement",
    "Tennis elbow",
    "Ankle sprain",
]
FEES = [1500, 2000, 2000, 2500]
METHODS = ["Cash", "Cash", "Cash", "Easypaisa", "JazzCash"]

answer = input("This adds made-up payments for the DEMO app only. Type DEMO to continue: ")
if answer.strip() != "DEMO":
    print("Nothing was changed.")
    raise SystemExit

today = datetime.now(ZoneInfo(CLINIC_TZ)).strftime("%Y-%m-%d")
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# Make sure the new columns exist (the web app also adds them when it reloads).
cur.execute("PRAGMA table_info(appointments)")
columns = [row[1] for row in cur.fetchall()]
for column, kind in (("fee", "INTEGER"), ("paid", "INTEGER"), ("pay_method", "TEXT"), ("note", "TEXT")):
    if column not in columns:
        cur.execute("ALTER TABLE appointments ADD COLUMN " + column + " " + kind)
cur.execute("PRAGMA table_info(patients)")
if "diagnosis" not in [row[1] for row in cur.fetchall()]:
    cur.execute("ALTER TABLE patients ADD COLUMN diagnosis TEXT")

from datetime import timedelta

# The demo may only have future appointments. Then make some past "Done" visits
# (last 25 days, Sundays skipped) for the demo patients, so there is something to earn.
cur.execute(
    "SELECT COUNT(*) FROM appointments WHERE date <= ? AND COALESCE(status, 'Scheduled') NOT IN ('Cancelled', 'No-show')",
    (today,),
)
made = 0
if cur.fetchone()[0] == 0:
    cur.execute("SELECT id FROM patients ORDER BY id")
    demo_patients = [row[0] for row in cur.fetchall()]
    cur.execute("SELECT name FROM doctors ORDER BY id")
    demo_doctors = [row[0] for row in cur.fetchall()]
    if demo_patients and demo_doctors:
        start = datetime.now(ZoneInfo(CLINIC_TZ)).date()
        slots = ["10:00", "10:45", "11:30", "12:15", "15:00", "15:45", "16:30", "17:15"]
        for back in range(1, 26):
            day = start - timedelta(days=back)
            if day.weekday() == 6:
                continue
            for slot in random.sample(slots, random.randint(2, 5)):
                cur.execute(
                    "INSERT INTO appointments (patient_id, doctor, date, time, status) VALUES (?, ?, ?, ?, 'Done')",
                    (random.choice(demo_patients), random.choice(demo_doctors), day.strftime("%Y-%m-%d"), slot),
                )
                made += 1

cur.execute(
    "SELECT id FROM appointments WHERE fee IS NULL AND date <= ? "
    "AND COALESCE(status, 'Scheduled') NOT IN ('Cancelled', 'No-show')",
    (today,),
)
appointment_ids = [row[0] for row in cur.fetchall()]
for appointment_id in appointment_ids:
    fee = random.choice(FEES)
    paid = fee if random.random() > 0.15 else fee - 500
    cur.execute(
        "UPDATE appointments SET fee = ?, paid = ?, pay_method = ? WHERE id = ?",
        (fee, paid, random.choice(METHODS), appointment_id),
    )

cur.execute("SELECT id FROM patients WHERE diagnosis IS NULL OR diagnosis = ''")
patient_ids = [row[0] for row in cur.fetchall()]
for patient_id in patient_ids:
    cur.execute("UPDATE patients SET diagnosis = ? WHERE id = ?", (random.choice(DIAGNOSES), patient_id))

conn.commit()
conn.close()
if made:
    print("Made " + str(made) + " past demo visits.")
print("Demo payments added to " + str(len(appointment_ids)) + " appointments.")
print("Demo diagnosis added to " + str(len(patient_ids)) + " patients.")
