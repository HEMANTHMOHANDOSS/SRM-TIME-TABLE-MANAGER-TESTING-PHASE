from werkzeug.security import check_password_hash
import sqlite3

conn = sqlite3.connect("timetable.db")
cursor = conn.cursor()

cursor.execute("SELECT password_hash FROM users WHERE email = ?", ("srmtt@srmist.edu.in",))
row = cursor.fetchone()
conn.close()

if row:
    hash_from_db = row[0]
    input_password = "srmtt123"  # This is the password you typed
    is_valid = check_password_hash(hash_from_db, input_password)
    print(f"✅ Password check: {is_valid}")
else:
    print("❌ User not found.")
