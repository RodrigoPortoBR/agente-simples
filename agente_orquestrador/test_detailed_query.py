import httpx
import json

# Test database query with detailed output
response = httpx.post(
    'http://127.0.0.1:8000/webhook/chat',
    json={
        'message': 'Qual a receita do cluster premium?',
        'sessionId': 'test789'
    },
    timeout=60
)

print(f'Status: {response.status_code}')
data = response.json()
print(f'Success: {data.get("success")}')
print(f'\nFull Response:')
print(json.dumps(data, indent=2, ensure_ascii=False))
