import getpass
import mysql.connector
from werkzeug.security import check_password_hash

mysql_password = getpass.getpass("Enter MySQL root password: ")

db = mysql.connector.connect(
    host="localhost",
    user="root",
    password=mysql_password,
    database="ai_bug_analyzer"
)

cursor = db.cursor()

cursor.execute(
    "SELECT password FROM users WHERE email = %s",
    ("testuser@bugai.local",)
)

row = cursor.fetchone()

if row is None:
    print("User found: False")
else:
    print("User found: True")

    stored_hash = row[0]

    password_match = check_password_hash(
        stored_hash,
        "NewPassword123"
    )

    print("Password match:", password_match)

cursor.close()
db.close()