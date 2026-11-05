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

import web  # makes sure the new columns exist

today = datetime.now(ZoneInfo(CLINIC_TZ)).strftime("%Y-%m-%d")
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

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
print("Demo payments added to " + str(len(appointment_ids)) + " appointments.")
print("Demo diagnosis added to " + str(len(patient_ids)) + " patients.")
