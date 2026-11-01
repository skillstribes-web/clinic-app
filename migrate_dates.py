import os
import sqlite3
from datetime import datetime

if not os.path.exists("clinic.db"):
    print("clinic.db not found. Are you inside the clinic-app folder?")
else:
    conn = sqlite3.connect("clinic.db")
    cur = conn.cursor()

    cur.execute("SELECT id, date, time FROM appointments")
    rows = cur.fetchall()

    changed = 0
    left = 0
    for row_id, date, time in rows:
        new_date = date
        new_time = time
        try:
            new_date = datetime.strptime(date, "%d-%m-%Y").strftime("%Y-%m-%d")
        except ValueError:
            pass
        try:
            new_time = datetime.strptime(time, "%I:%M %p").strftime("%H:%M")
        except ValueError:
            pass
        if new_date != date or new_time != time:
            cur.execute(
                "UPDATE appointments SET date = ?, time = ? WHERE id = ?",
                (new_date, new_time, row_id),
            )
            changed += 1
        else:
            left += 1

    conn.commit()
    print(changed, "rows converted,", left, "rows left as they were")

    print("Now in the database:")
    cur.execute("SELECT id, name, date, time FROM appointments ORDER BY date, time")
    for row in cur.fetchall():
        print(row)

    conn.close()