import sqlite3

conn = sqlite3.connect("practice.db")
cur = conn.cursor()

cur.execute("DROP TABLE IF EXISTS patients")
cur.execute("CREATE TABLE patients (id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT, age INTEGER)")

cur.execute("INSERT INTO patients (name, age) VALUES (?, ?)", ("Ali", 30))
cur.execute("INSERT INTO patients (name, age) VALUES (?, ?)", ("Sara", 25))
cur.execute("INSERT INTO patients (name, age) VALUES (?, ?)", ("Omar", 40))
conn.commit()

print("1. All patients, oldest first:")
cur.execute("SELECT id, name, age FROM patients ORDER BY age DESC")
print(cur.fetchall())

print("2. Search names containing 'ar':")
cur.execute("SELECT id, name, age FROM patients WHERE name LIKE ?", ("%ar%",))
print(cur.fetchall())

print("3. After update, Ali:")
cur.execute("UPDATE patients SET age = ? WHERE name = ?", (31, "Ali"))
conn.commit()
cur.execute("SELECT id, name, age FROM patients WHERE name = ?", ("Ali",))
print(cur.fetchall())

print("4. After delete, all patients:")
cur.execute("DELETE FROM patients WHERE name = ?", ("Omar",))
conn.commit()
cur.execute("SELECT id, name, age FROM patients")
print(cur.fetchall())

conn.close()