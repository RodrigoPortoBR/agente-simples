from app_models import WebhookPayload
print("Imported WebhookPayload successfully")

try:
    w = WebhookPayload(message="hello", sessionId="123")
    print(f"Created payload: {w}")
except Exception as e:
    print(f"Error creating payload: {e}")
