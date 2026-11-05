import sqlite3

from werkzeug.security import generate_password_hash

DB_FILE = "clinic.db"

print("Set a new password for an existing user.")
print("TEST VERSION: the password is visible while you type.")
print()

conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()
cur.execute("SELECT id, username FROM users ORDER BY id")
users = cur.fetchall()

if not users:
    print("There are no users yet. Run create_user.py first.")
    conn.close()
    raise SystemExit

print("Users:")
for user in users:
    print("  " + user[1])
print()

username = input("Username to change: ").strip()
cur.execute("SELECT id, username FROM users WHERE username = ?", (username,))
found = cur.fetchone()
if found is None:
    print("Error: no user with that name. Nothing was changed.")
    conn.close()
    raise SystemExit

password = input("New password (at least 8 characters): ")
if len(password) < 8:
    print("Error: the password must be at least 8 characters. Nothing was changed.")
    conn.close()
    raise SystemExit

again = input("Type the new password again: ")
if again != password:
    print("Error: the two passwords are not the same. Nothing was changed.")
    conn.close()
    raise SystemExit

cur.execute(
    "UPDATE users SET password_hash = ? WHERE id = ?",
    (generate_password_hash(password), found[0]),
)
conn.commit()
conn.close()
print("Password changed for: " + found[1])
