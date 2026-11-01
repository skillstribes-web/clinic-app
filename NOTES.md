# Clinic Appointment App - Notes

Website for clinic staff (receptionist and doctor) to manage appointments.
Built with Flask + SQLite (+ optional Groq AI). Runs in the browser, nothing to install on phones.

Live (free test site): https://skillstribes.pythonanywhere.com

## Files
- web.py - the whole website (pages, database code, login, messages)
- serve.py - starts the site with waitress (used on my laptop for a production-like run)
- requirements.txt - the packages the app needs (Flask, groq, waitress, tzdata)
- create_user.py - creates a login user (run it where the app runs)
- backup.py - copies clinic.db into backups/ with a timestamp, keeps the newest 10
- migrate*.py - one-time scripts used to move old data to the new database layout
- hash_practice.py, db_practice.py - practice files, not part of the app
- app.py - old terminal version (to be deleted later)

## Private files (never push to GitHub)
- clinic.db - all clinic data
- backups/ - database copies
- secret.key - signs the login cookies (auto-created on first run)
- __pycache__/ - Python's compiled copies
- These are listed in .gitignore. Always run `git status` before `git add .`

## Database (clinic.db)
- patients(id, name, age, gender, phone)
- appointments(id, patient_id, doctor, date, time)
- users(id, username, password_hash)
- appointments_old - safety copy of the old table, to be deleted later
- Dates are saved as YYYY-MM-DD and times as 24h HH:MM; the screen shows DD-MM-YYYY and 9:00 AM
- A patient is the same person if name (any case) and phone match
- The laptop and the online server have separate databases

## Features
- Today's appointments table (uses the clinic's time zone)
- Add appointment (validation, no double booking for one doctor)
- Search, reschedule, delete
- Reminder and Doctor unavailable messages with an "Open in WhatsApp" link
- "Dr." is added to the doctor's name in messages if not already written
- Mobile friendly layout (table becomes cards on small screens)

## Login security
- Each person has their own username and password
- Passwords are stored hashed (werkzeug scrypt), never as plain text
- Same error for wrong username or wrong password
- 5 wrong attempts locks that user for 10 minutes (kept in memory; a restart resets it)
- Login lasts 8 hours; cookie is HttpOnly and SameSite=Lax
- Secure cookie is turned on with CLINIC_HTTPS=1 (set in the server's WSGI file)
- CSRF token on every POST form
- Security headers: no-store, X-Frame-Options, nosniff

## Settings (environment variables)
- CLINIC_TZ - clinic time zone, default Asia/Karachi (all of Pakistan is one zone)
- CLINIC_AI - set to 1 to turn AI on; default is off
- GROQ_API_KEY - key for the AI (only needed when CLINIC_AI=1)
- CLINIC_SECRET_KEY - optional; if not set, the secret.key file is used
- CLINIC_HTTPS - set to 1 when the site runs on HTTPS
- PORT, CLINIC_HOST - used by serve.py (defaults 8000 and 127.0.0.1)

## AI privacy
- AI is OFF by default. When it is off, Reminder and Doctor unavailable use a ready-made text
- When it is ON, the AI gets only the doctor name, date and time
- The patient name is replaced by a [PATIENT] marker before sending and put back afterwards
- Age, gender and phone are never sent
- Use only fake patient data while testing
- Turn AI on for a clinic only after the doctor agrees in writing

## How to run on my laptop
1. cd Desktop/clinic-app
2. python create_user.py (first time only)
3. python backup.py && python serve.py
4. Open http://127.0.0.1:8000
- For development with auto-reload: python web.py (port 5000)
- To test AI on the laptop: export CLINIC_AI=1 first (and have GROQ_API_KEY set)

## Online hosting (PythonAnywhere, free Beginner plan)
- Account: skillstribes. Code is in /home/skillstribes/clinic-app (cloned from GitHub)
- Virtualenv: /home/skillstribes/.virtualenvs/clinicenv (Python 3.13)
- Web app is "Manual configuration"; the WSGI file sets the folder, CLINIC_HTTPS=1 and
  imports the app with: from web import web as application
- Free plan limits: outbound internet is limited to a whitelist (so Groq AI cannot work),
  no scheduled tasks, no custom domain. The $10/month plan removes these limits
- The free site may need a "keep alive" button click on the Web tab every few months

## How to update the online site
1. On the laptop: git add ., git commit, git push
2. On PythonAnywhere: Consoles > Bash, then: cd clinic-app && git pull
3. Web tab > green Reload button
4. Open the site and check it

## Backup and restore
- On the server: Bash console, cd clinic-app && python backup.py (copy goes to backups/)
- Download the newest file from Files > clinic-app > backups to the laptop
  (folder: Desktop/MY CLINIC APP/BACKUP). Do this weekly, or daily during the pilot
- Check a backup: open it with sqlite3 and count the rows in users, patients, appointments (done once, OK)
- Restore: upload the backup to clinic-app as clinic.db, then press Reload
- Backups contain patient data. Never email or share them

## Pilot agreement
- A draft is saved as a doc: "Pilot Agreement - Clinic Appointment App"
- To do: see a local lawyer (stamp paper needed?), show the app to the doctor, fill in names, both sign

## Roadmap
1. Mobile friendly pages - DONE
2. Stronger login (users, hashing, CSRF, lockout) - DONE
3. Time zone fix - DONE
4. Production setup (waitress, requirements.txt, no debug) - DONE
5. Put online with HTTPS (free plan) - DONE
6. Backup and restore test (manual on the free plan) - DONE
7. Patient data and AI privacy (AI switch, name hidden from AI, draft agreement) - DONE; legal check still to do
8. Pilot: fake data first, then one trusted doctor, collect feedback - NEXT (after lawyer and doctor meeting)
9. Extras: Patients page (LEFT JOIN, COUNT, GROUP BY), doctor list, appointment status,
   delete appointments_old and old app.py
- Later: paid plan ($10/month) for AI, daily automatic backups and a custom domain