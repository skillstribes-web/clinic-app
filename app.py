def naya_appointment():
    naam = input("Patient ka naam: ")
    doctor = input("Doctor ka naam: ")
    waqt = input("Appointment ka waqt (jaise 5 baje): ")
    with open("appointments.txt", "a") as f:
        f.write(naam + "," + doctor + "," + waqt + "\n")
    print("Appointment save ho gayi")


def appointments_dekho():
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                naam, doctor, waqt = line.strip().split(",")
                print(naam, "ko", doctor, "se", waqt, "par milna hai")
    except FileNotFoundError:
        print("Abhi koi appointment save nahi hai")


def appointment_dhoondo():
    talash = input("Kis patient ka naam dhoondna hai? ").lower()
    mila = False
    try:
        with open("appointments.txt", "r") as f:
            for line in f:
                naam, doctor, waqt = line.strip().split(",")
                if talash in naam.lower():
                    print(naam, "ko", doctor, "se", waqt, "par milna hai")
                    mila = True
    except FileNotFoundError:
        print("Abhi koi appointment save nahi hai")
        return
    if not mila:
        print("Is naam ki koi appointment nahi mili")


while True:
    print("")
    print("=== Clinic Appointment App ===")
    print("1. Naya appointment")
    print("2. Saari appointments dekho")
    print("3. Patient dhoondo")
    print("4. Band karo")
    pasand = input("Apni pasand likho (1/2/3/4): ")

    if pasand == "1":
        naya_appointment()
    elif pasand == "2":
        appointments_dekho()
    elif pasand == "3":
        appointment_dhoondo()
    elif pasand == "4":
        print("Khuda hafiz")
        break
    else:
        print("Galat pasand, dobara koshish karo")