# Clinic Appointment App - Notes

Website for clinic staff (receptionist and doctor) to manage appointments.
Built with Flask + SQLite (+ optional Groq AI). Runs in the browser, nothing to install on phones.

Test site (free hosting, fake data only): https://skillstribes.pythonanywhere.com

## Files
- web.py - the whole website (pages, database code, login, messages, theme)
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
- appointments(id, patient_id, doctor, date, time, status)
- doctors(id, name) - the list used by the dropdown
- users(id, username, password_hash)
- appointments_old - safety copy of the old table (laptop only), to be deleted later
- Dates are saved as YYYY-MM-DD and times as 24h HH:MM; the screen shows DD-MM-YYYY and 9:00 AM
- A patient is the same person if name (any case) and phone match
- status is Scheduled, Done, No-show or Cancelled (old rows count as Scheduled)
- New columns and tables are added automatically when the app starts (init_db)
- Doctors are seeded from existing appointments the first time the doctors table is created
- The laptop and the online server have separate databases

## Features
- Today's appointments table (uses the clinic's time zone)
- Add appointment: doctor is chosen from a dropdown; validation; no double booking for one doctor
- A Cancelled appointment frees its time slot again
- Status per appointment (Set status button)
- Search, reschedule, delete (the page stays where it was after Delete and Set status)
- Patients page: every patient with the number of appointments and the last appointment
- Doctors page: add a doctor; a doctor with appointments cannot be removed
- Reminder and Doctor unavailable messages with an "Open in WhatsApp" link
- "Dr." is added to the doctor's name in messages if not already written
- Clinic name on the pages and in the browser tab (CLINIC_NAME)
- Black and gold theme; all colours are in THEME_CSS in web.py
- Mobile friendly layout (table becomes cards on small screens)

## Login security
- Each person has their own username and password (name them by role or person, e.g. reception, dr.ahmed)
- Passwords are stored hashed (werkzeug scrypt), never as plain text
- Same error for wrong username or wrong password
- 5 wrong attempts locks that user for 10 minutes (kept in memory; a restart resets it)
- Login lasts 8 hours; cookie is HttpOnly and SameSite=Lax
- Secure cookie is turned on with CLINIC_HTTPS=1 (set in the server's WSGI file)
- CSRF token on every POST form
- Security headers: no-store, X-Frame-Options, nosniff
- Any logged-in user can add doctors (no roles yet)

## Settings (environment variables)
- CLINIC_NAME - name shown on the pages, default "Clinic Appointment App"
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
- To try a clinic name: export CLINIC_NAME="Al-Shifa Clinic, Sahiwal" first
- To test AI on the laptop: export CLINIC_AI=1 first (and have GROQ_API_KEY set)
- Copying big files: open notepad web.py, Ctrl+A, Delete, paste, Ctrl+S, then check wc -l web.py and tail -4 web.py

## Online hosting (PythonAnywhere, free Beginner plan)
- Account: skillstribes. Code is in /home/skillstribes/clinic-app (cloned from GitHub)
- Virtualenv: /home/skillstribes/.virtualenvs/clinicenv (Python 3.13); in a new console run: workon clinicenv
- Web app is "Manual configuration"; the WSGI file sets the folder, CLINIC_HTTPS=1 and
  imports the app with: from web import web as application
- To set the clinic name online: add os.environ["CLINIC_NAME"] = "..." to the WSGI file, then Reload
- Free plan limits: outbound internet is limited to a whitelist (so Groq AI cannot work),
  no scheduled tasks, no custom domain. The $10/month plan removes these limits
- The free site may need a "keep alive" button click on the Web tab every few months
- Three different logins: PythonAnywhere account, online app users, laptop test users. Passwords are separate

## How to update the online site
1. On the laptop: git status, git add ., git commit, git push
2. On PythonAnywhere: Consoles > Bash, then: python backup.py and then git pull
3. Web tab > green Reload button (database changes happen at Reload)
4. Open the site, press Ctrl+F5 and check it

## Setting up a new clinic (one clinic per server for now)
1. Put the app on its own server/folder so it has its own empty clinic.db
2. Create the clinic's users with create_user.py (reception, doctor)
3. Set CLINIC_NAME to the clinic's name
4. Open the Doctors page and add the clinic's doctors, then start adding appointments
- Do not share one server between two clinics: they would see each other's data

## Backup and restore
- On the server: Bash console, python backup.py (copy goes to backups/)
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
9. Extras: Patients page, appointment status, doctor list, theme, clinic name - DONE
   Left: delete old app.py and the appointments_old table
- Before a real pilot: clear the fake data on the server, set the clinic name, create the clinic's users
- Later: paid plan ($10/month) for AI, daily automatic backups and a custom domain;
  roles (reception vs doctor); one server for many clinics