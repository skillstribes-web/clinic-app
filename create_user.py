import sqlite3

from werkzeug.security import generate_password_hash

conn = sqlite3.connect("clinic.db")
cur = conn.cursor()

cur.execute("""
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE COLLATE NOCASE,
    password_hash TEXT
)
""")

print("TEST VERSION: the password is visible while you type. Use only test passwords.")
username = input("New username (letters and numbers, no spaces): ").strip()
if username == "" or " " in username or "," in username:
    print("Not saved: the username cannot be empty and cannot have spaces or commas.")
else:
    password = input("Password (at least 8 characters): ").strip()
    again = input("Type the password again: ").strip()
    if password != again:
        print("Not saved: the two passwords are different.")
        print("First one has", len(password), "characters, second one has", len(again), "characters.")
    elif len(password) < 8:
        print("Not saved: the password must have at least 8 characters.")
    else:
        password_hash = generate_password_hash(password)
        cur.execute("SELECT id FROM users WHERE username = ?", (username,))
        found = cur.fetchone()
        if found is None:
            cur.execute(
                "INSERT INTO users (username, password_hash) VALUES (?, ?)",
                (username, password_hash),
            )
            conn.commit()
            print("User created:", username)
        else:
            answer = input("This user already exists. Change the password? (yes/no): ").strip().lower()
            if answer == "yes":
                cur.execute(
                    "UPDATE users SET password_hash = ? WHERE id = ?",
                    (password_hash, found[0]),
                )
                conn.commit()
                print("Password changed for:", username)
            else:
                print("Nothing was changed.")

print("All users now:")
cur.execute("SELECT id, username FROM users ORDER BY id")
for row in cur.fetchall():
    print(row)

conn.close()