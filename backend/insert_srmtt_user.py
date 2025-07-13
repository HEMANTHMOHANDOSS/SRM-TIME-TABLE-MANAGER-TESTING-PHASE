# insert_srmtt_user.py
import sqlite3
from werkzeug.security import generate_password_hash

DB_PATH = "timetable.db"
EMAIL = "srmtt@srmist.edu.in"
PASSWORD = "srmtt123"

hashed_password = generate_password_hash(PASSWORD)

conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Optional: Delete if user already exists
cursor.execute("DELETE FROM users WHERE email = ?", (EMAIL,))

cursor.execute("""
    INSERT INTO users (name, email, password_hash, role)
    VALUES (?, ?, ?, ?)
""", ("SRMTT Admin", EMAIL, hashed_password, "main_admin"))

conn.commit()
conn.close()

print(f"✅ User '{EMAIL}' added successfully with password '{PASSWORD}'")
