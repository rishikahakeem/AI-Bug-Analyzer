
from flask import Blueprint, jsonify
from datetime import datetime

from models.analysis_model import get_user_analyses
from database import get_db_connection


# =========================================================
# HISTORY BLUEPRINT
# =========================================================

history_bp = Blueprint(
    "history",
    __name__
)


# =========================================================
# GET USER HISTORY
# =========================================================

@history_bp.route(
    "/api/history/<int:user_id>",
    methods=["GET"]
)
def get_history(user_id):

    try:

        analyses = get_user_analyses(user_id)

        # =================================================
        # FIX CREATED_AT TIMESTAMP
        # =================================================
        #
        # MySQL returns created_at as a Python datetime.
        #
        # If Flask receives that datetime directly, Flask
        # converts it to:
        #
        # Mon, 21 Sep 2026 22:22:07 GMT
        #
        # The browser then interprets GMT and converts it
        # to Indian time, causing the unwanted +5:30 shift.
        #
        # We therefore convert the datetime to a plain
        # MySQL-style string before jsonify().
        # =================================================

        for analysis in analyses:

            created_at = analysis.get("created_at")

            if isinstance(created_at, datetime):

                analysis["created_at"] = created_at.strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

        return jsonify({
            "success": True,
            "analyses": analyses
        }), 200

    except Exception as e:

        print(
            "History error:",
            e
        )

        return jsonify({
            "success": False,
            "message": "Could not fetch analysis history."
        }), 500


# =========================================================
# DELETE ONE HISTORY ITEM
# =========================================================

@history_bp.route(
    "/api/history/<int:analysis_id>",
    methods=["DELETE"]
)
def delete_history(analysis_id):

    connection = get_db_connection()

    if connection is None:

        return jsonify({
            "success": False,
            "message": "Could not connect to database."
        }), 500

    try:

        cursor = connection.cursor()

        query = """
            DELETE FROM analyses
            WHERE id = %s
        """

        cursor.execute(
            query,
            (analysis_id,)
        )

        # Check whether a record was actually deleted
        if cursor.rowcount == 0:

            cursor.close()

            return jsonify({
                "success": False,
                "message": "Analysis not found."
            }), 404

        connection.commit()

        cursor.close()

        return jsonify({
            "success": True,
            "message": "Analysis deleted successfully."
        }), 200

    except Exception as e:

        print(
            "Delete history error:",
            e
        )

        connection.rollback()

        return jsonify({
            "success": False,
            "message": "Could not delete analysis."
        }), 500

    finally:

        connection.close()
