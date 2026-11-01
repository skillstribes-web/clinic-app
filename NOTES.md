\# Clinic Appointment App - Notes



Website for clinic staff (receptionist and doctor) to manage appointments.

Built with Flask + SQLite + Groq AI. Runs in the browser, nothing to install on phones.



\## Files

\- web.py - the whole website (pages, database code, login, AI buttons)

\- create\_user.py - creates a login user (run it on the computer where the app runs)

\- backup.py - copies clinic.db into backups/ with a timestamp, keeps the newest 10

\- migrate\*.py - one-time scripts used to move old data to the new database layout

\- hash\_practice.py, db\_practice.py - practice files, not part of the app

\- app.py - old terminal version (to be deleted later)



\## Private files (never push to GitHub)

\- clinic.db - all clinic data

\- backups/ - database copies

\- secret.key - signs the login cookies (auto-created on first run)

\- These are listed in .gitignore. Always run `git status` before `git add .`



\## Database (clinic.db)

\- patients(id, name, age, gender, phone)

\- appointments(id, patient\_id, doctor, date, time)

\- users(id, username, password\_hash)

\- appointments\_old - safety copy of the old table, to be deleted later

\- Dates are saved as YYYY-MM-DD and times as 24h HH:MM; the screen shows DD-MM-YYYY and 9:00 AM

\- A patient is the same person if name (any case) and phone match



\## Features

\- Today's appointments table

\- Add appointment (validation, no double booking for one doctor)

\- Search, reschedule, delete

\- AI reminder message and "doctor unavailable" message with a WhatsApp link

\- Mobile friendly layout (table becomes cards on small screens)



\## Login security

\- Each person has their own username and password

\- Passwords are stored hashed (werkzeug scrypt), never as plain text

\- Same error for wrong username or wrong password

\- 5 wrong attempts locks that user for 10 minutes (kept in memory; a restart resets it)

\- Login lasts 8 hours; cookie is HttpOnly and SameSite=Lax

\- Secure cookie is turned on with CLINIC\_HTTPS=1 (needed once the site uses HTTPS)

\- CSRF token on every POST form

\- Security headers: no-store, X-Frame-Options, nosniff



\## Environment variables

\- GROQ\_API\_KEY - key for the AI

\- CLINIC\_SECRET\_KEY - optional; if not set, secret.key file is used

\- CLINIC\_HTTPS - set to 1 when the site runs on HTTPS



\## How to run

1\. cd Desktop/clinic-app

2\. python create\_user.py (first time only, to make a user)

3\. python backup.py \&\& python web.py

4\. Open http://127.0.0.1:5000



\## AI privacy

\- Only name, doctor, date, time go to the AI

\- Age, gender, phone are never sent

\- Use only fake patient data while testing



\## Roadmap to pilot

1\. Mobile friendly pages - DONE

2\. Stronger login (users, hashing, CSRF, lockout) - DONE

3\. Time zone fix (today = clinic's time zone, not server time)

4\. Production setup (no debug, waitress/gunicorn, requirements.txt, env settings)

5\. Put online with HTTPS (database file must stay persistent)

6\. Off-site backup and a restore test

7\. Patient data and AI privacy (AI on/off option, check local law, written agreement with doctor)

8\. Pilot: fake data first, then one trusted doctor, collect feedback

9\. Extras: Patients page, doctor list, appointment status, delete appointments\_old and old app.py

