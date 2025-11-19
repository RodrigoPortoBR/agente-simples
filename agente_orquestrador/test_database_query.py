import httpx
import json

# Test database query
response = httpx.post(
    'http://127.0.0.1:8000/webhook/chat',
    json={
        'message': 'Qual a receita do cluster premium?',
        'sessionId': 'test456'
    },
    timeout=60
)

print(f'Status: {response.status_code}')
data = response.json()
print(f'Success: {data.get("success")}')
print(f'\nResponse:\n{data.get("response")}')
print(f'\nMetadata: {json.dumps(data.get("metadata", {}), indent=2)}')
