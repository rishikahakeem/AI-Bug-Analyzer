from database import get_db_connection


# =========================================================
# CREATE USER
# =========================================================

def create_user(name, email, password):

    connection = get_db_connection()

    if connection is None:
        return None

    try:

        cursor = connection.cursor()

        query = """
            INSERT INTO users
            (name, email, password)
            VALUES (%s, %s, %s)
        """

        values = (
            name,
            email,
            password
        )

        cursor.execute(query, values)

        connection.commit()

        user_id = cursor.lastrowid

        cursor.close()

        return user_id

    except Exception as e:

        print("Error creating user:", e)

        connection.rollback()

        return None

    finally:

        connection.close()


# =========================================================
# GET USER BY EMAIL
# =========================================================

def get_user_by_email(email):

    connection = get_db_connection()

    if connection is None:
        return None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        query = """
            SELECT
                id,
                name,
                email,
                password,
                role
            FROM users
            WHERE email = %s
        """

        cursor.execute(
            query,
            (email,)
        )

        user = cursor.fetchone()

        cursor.close()

        return user

    except Exception as e:

        print(
            "Error finding user:",
            e
        )

        return None

    finally:

        connection.close()