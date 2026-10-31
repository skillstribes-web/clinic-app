\# Clinic App



\## What it does

A clinic appointment app. There are two versions:

\- Terminal app: app.py (older, in Roman Urdu)

\- Website: web.py (main version, in English)



\## How to run the website

1\. cd Desktop/clinic-app

2\. python web.py

3\. Open http://127.0.0.1:5000 in the browser

4\. Press Ctrl + C in Git Bash to stop the server



\## Features (website)

\- Add an appointment: patient name, age, gender, phone, doctor, date, time (hour, minute, AM/PM dropdowns)

\- Checks: no empty fields, no commas, valid date, valid time, age 0-120, valid phone, no double booking for the same doctor, date and time

\- Table of all appointments

\- Delete button (red) with an "Are you sure?" question

\- Reminder (AI) button: the AI writes a short reminder message

\- Doctor unavailable button: the AI writes a message asking the patient to contact the clinic

\- Open in WhatsApp link: opens WhatsApp with the patient's number and the message already filled in (staff presses Send)

\- Green styled page (CSS)



\## AI

\- Free Groq API, library: groq

\- Key is saved on the laptop as GROQ\_API\_KEY (never written in code or on GitHub)

\- Model: openai/gpt-oss-20b

\- The AI only gets name, doctor, date and time. Age, gender and phone are never sent to the AI.

\- Use only fake patient data while testing



\## Data

\- Saved in appointments.txt, one line per appointment: name,doctor,date,time,gender,age,phone

\- appointments.txt is in .gitignore, so patient data stays off GitHub

\- If the data format changes, old lines stop working, so remove the old test data (rm appointments.txt)



\## Problems we met and how we fixed them

\- FileNotFoundError: use try/except

\- ValueError (too many values): check the input before saving it (no commas, no empty fields)

\- purani.txt went to GitHub: git rm --cached, and write names in .gitignore before git add

\- model\_not\_found: the model name had changed, use a current model name

\- AI replied in Hindi: tell the AI the language in the prompt

\- AI adds details by itself: tell it to use only the information given

\- IndentationError: spaces must line up



\## Next steps

\- Login (password) so not everyone can see the appointments

\- Edit or reschedule an appointment

\- Put the website online

\- Automatic SMS or WhatsApp (needs a paid service)

