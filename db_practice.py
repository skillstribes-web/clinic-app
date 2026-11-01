import sqlite3

conn = sqlite3.connect("practice.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS appointments")
cur.execute("DROP TABLE IF EXISTS patients")

cur.execute("CREATE TABLE patients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT)")
cur.execute("CREATE TABLE appointments (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, doctor TEXT, date TEXT, time TEXT)")

cur.execute("INSERT INTO patients (name, phone) VALUES (?, ?)", ("Ali", "15551230001"))
cur.execute("INSERT INTO patients (name, phone) VALUES (?, ?)", ("Sara", "15551230002"))

cur.execute("INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)", (1, "Dr Khan", "2026-11-05", "09:00"))
cur.execute("INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)", (1, "Dr Khan", "2026-11-12", "10:30"))
cur.execute("INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)", (2, "Dr Waseem", "2026-11-05", "11:00"))
conn.commit()

print("1. Patients:")
cur.execute("SELECT id, name, phone FROM patients")
print(cur.fetchall())

print("2. Appointments (only a patient number, no names):")
cur.execute("SELECT id, patient_id, doctor, date, time FROM appointments")
print(cur.fetchall())

print("3. Joined, with the patient name and phone:")
cur.execute("""
SELECT appointments.id, patients.name, patients.phone, appointments.doctor, appointments.date, appointments.time
FROM appointments
JOIN patients ON appointments.patient_id = patients.id
ORDER BY appointments.date, appointments.time
""")
for row in cur.fetchall():
    print(row)

print("4. After changing Ali's phone in ONE place:")
cur.execute("UPDATE patients SET phone = ? WHERE name = ?", ("15559990000", "Ali"))
conn.commit()
cur.execute("""
SELECT patients.name, patients.phone, appointments.date
FROM appointments
JOIN patients ON appointments.patient_id = patients.id
ORDER BY appointments.date, appointments.time
""")
for row in cur.fetchall():
    print(row)

conn.close()