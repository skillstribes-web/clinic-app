import sqlite3

conn = sqlite3.connect("practice.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS appointments")
cur.execute("DROP TABLE IF EXISTS patients")

cur.execute("CREATE TABLE patients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, phone TEXT)")
cur.execute("CREATE TABLE appointments (id INTEGER PRIMARY KEY AUTOINCREMENT, patient_id INTEGER, doctor TEXT, date TEXT, time TEXT)")

cur.execute("INSERT INTO patients (name, phone) VALUES (?, ?)", ("Ali", "15551230001"))
cur.execute("INSERT INTO patients (name, phone) VALUES (?, ?)", ("Sara", "15551230002"))
cur.execute("INSERT INTO patients (name, phone) VALUES (?, ?)", ("Omar", "15551230003"))

cur.execute("INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)", (1, "Dr Khan", "2026-11-05", "09:00"))
cur.execute("INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)", (1, "Dr Khan", "2026-11-12", "10:30"))
cur.execute("INSERT INTO appointments (patient_id, doctor, date, time) VALUES (?, ?, ?, ?)", (2, "Dr Waseem", "2026-11-05", "11:00"))
conn.commit()

print("1. Plain JOIN (Omar is missing, he has no appointments):")
cur.execute("""
SELECT patients.name, appointments.date
FROM patients
JOIN appointments ON appointments.patient_id = patients.id
ORDER BY patients.name, appointments.date
""")
print(cur.fetchall())

print("2. LEFT JOIN (Omar shows up, his date is None):")
cur.execute("""
SELECT patients.name, appointments.date
FROM patients
LEFT JOIN appointments ON appointments.patient_id = patients.id
ORDER BY patients.name, appointments.date
""")
print(cur.fetchall())

print("3. How many appointments each patient has:")
cur.execute("""
SELECT patients.name, COUNT(appointments.id)
FROM patients
LEFT JOIN appointments ON appointments.patient_id = patients.id
GROUP BY patients.id
ORDER BY patients.name
""")
print(cur.fetchall())

print("4. Patients with no appointments:")
cur.execute("""
SELECT patients.name
FROM patients
LEFT JOIN appointments ON appointments.patient_id = patients.id
WHERE appointments.id IS NULL
""")
print(cur.fetchall())

conn.close()