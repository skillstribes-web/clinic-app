import os
import sqlite3
from datetime import datetime

KEEP = 10

if not os.path.exists("clinic.db"):
    print("clinic.db not found. Are you inside the clinic-app folder?")
else:
    os.makedirs("backups", exist_ok=True)

    name = "backups/clinic-" + datetime.now().strftime("%Y-%m-%d_%H-%M-%S") + ".db"

    source = sqlite3.connect("clinic.db")
    target = sqlite3.connect(name)
    source.backup(target)
    target.close()
    source.close()

    print("Backup saved:", name)

    files = sorted(f for f in os.listdir("backups") if f.startswith("clinic-") and f.endswith(".db"))
    for old in files[:-KEEP]:
        os.remove("backups/" + old)
        print("Removed old backup:", old)