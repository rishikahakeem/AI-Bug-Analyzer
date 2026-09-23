from flask import Blueprint, request, jsonify

from database import get_db_connection

from models.user_model import (
    create_user,
    get_user_by_email
)

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

import secrets
import os
import smtplib

from datetime import datetime, timedelta
from urllib.parse import quote

from email.message import EmailMessage
from dotenv import load_dotenv


# =========================================================
# LOAD ENVIRONMENT VARIABLES
# =========================================================

load_dotenv()


# =========================================================
# BLUEPRINT
# =========================================================

auth_bp = Blueprint("auth", __name__)


# =========================================================
# EMAIL SETTINGS
# =========================================================

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")

FRONTEND_URL = os.getenv(
    "FRONTEND_URL",
    "http://localhost:5173"
)


# =========================================================
# SEND PASSWORD RESET EMAIL
# =========================================================

def send_reset_email(
    recipient_email,
    reset_link
):

    if not MAIL_USERNAME:
        raise ValueError(
            "MAIL_USERNAME is missing in .env"
        )

    if not MAIL_PASSWORD:
        raise ValueError(
            "MAIL_PASSWORD is missing in .env"
        )

    message = EmailMessage()

    message["Subject"] = "Reset Your BugAI Password"
    message["From"] = MAIL_USERNAME
    message["To"] = recipient_email

    # -----------------------------------------------------
    # Plain text version
    # -----------------------------------------------------

    message.set_content(
        f"""
Hello,

We received a request to reset your BugAI password.

Click the link below to create a new password:

{reset_link}

This password reset link is valid for 15 minutes.

If you did not request a password reset, you can safely ignore this email.

Regards,
BugAI
AI Software Bug Analyzer
""".strip()
    )

    # -----------------------------------------------------
    # HTML version
    # -----------------------------------------------------

    html_content = f"""
    <html>
        <body style="
            font-family: Arial, sans-serif;
            background-color: #f7f9fc;
            padding: 30px;
        ">

            <div style="
                max-width: 600px;
                margin: auto;
                background: white;
                padding: 30px;
                border-radius: 10px;
                border: 1px solid #e5e7eb;
            ">

                <h2 style="color: #1f3c5b;">
                    BugAI Password Reset
                </h2>

                <p>
                    Hello,
                </p>

                <p>
                    We received a request to reset your
                    BugAI password.
                </p>

                <p>
                    Click the button below to create a
                    new password:
                </p>

                <p style="margin: 30px 0;">
                    <a
                        href="{reset_link}"
                        style="
                            background-color: #1f3c5b;
                            color: white;
                            padding: 12px 22px;
                            text-decoration: none;
                            border-radius: 6px;
                            display: inline-block;
                            font-weight: 600;
                        "
                    >
                        Reset Password
                    </a>
                </p>

                <p>
                    This password reset link is valid
                    for <strong>15 minutes</strong>.
                </p>

                <p>
                    If you did not request a password
                    reset, you can safely ignore this email.
                </p>

                <hr style="
                    border: none;
                    border-top: 1px solid #e5e7eb;
                    margin: 25px 0;
                ">

                <p style="
                    color: #6b7280;
                    font-size: 13px;
                ">
                    BugAI - AI Software Bug Analyzer
                </p>

            </div>

        </body>
    </html>
    """

    message.add_alternative(
        html_content,
        subtype="html"
    )

    # -----------------------------------------------------
    # Gmail SMTP
    # -----------------------------------------------------

    with smtplib.SMTP(
        "smtp.gmail.com",
        587
    ) as server:

        server.starttls()

        server.login(
            MAIL_USERNAME,
            MAIL_PASSWORD
        )

        server.send_message(message)


# =========================================================
# SIGN UP
# =========================================================

@auth_bp.route(
    "/api/auth/signup",
    methods=["POST"]
)
def signup():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    name = data.get(
        "name",
        ""
    ).strip()

    email = data.get(
        "email",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    ).strip()

    if not name or not email or not password:
        return jsonify({
            "success": False,
            "message": "All fields are required."
        }), 400

    existing_user = get_user_by_email(
        email
    )

    if existing_user:
        return jsonify({
            "success": False,
            "message": "Email already registered."
        }), 409

    # Secure password hashing
    hashed_password = generate_password_hash(
        password
    )

    user_id = create_user(
        name,
        email,
        hashed_password
    )

    if user_id is None:
        return jsonify({
            "success": False,
            "message": "Could not create user."
        }), 500

    return jsonify({
        "success": True,
        "message": "Account created successfully.",
        "user": {
            "id": user_id,
            "name": name,
            "email": email,
            "role": "user"
        }
    }), 201


# =========================================================
# LOGIN
# =========================================================

@auth_bp.route(
    "/api/auth/login",
    methods=["POST"]
)
def login():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    email = data.get(
        "email",
        ""
    ).strip()

    password = data.get(
        "password",
        ""
    ).strip()

    if not email or not password:
        return jsonify({
            "success": False,
            "message":
                "Email and password are required."
        }), 400

    user = get_user_by_email(
        email
    )

    if not user:
        return jsonify({
            "success": False,
            "message":
                "Invalid email or password."
        }), 401

    # Check hashed password
    if not check_password_hash(
        user["password"],
        password
    ):
        return jsonify({
            "success": False,
            "message":
                "Invalid email or password."
        }), 401

    # Get role safely
    role = str(
        user.get(
            "role",
            "user"
        )
    ).strip().lower()

    return jsonify({

        "success": True,

        "message":
            "Login successful.",

        "user": {

            "id":
                user["id"],

            "name":
                user["name"],

            "email":
                user["email"],

            "role":
                role

        }

    }), 200


