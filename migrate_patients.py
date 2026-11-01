import os
import sqlite3

if not os.path.exists("clinic.db"):
    print("clinic.db not found. Are you inside the clinic-app folder?")
else:
    conn = sqlite3.connect("clinic.db")
    cur = conn.cursor()

    cur.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name = 'appointments_old'")
    if cur.fetchone() is not None:
        print("Already migrated (appointments_old exists). Nothing was changed.")
    else:
        try:
            cur.execute("BEGIN")

            cur.execute("ALTER TABLE appointments RENAME TO appointments_old")

            cur.execute("""
            CREATE TABLE patients (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT,
                age TEXT,
                gender TEXT,
                phone TEXT
            )
            """)

            cur.execute("""
            CREATE TABLE appointments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                patient_id INTEGER,
                doctor TEXT,
                date TEXT,
                time TEXT
            )
            """)

            cur.execute("SELECT id, name, doctor, date, time, gender, age, phone FROM appointments_old ORDER BY id")
            old_rows = cur.fetchall()

            for old_id, name, doctor, date, time, gender, age, phone in old_rows:
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
                    patient_id = cur.lastrowid
                else:
                    patient_id = found[0]
                    cur.execute(
                        "UPDATE patients SET age = ?, gender = ? WHERE id = ?",
                        (age, gender, patient_id),
                    )
                cur.execute(
                    "INSERT INTO appointments (id, patient_id, doctor, date, time) VALUES (?, ?, ?, ?, ?)",
                    (old_id, patient_id, doctor, date, time),
                )

            cur.execute("""
            SELECT COUNT(*)
            FROM appointments_old o
            JOIN appointments a ON a.id = o.id
            JOIN patients p ON p.id = a.patient_id
            WHERE LOWER(p.name) = LOWER(o.name)
              AND p.phone = o.phone
              AND a.doctor = o.doctor
              AND a.date = o.date
              AND a.time = o.time
            """)
            matching = cur.fetchone()[0]

            if matching != len(old_rows):
                raise Exception("Check failed: " + str(matching) + " of " + str(len(old_rows)) + " rows match")

            conn.commit()

            cur.execute("SELECT COUNT(*) FROM patients")
            patient_count = cur.fetchone()[0]
            print(len(old_rows), "appointments moved,", patient_count, "patients created")
            print("Check OK: every appointment matches the old data")

            print("Patients:")
            cur.execute("SELECT id, name, age, gender, phone FROM patients")
            for row in cur.fetchall():
                print(row)

            print("Appointments:")
            cur.execute("""
            SELECT appointments.id, patients.name, appointments.doctor, appointments.date, appointments.time
            FROM appointments
            JOIN patients ON appointments.patient_id = patients.id
            ORDER BY appointments.date, appointments.time
            """)
            for row in cur.fetchall():
                print(row)

        except Exception as error:
            conn.rollback()
            print("Something went wrong, nothing was changed:", error)

    conn.close()