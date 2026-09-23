import os
import smtplib
from email.message import EmailMessage

from dotenv import load_dotenv

load_dotenv()


def send_reset_email(to_email, reset_token):

    mail_username = os.getenv("MAIL_USERNAME")
    mail_password = os.getenv("MAIL_PASSWORD")
    frontend_url = os.getenv(
        "FRONTEND_URL",
        "http://localhost:5173"
    )

    if not mail_username or not mail_password:
        print("Email configuration is missing.")
        return False

    reset_link = (
        f"{frontend_url}/reset-password"
        f"?token={reset_token}"
    )

    message = EmailMessage()

    message["Subject"] = "AI Bug Analyzer - Password Reset"
    message["From"] = mail_username
    message["To"] = to_email

    message.set_content(
        f"""
Hello,

We received a request to reset your password
for your AI Software Bug Analyzer account.

Click the link below to create a new password:

{reset_link}

This password reset link will expire in 15 minutes.

If you did not request a password reset,
you can safely ignore this email.

Regards,
AI Software Bug Analyzer
"""
    )

    try:

        with smtplib.SMTP(
            "smtp.gmail.com",
            587
        ) as server:

            server.starttls()

            server.login(
                mail_username,
                mail_password
            )

            server.send_message(message)

        print(
            "Password reset email sent successfully."
        )

        return True

    except Exception as e:

        print(
            "Email sending error:",
            e
        )

        return False