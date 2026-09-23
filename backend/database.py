
import os

import mysql.connector
from mysql.connector import Error


# =========================================================
# MYSQL DATABASE CONFIGURATION
# =========================================================

DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "database": os.getenv("MYSQL_DATABASE", "ai_bug_analyzer"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
}


# =========================================================
# DATABASE CONNECTION
# =========================================================

def get_db_connection():
    """
    Create and return a MySQL database connection.
    """

    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG["host"],
            user=DB_CONFIG["user"],
            password=DB_CONFIG["password"],
            database=DB_CONFIG["database"],
            port=DB_CONFIG["port"],
        )

        if connection.is_connected():

            # -------------------------------------------------
            # Set MySQL session timezone to IST
            # -------------------------------------------------

            cursor = connection.cursor()

            try:
                cursor.execute("SET time_zone = '+05:30'")
            except Error as timezone_error:
                print("Could not set MySQL timezone:", timezone_error)

            cursor.close()

            print("MySQL database connected successfully.")
            print("Database timezone set to IST (+05:30).")

        return connection

    except Error as e:
        print("MySQL connection error:", e)
        return None
