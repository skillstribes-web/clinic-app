def naya_appointment():
    naam = input("Patient ka naam: ")
    doctor = input("Doctor ka naam: ")
    waqt = input("Appointment ka waqt (jaise 5 baje): ")
    with open("appointments.txt", "a") as f:
        f.write(naam + "," + doctor + "," + waqt + "\n")
    print("Appointment save ho gayi")


def appointments_dekho():
    with open("appointments.txt", "r") as f:
        for line in f:
            naam, doctor, waqt = line.strip().split(",")
            print(naam, "ko", doctor, "se", waqt, "par milna hai")


while True:
    print("")
    print("=== Clinic Appointment App ===")
    print("1. Naya appointment")
    print("2. Saari appointments dekho")
    print("3. Band karo")
    pasand = input("Apni pasand likho (1/2/3): ")

    if pasand == "1":
        naya_appointment()
    elif pasand == "2":
        appointments_dekho()
    elif pasand == "3":
        print("Khuda hafiz")
        break
    else:
        print("Galat pasand, dobara koshish karo")