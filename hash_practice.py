from werkzeug.security import check_password_hash, generate_password_hash

password = "my secret 123"

hash1 = generate_password_hash(password)
hash2 = generate_password_hash(password)

print("1. Hash number one:")
print(hash1)
print("2. Hash number two (same password, different text):")
print(hash2)

print("3. Right password against hash one:", check_password_hash(hash1, "my secret 123"))
print("4. Right password against hash two:", check_password_hash(hash2, "my secret 123"))
print("5. Wrong password against hash one:", check_password_hash(hash1, "my secret 124"))