# =========================================================
# FORGOT PASSWORD
# =========================================================

@auth_bp.route(
    "/api/auth/forgot-password",
    methods=["POST"]
)
def forgot_password():

    data = request.get_json()

    if not data:
        return jsonify({
            "success": False,
            "message": "No data received."
        }), 400

    email = data.get(
        "email",
        ""
    ).strip()

    if not email:
        return jsonify({
            "success": False,
            "message":
                "Email address is required."
        }), 400

    user = get_user_by_email(
        email
    )

    # -----------------------------------------------------
    # SECURITY
    # -----------------------------------------------------

    # Do not reveal whether an account exists.
    if not user:
        return jsonify({

            "success": True,

            "message":
                "If an account exists with this email, "
                "a password reset link has been sent."

        }), 200

    # -----------------------------------------------------
    # GENERATE SECURE TOKEN
    # -----------------------------------------------------

    reset_token = secrets.token_urlsafe(
        32
    )

    # Token valid for 15 minutes
    expiry = datetime.now() + timedelta(
        minutes=15
    )

    connection = get_db_connection()

    if connection is None:
        return jsonify({
            "success": False,
            "message":
                "Could not connect to database."
        }), 500

    try:

        cursor = connection.cursor()

        # -------------------------------------------------
        # SAVE TOKEN
        # -------------------------------------------------

        query = """
            UPDATE users
            SET reset_token = %s,
                reset_token_expiry = %s
            WHERE id = %s
        """

        cursor.execute(
            query,
            (
                reset_token,
                expiry,
                user["id"]
            )
        )

        connection.commit()

        cursor.close()

        # -------------------------------------------------
        # BUILD RESET LINK
        # -------------------------------------------------

        encoded_token = quote(
            reset_token,
            safe=""
        )

        reset_link = (
            f"{FRONTEND_URL}"
            f"/reset-password"
            f"?token={encoded_token}"
        )

        print(
            "Sending password reset email to:",
            email
        )

        # -------------------------------------------------
        # SEND EMAIL
        # -------------------------------------------------

        try:

            send_reset_email(
                email,
                reset_link
            )

        except Exception as email_error:

            print(
                "Email sending error:",
                email_error
            )

            return jsonify({

                "success": False,

                "message":
                    "The reset request was created, "
                    "but the email could not be sent. "
                    "Please check the email configuration."

            }), 500

        # -------------------------------------------------
        # SUCCESS
        # -------------------------------------------------

        return jsonify({

            "success": True,

            "message":
                "A password reset link has been sent "
                "to your email."

        }), 200

    except Exception as e:

        print(
            "Forgot password error:",
            e
        )

        connection.rollback()

        return jsonify({

            "success": False,

            "message":
                "Could not process password reset request."

        }), 500

    finally:

        connection.close()


# =========================================================
# RESET PASSWORD
# =========================================================

@auth_bp.route(
    "/api/auth/reset-password",
    methods=["POST"]
)
def reset_password():

    data = request.get_json()

    if not data:
        return jsonify({

            "success": False,

            "message":
                "No data received."

        }), 400

    token = data.get(
        "token",
        ""
    ).strip()

    new_password = data.get(
        "password",
        ""
    ).strip()

    # -----------------------------------------------------
    # VALIDATION
    # -----------------------------------------------------

    if not token or not new_password:
        return jsonify({

            "success": False,

            "message":
                "Reset token and new password are required."

        }), 400

    if len(new_password) < 6:
        return jsonify({

            "success": False,

            "message":
                "Password must be at least 6 characters."

        }), 400

    connection = get_db_connection()

    if connection is None:
        return jsonify({

            "success": False,

            "message":
                "Could not connect to database."

        }), 500

    try:

        cursor = connection.cursor(
            dictionary=True
        )

        # -------------------------------------------------
        # CHECK TOKEN
        # -------------------------------------------------

        query = """
            SELECT id
            FROM users
            WHERE reset_token = %s
              AND reset_token_expiry > NOW()
        """

        cursor.execute(
            query,
            (token,)
        )

        user = cursor.fetchone()

        if not user:

            cursor.close()

            return jsonify({

                "success": False,

                "message":
                    "Invalid or expired reset token."

            }), 400

        # -------------------------------------------------
        # HASH NEW PASSWORD
        # -------------------------------------------------

        hashed_password = generate_password_hash(
            new_password
        )

        # -------------------------------------------------
        # UPDATE PASSWORD
        # -------------------------------------------------

        update_query = """
            UPDATE users
            SET password = %s,
                reset_token = NULL,
                reset_token_expiry = NULL
            WHERE id = %s
        """

        cursor.execute(
            update_query,
            (
                hashed_password,
                user["id"]
            )
        )

        connection.commit()

        cursor.close()

        return jsonify({

            "success": True,

            "message":
                "Password reset successfully."

        }), 200

    except Exception as e:

        print(
            "Reset password error:",
            e
        )

        connection.rollback()

        return jsonify({

            "success": False,

            "message":
                "Could not reset password."

        }), 500

    finally:

        connection.close()