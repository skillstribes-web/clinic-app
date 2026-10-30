print("=== Clinic Appointment App ===")
naam = input("Patient ka naam: ")
doctor = input("Doctor ka naam: ")
waqt = input("Appointment ka waqt (jaise 5 baje): ")

print("Appointment pakki:", naam, "ko", doctor, "se", waqt, "par milna hai")

with open("appointments.txt", "a") as f:
    f.write(naam + "," + doctor + "," + waqt + "\n")

print("Appointment file mein save ho gayi")