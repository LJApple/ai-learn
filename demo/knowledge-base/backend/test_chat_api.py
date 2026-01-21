
import requests
import json
import time

def test_chat():
    url = "http://localhost:8000/api/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer test_token"
    }
    data = {
        "query": "中建三局",
        "use_rerank": True
    }
    
    print(f"Sending request to {url}...")
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data)
        end_time = time.time()
        print(f"Status Code: {response.status_code}")
        print(f"Time Taken: {end_time - start_time:.2f}s")
        
        if response.status_code == 200:
            print("Response JSON:")
            print(json.dumps(response.json(), indent=2, ensure_ascii=False))
        else:
            print("Error Response:")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    test_chat()
