import os
from datetime import datetime

from groq import Groq

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))


def naya_appointment():
    naam = input("Patient ka naam: ").strip()
    doctor = input("Doctor ka naam: ").strip()
    tareekh = input("Tareekh (aise likho 05-11-2026): ").strip()
    waqt = input("Waqt (jaise 5 baje shaam): ").strip()

    if naam == "" or doctor == "" or tareekh == "" or waqt == "":
        print("Galti: koi bhi cheez khali nahi honi chahiye")
        return

    if "," in naam or "," in doctor or "," in tareekh or "," in waqt:
        print("Galti: comma (,) mat likho")
        return

    try:
        datetime.strptime(tareekh, "%d-%m-%Y")
    except ValueError:
        print("Galti: tareekh aise likho: 05-11-2026")
        return

    with open("appointments.txt", "a") as f:
        f.write(naam + "," + doctor + "," + tareekh + "," + waqt + "\n")
    print("Appointment save ho gayi")


def appointments_dekho():
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                naam, doctor, tareekh, waqt = line.strip().split(",")
                print(naam, "ko", doctor, "se", tareekh, "ko", waqt, "par milna hai")
    except FileNotFoundError:
        print("Abhi koi appointment save nahi hai")


def appointment_dhoondo():
    talash = input("Kis patient ka naam dhoondna hai? ").lower()
    mila = False
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                naam, doctor, tareekh, waqt = line.strip().split(",")
                if talash in naam.lower():
                    print(naam, "ko", doctor, "se", tareekh, "ko", waqt, "par milna hai")
                    mila = True
    except FileNotFoundError:
        print("Abhi koi appointment save nahi hai")
        return
    if not mila:
        print("Is naam ki koi appointment nahi mili")


def appointment_hatao():
    talash = input("Kis patient ki appointment hatani hai? ").lower()
    try:
        with open("appointments.txt", "r") as f:
            lines = f.readlines()
    except FileNotFoundError:
        print("Abhi koi appointment save nahi hai")
        return

    bachi = []
    hati = 0
    for line in lines:
        naam, doctor, tareekh, waqt = line.strip().split(",")
        if talash == naam.lower():
            hati += 1
        else:
            bachi.append(line)

    with open("appointments.txt", "w") as f:
        f.writelines(bachi)

    if hati == 0:
        print("Is naam ki koi appointment nahi mili")
    else:
        print(hati, "appointment hata di gayi")


def reminder_banao():
    talash = input("Kis patient ka reminder banana hai? ").lower()
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                naam, doctor, tareekh, waqt = line.strip().split(",")
                if talash == naam.lower():
                    sawal = (
                        "Is appointment ke liye patient ko ek chhota, shaista "
                        "reminder message likho. Patient: " + naam
                        + ", Doctor: " + doctor + ", Tareekh: " + tareekh
                        + ", Waqt: " + waqt
                    )
                    try:
                        jawab = client.chat.completions.create(
                            messages=[
                                {"role": "system", "content": "Tum ek clinic ke madadgaar ho. Hamesha Roman Urdu mein jawab do, Hindi mein nahi. Urdu lafz istemal karo (meharbani, shukriya). Sirf wohi maloomat likho jo di gayi hai, apni taraf se waqt ya koi aur cheez mat jodo. Sirf message likho, medical salah mat do."},
                                {"role": "user", "content": sawal},
                            ],
                            model="openai/gpt-oss-20b",
                        )
                        print("")
                        print(jawab.choices[0].message.content)
                    except Exception:
                        print("AI se jawab nahi mila, thori der baad koshish karo")
                    return
    except FileNotFoundError:
        print("Abhi koi appointment save nahi hai")
        return
    print("Is naam ki koi appointment nahi mili")


while True:
    print("")
    print("=== Clinic Appointment App ===")
    print("1. Naya appointment")
    print("2. Saari appointments dekho")
    print("3. Patient dhoondo")
    print("4. Appointment hatao")
    print("5. Reminder message banao (AI)")
    print("6. Band karo")
    pasand = input("Apni pasand likho (1/2/3/4/5/6): ")

    if pasand == "1":
        naya_appointment()
    elif pasand == "2":
        appointments_dekho()
    elif pasand == "3":
        appointment_dhoondo()
    elif pasand == "4":
        appointment_hatao()
    elif pasand == "5":
        reminder_banao()
    elif pasand == "6":
        print("Khuda hafiz")
        break
    else:
        print("Galat pasand, dobara koshish karo")