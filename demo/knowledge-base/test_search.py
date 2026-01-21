
import requests
import json

url = "http://localhost:8000/api/v1/chat/completions"
headers = {
    "Content-Type": "application/json"
}

payload = {
    "query": "中建三局",
    "use_rerank": True
}

try:
    print("Sending request...")
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("Answer:", data.get("answer"))
        print("Sources:", len(data.get("sources", [])))
        for s in data.get("sources", []):
            print(f"- DocID: {s.get('document_id')}, Score: {s.get('score')}")
    else:
        print("Error:", response.text)
except Exception as e:
    print(f"Failed: {e}")
