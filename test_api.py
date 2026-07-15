import requests
import json

url = "http://localhost:8000/api/event/enhance-prompt"
data = {"prompt": "环保抗议"}

try:
    response = requests.post(url, json=data)
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
except Exception as e:
    print(f"Error: {e}")
