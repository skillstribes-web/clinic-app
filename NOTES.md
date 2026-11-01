\# Clinic Appointment App



A small website for managing clinic appointments, built with Python, Flask and SQLite.

It also uses a free AI (Groq) to write patient messages.

This is my first real project while learning AI app development.



\## Features

\- Login with a password (shared password, stored on my computer)

\- Add an appointment: name, age, gender, phone, doctor, date, time (AM/PM)

\- A patient is saved only once. If the same name and phone book again, the app reuses that patient.

\- Checks: no empty fields, valid date and time, valid age, valid phone

\- Double-booking protection: the same doctor cannot have two appointments at the same date and time (also catches a date typed like 5-11-2026)

\- Reschedule an appointment (new date and time, same checks)

\- Delete an appointment (with a confirmation popup). The patient is kept.

\- Search by name, doctor, date or phone (not case sensitive), with "Showing X of Y" and a Clear link

\- Appointments are always shown sorted by date and time (earliest first), sorted by SQL

\- "Today's appointments" section at the top of the page (only today's appointments, in time order)

\- AI reminder message for a patient

\- AI "doctor unavailable" message for a patient

\- WhatsApp link: opens a chat with the patient with the message already typed (I press send myself)

\- Automatic backup of the database every time I start the server



\## How to run

1\. Open Git Bash and go to the folder: cd Desktop/clinic-app

2\. Start the server with a backup first: python backup.py \&\& python web.py

&#x20;  (\&\& means: run the second command only if the first one worked)

3\. Open http://127.0.0.1:5000 in the browser and log in

4\. Stop the server with Ctrl + C



\## Settings on my computer (environment variables)

\- GROQ\_API\_KEY: my Groq key (never put it in the code or on GitHub)

\- CLINIC\_PASSWORD: the login password

\- They are set with setx, then a NEW Git Bash window must be opened



\## Files

\- web.py: the website (main file)

\- clinic.db: the SQLite database (never pushed to GitHub, \*.db is in .gitignore)

\- backup.py: copies clinic.db into the backups folder with the date and time in the name, and keeps only the newest 10 copies

\- backups/: the backup copies (never pushed to GitHub, they are .db files)

\- migrate.py: one-time script that copied the old appointments.txt data into clinic.db (it stops if the database already has data)

\- migrate\_dates.py: one-time script that changed old dates and times to the new format (safe to run again)

\- migrate\_patients.py: one-time script that split the old single appointments table into patients + appointments (safe to run again, it says "Already migrated"; it rolls back everything if something goes wrong)

\- db\_practice.py: my SQLite practice file (uses practice.db)

\- appointments.txt: the OLD data file, not used by web.py anymore. Kept only as an old backup. Never pushed (in .gitignore).

\- app.py: the old terminal version (old 4-field format, not used anymore)

\- .gitignore: lists files Git must ignore (appointments.txt, purani.txt, \*.db)

\- NOTES.md: this file



\## Database (SQLite)

\- SQLite is built into Python (import sqlite3), nothing to install.

\- Table patients: id, name, age, gender, phone

\- Table appointments: id, patient\_id (the id of a patient), doctor, date, time

\- Table appointments\_old: the old single table, kept inside clinic.db as an extra safety copy. web.py does not use it. It can be deleted later.

\- A patient is the same person when the name (ignoring capital letters) and the phone are the same.

\- When the same patient books again, the age and gender are updated to the newest values.

\- JOIN connects the tables: appointments JOIN patients ON appointments.patient\_id = patients.id

&#x20; Use table.column (for example appointments.date) because both tables have an id column.

\- Benefit: patient details are saved once. Changing a phone number in one place changes it for all that patient's appointments.

\- In the database the date is saved as 2026-11-05 (YYYY-MM-DD) and the time as 24 hours like 09:00 or 15:30.

&#x20; This way SQL can sort them correctly with ORDER BY date, time.

\- On the screen I still see 05-11-2026 and 9:00 AM. web.py converts both ways:

&#x20; date\_to\_db / time\_to\_db (when saving) and date\_to\_show / time\_to\_show (when showing).

\- Rule: the database keeps the machine-friendly form, the screen shows the human-friendly form.

\- web.py creates the tables itself if they do not exist (init\_db).

\- Reschedule and Delete work with the appointment id, so they always change exactly one row.

\- Commas in names are allowed now (the old text file did not allow them).

\- Always use ? placeholders in SQL, never join user text into the SQL string.

\- Always put WHERE in UPDATE and DELETE, otherwise ALL rows change or disappear.

\- After INSERT, UPDATE or DELETE call conn.commit(), otherwise the change is lost.

\- For a big change: 1) make a backup (python backup.py), 2) write a migration script that checks its own work and rolls back on error, 3) change the code.



