from database import get_db_connection
import json


def save_analysis(user_id, language, code, result):
    """
    Save a complete code analysis into the analyses table.

    The result is stored as TEXT so the complete History report
    can be retrieved later.
    """

    connection = get_db_connection()

    if connection is None:
        print("ERROR: Could not connect to database.")
        return None

    cursor = None

    try:
        # --------------------------------------------------
        # Make sure result is stored as text
        # --------------------------------------------------

        if result is None:
            result = ""

        elif isinstance(result, (dict, list)):
            result = json.dumps(
                result,
                ensure_ascii=False,
                indent=2
            )

        else:
            result = str(result)

        print("==========================================")
        print("Saving analysis to database...")
        print(f"User ID: {user_id}")
        print(f"Language: {language}")
        print(f"Code length: {len(code)}")
        print(f"Result length: {len(result)}")
        print("==========================================")

        # --------------------------------------------------
        # Create cursor
        # --------------------------------------------------

        cursor = connection.cursor()

        # --------------------------------------------------
        # Insert complete analysis
        # --------------------------------------------------

        query = """
            INSERT INTO analyses
            (
                user_id,
                language,
                code,
                result
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s
            )
        """

        values = (
            user_id,
            language,
            code,
            result
        )

        cursor.execute(
            query,
            values
        )

        connection.commit()

        analysis_id = cursor.lastrowid

        print(
            f"Analysis saved successfully. ID: {analysis_id}"
        )

        return analysis_id

    except Exception as e:

        print(
            "ERROR saving analysis:",
            e
        )

        try:
            connection.rollback()
        except Exception:
            pass

        return None

    finally:

        if cursor is not None:

            try:
                cursor.close()
            except Exception:
                pass

        connection.close()


def get_user_analyses(user_id):
    """
    Get all previous analyses for a user.
    """

    connection = get_db_connection()

    if connection is None:
        print("ERROR: Could not connect to database.")
        return []

    cursor = None

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        query = """
            SELECT
                id,
                user_id,
                language,
                code,
                result,
                created_at
            FROM analyses
            WHERE user_id = %s
            ORDER BY created_at DESC
        """

        cursor.execute(
            query,
            (user_id,)
        )

        analyses = cursor.fetchall()

        # --------------------------------------------------
        # Convert database result into normal Python data
        # --------------------------------------------------

        for analysis in analyses:

            if analysis.get("result") is None:
                analysis["result"] = ""

            else:
                analysis["result"] = str(
                    analysis["result"]
                )

        print(
            f"Fetched {len(analyses)} analyses for user {user_id}."
        )

        return analyses

    except Exception as e:

        print(
            "ERROR fetching analyses:",
            e
        )

        return []

    finally:

        if cursor is not None:

            try:
                cursor.close()
            except Exception:
                pass

        connection.close()