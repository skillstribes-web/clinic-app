import sqlite3

conn = sqlite3.connect("clinic.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    doctor TEXT,
    date TEXT,
    time TEXT,
    gender TEXT,
    age TEXT,
    phone TEXT
)
""")

cur.execute("SELECT COUNT(*) FROM appointments")
already = cur.fetchone()[0]

if already > 0:
    print("The database already has", already, "appointments. Stopping so nothing is added twice.")
else:
    count = 0
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) == 7:
                    cur.execute(
                        "INSERT INTO appointments (name, doctor, date, time, gender, age, phone) VALUES (?, ?, ?, ?, ?, ?, ?)",
                        parts,
                    )
                    count += 1
    except FileNotFoundError:
        print("appointments.txt not found")
    conn.commit()
    print(count, "appointments moved to the database")

print("Now in the database:")
cur.execute("SELECT id, name, doctor, date, time FROM appointments")
for row in cur.fetchall():
    print(row)

conn.close()