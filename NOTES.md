\# Clinic Appointment App



A small website for managing clinic appointments, built with Python and Flask.

It also uses a free AI (Groq) to write patient messages.

This is my first real project while learning AI app development.



\## Features

\- Login with a password (shared password, stored on my computer)

\- Add an appointment: name, age, gender, phone, doctor, date, time (AM/PM)

\- Checks: no empty fields, no commas, valid date and time, valid phone

\- Double-booking protection: the same doctor cannot have two appointments at the same date and time

\- Reschedule an appointment (new date and time, same checks)

\- Delete an appointment (with a confirmation popup)

\- Search by name, doctor, date or phone (not case sensitive), with "Showing X of Y" and a Clear link

\- Appointments are always shown sorted by date and time (earliest first)

\- AI reminder message for a patient

\- AI "doctor unavailable" message for a patient

\- WhatsApp link: opens a chat with the patient with the message already typed (I press send myself)



\## How to run

1\. Open Git Bash and go to the folder: cd Desktop/clinic-app

2\. Start the server: python web.py

3\. Open http://127.0.0.1:5000 in the browser and log in

4\. Stop the server with Ctrl + C



\## Settings on my computer (environment variables)

\- GROQ\_API\_KEY: my Groq key (never put it in the code or on GitHub)

\- CLINIC\_PASSWORD: the login password

\- They are set with setx, then a NEW Git Bash window must be opened



\## Files

\- web.py: the website (main file)

\- app.py: the old terminal version (old 4-field format, not used anymore)

\- appointments.txt: the saved data (never pushed to GitHub, it is in .gitignore)

\- .gitignore: lists files Git must ignore

\- NOTES.md: this file



\## Data format

One appointment per line, 7 fields separated by commas:

name,doctor,date,time,gender,age,phone

Example (fake data): Ali,Dr Khan,05-11-2026,10:30 AM,Male,30,15551234567

Because commas separate the fields, the app does not allow commas in any field.

If the format changes, old lines break, so old test data must be removed.



\## AI notes

\- Library: groq, model: openai/gpt-oss-20b

\- The prompt says: reply in English, use only the information given, do not invent details, no medical advice

\- Only name, doctor, date and time are sent to the AI. Age, gender and phone are NEVER sent.

\- Use only fake patient data while testing (free AI tiers may use prompts)



\## Security (important)

\- The login is one shared password. Good for learning, not enough for a real clinic.

\- Before going online I need: HTTPS, a separate account for each user, and stronger password handling.

\- The session secret key is created again every time the server starts, so everyone is logged out after a restart.

\- Patient data must never be committed to GitHub.



\## Problems I had and how I fixed them

\- python or pip not found: use python -m pip install ...

\- SyntaxError: a plain sentence was written in the .py file, wrap it in print(...) or remove it

\- IndentationError: lines must start with the same number of spaces

\- TypeError str vs int: wrap input(...) in int(...)

\- FileNotFoundError: use try/except around opening the file

\- ValueError too many values to unpack: a bad line (extra commas) in the data file, fixed with checks and cleaning the file

\- Groq 404 model\_not\_found: the model was removed, switched to openai/gpt-oss-20b

\- AI answered in Hindi script: tell the AI the language in the prompt

\- Data files pushed to GitHub by mistake: git rm --cached file, then add the file to .gitignore

\- Browser says site can't be reached: the server was stopped, run python web.py again

\- Environment variable not found: open a new Git Bash window after setx



\## Git routine

git status

git add .

git commit -m "message"

git push



\## Next ideas

\- Show today's appointments separately

\- Put the app online (HTTPS, better login)

\- Automatic SMS or WhatsApp (needs a paid service)

\- Use a real database instead of a text file

\- Translate or retire the old app.py

