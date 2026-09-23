from flask import Blueprint, jsonify

from database import get_db_connection


admin_bp = Blueprint("admin", __name__)


@admin_bp.route(
    "/api/admin/dashboard/<int:user_id>",
    methods=["GET"]
)
def get_admin_dashboard(user_id):

    connection = None
    cursor = None

    try:
        connection = get_db_connection()

        cursor = connection.cursor(dictionary=True)

        # =====================================================
        # CHECK USER
        # =====================================================

        cursor.execute(
            """
            SELECT id, name, email, role
            FROM users
            WHERE id = %s
            """,
            (user_id,)
        )

        admin_user = cursor.fetchone()

        if not admin_user:
            return jsonify({
                "success": False,
                "message": "User not found."
            }), 404

        # =====================================================
        # CHECK ADMIN
        # =====================================================

        if admin_user["role"] != "admin":
            return jsonify({
                "success": False,
                "message": "Admin access required."
            }), 403

        # =====================================================
        # TOTAL USERS
        # =====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_users
            FROM users
            """
        )

        total_users = cursor.fetchone()["total_users"]

        # =====================================================
        # TOTAL ANALYSES
        # =====================================================

        cursor.execute(
            """
            SELECT COUNT(*) AS total_analyses
            FROM analyses
            """
        )

        total_analyses = cursor.fetchone()["total_analyses"]

        # =====================================================
        # ANALYSES BY LANGUAGE
        # =====================================================

        cursor.execute(
            """
            SELECT
                language,
                COUNT(*) AS count
            FROM analyses
            GROUP BY language
            ORDER BY count DESC
            """
        )

        language_rows = cursor.fetchall()

        language_stats = [
            {
                "language": row["language"],
                "count": int(row["count"])
            }
            for row in language_rows
        ]

        # =====================================================
        # RECENT USERS
        # =====================================================

        cursor.execute(
            """
            SELECT
                id,
                name,
                email,
                role,
                created_at
            FROM users
            ORDER BY created_at DESC
            LIMIT 10
            """
        )

        recent_users = cursor.fetchall()

        for user in recent_users:
            if user.get("created_at"):
                user["created_at"] = str(
                    user["created_at"]
                )

        # =====================================================
        # RECENT ANALYSES
        # =====================================================

        cursor.execute(
            """
            SELECT
                a.id,
                a.user_id,
                a.language,
                a.created_at,
                u.name AS user_name,
                u.email AS user_email
            FROM analyses a
            LEFT JOIN users u
                ON a.user_id = u.id
            ORDER BY a.created_at DESC
            LIMIT 10
            """
        )

        recent_analyses = cursor.fetchall()

        for analysis in recent_analyses:
            if analysis.get("created_at"):
                analysis["created_at"] = str(
                    analysis["created_at"]
                )

        # =====================================================
        # RESPONSE
        # =====================================================

        return jsonify({
            "success": True,

            "admin": {
                "id": admin_user["id"],
                "name": admin_user["name"],
                "email": admin_user["email"],
                "role": admin_user["role"]
            },

            "stats": {
                "total_users": int(total_users),
                "total_analyses": int(total_analyses)
            },

            "language_stats": language_stats,
            "recent_users": recent_users,
            "recent_analyses": recent_analyses
        }), 200

    except Exception as error:

        print(
            "ADMIN DASHBOARD ERROR:",
            error
        )

        return jsonify({
            "success": False,
            "message": f"Admin dashboard failed: {error}"
        }), 500

    finally:

        if cursor:
            cursor.close()

        if connection:
            connection.close()