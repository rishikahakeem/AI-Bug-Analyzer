from services.email_service import send_reset_email

test_email = "hakeemrishika@gmail.com"

fake_token = "test-token-123"

result = send_reset_email(
    test_email,
    fake_token
)

print("Email result:", result)