\## Backup

\- Run python backup.py (or start the server with python backup.py \&\& python web.py).

\- It uses SQLite's own backup function, so it is safe even while the server is running.

\- Backups are saved like backups/clinic-2026-11-01\_07-26-08.db (date and time in the name).

\- Only the newest 10 backups are kept, older ones are deleted automatically (KEEP = 10 in backup.py).

\- If I am in the wrong folder it says: clinic.db not found. Are you inside the clinic-app folder?

\- To restore: close the server, rename the current clinic.db (for example to clinic-broken.db), copy a backup file to clinic.db, start the server again.

\- The backups are on the same laptop. If the laptop breaks they are gone too, so sometimes copy one backup file to a USB drive or another safe place. Do not put them on GitHub (patient data).



\## SQL I learned

\- CREATE TABLE IF NOT EXISTS: make a table

\- INSERT INTO table (columns) VALUES (?, ?): add a row

\- SELECT columns FROM table: read rows

\- WHERE name LIKE ? with "%ar%": search (% means anything)

\- ORDER BY age DESC: sort (DESC big to small, ASC small to big)

\- ORDER BY date, time: sort by date first, then by time

\- UPDATE table SET column = ? WHERE id = ?: change a row

\- DELETE FROM table WHERE id = ?: remove a row

\- JOIN ... ON ...: connect two tables

\- ALTER TABLE ... RENAME TO ...: rename a table

\- BEGIN, commit(), rollback(): do many changes as one, all or nothing



\## AI notes

\- Library: groq, model: openai/gpt-oss-20b

\- The prompt says: reply in English, use only the information given, do not invent details, no medical advice

\- Only name, doctor, date and time are sent to the AI. Age, gender and phone are NEVER sent.

\- Use only fake patient data while testing (free AI tiers may use prompts)



\## Security (important)

\- The login is one shared password. Good for learning, not enough for a real clinic.

\- Before going online I need: HTTPS, a separate account for each user, and stronger password handling.

\- The session secret key is created again every time the server starts, so everyone is logged out after a restart.

\- Patient data (clinic.db, backups, appointments.txt) must never be committed to GitHub. Check git status before git add . (no .db file and no backups folder should be listed).



\## Problems I had and how I fixed them

\- python or pip not found: use python -m pip install ...

\- SyntaxError: a plain sentence was written in the .py file, wrap it in print(...) or remove it

\- IndentationError: lines must start with the same number of spaces

\- TypeError str vs int: wrap input(...) in int(...)

\- FileNotFoundError: use try/except around opening the file

\- ValueError too many values to unpack: a bad line (extra commas) in the old data file

\- Groq 404 model\_not\_found: the model was removed, switched to openai/gpt-oss-20b

\- AI answered in Hindi script: tell the AI the language in the prompt

\- Data files pushed to GitHub by mistake: git rm --cached file, then add the file to .gitignore

\- Browser says site can't be reached: the server was stopped, run the start command again

\- Environment variable not found: open a new Git Bash window after setx

\- Long code got cut when pasted (file ended in the middle of a function): use the Copy button of the code box, then check with wc -l web.py and tail -4 web.py

\- SyntaxError after adding the missing part: two lines were glued together, the file had no new line at the end. Press Enter to split them.

\- python web.py printed nothing and stopped: the file was incomplete (no web.run line at the end)

\- clinic.db showed up in git status: \*.db was missing in .gitignore. Fixed with: echo "\*.db" >> .gitignore (two > signs, one > would erase the file). Check with cat -A .gitignore

\- After the patients migration the old web.py does not work (the table changed). Run the migration and replace web.py in the same session.



\## Git routine

git status

git add .

git commit -m "message"

git push

(Run git status first and check that no .db file and no backups folder is listed.)



\## Next ideas

\- A Patients page: list of patients with how many appointments each has

\- Pick an existing patient from a list when booking

\- Put the app online (HTTPS, better login, separate user accounts)

\- Automatic SMS or WhatsApp (needs a paid service)

\- Delete the appointments\_old table when I am sure everything is fine

\- Translate or retire the old app.py

