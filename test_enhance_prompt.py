import requests
import json

url = "http://localhost:8000/api/event/enhance-prompt"
payload = {
    "prompt": "AI 技术发展"
}

try:
    response = requests.post(url, json=payload, timeout=30)
    print(f"Status Code: {response.status_code}")
    print(f"Response JSON:")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
