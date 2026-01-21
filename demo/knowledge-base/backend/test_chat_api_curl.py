import requests
import json
import time

def test_chat(threshold=0.7):
    url = "http://localhost:8000/api/v1/chat/completions"
    
    headers = {
        'Accept': 'application/json, text/plain, */*',
        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,zh-TW;q=0.7,lg;q=0.6',
        'Authorization': 'Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIiLCJsb2dpbl91c2VyX2tleSI6IjY5MTJlOTdjLWE1MGEtNDkyNS1hMWE4LWJjNThlNDJkZjNiMSJ9.2OLoaNTUN_6_9Ljx0N9gFJIFN-d2NcRxS7t1dQ_3_ViZqYE77yXV6fumTXdbMW7TBRPwVlbKvb1DiBfdCQhr4Q',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'http://localhost:3000',
        'Pragma': 'no-cache',
        'Referer': 'http://localhost:3000/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Google Chrome";v="143", "Chromium";v="143", "Not A(Brand";v="24"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"'
    }

    data = {
        "query": "中建三局\n\n",
        "conversation_id": "82364dfc-950d-4a57-9012-0ea5870d7272",
        "top_k": 10,
        "score_threshold": threshold,
        "use_rerank": True
    }
    
    print(f"\nSending request to {url} with threshold {threshold}...")
    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data)
        end_time = time.time()
        print(f"Status Code: {response.status_code}")
        print(f"Time Taken: {end_time - start_time:.2f}s")
        
        if response.status_code == 200:
            res_json = response.json()
            print("Response JSON:")
            print(json.dumps(res_json, indent=2, ensure_ascii=False))
            
            sources = res_json.get("sources", [])
            print(f"\nFound {len(sources)} sources.")
            for i, src in enumerate(sources):
                print(f"Source {i+1}: Score={src.get('score')}, ID={src.get('document_id')}")
        else:
            print("Error Response:")
            print(response.text)
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # First try with user's provided threshold (0.7)
    print("=== Test 1: User provided threshold (0.7) ===")
    test_chat(0.7)
    
    # Then try with lowered threshold (0.5)
    print("\n=== Test 2: Lowered threshold (0.5) ===")
    test_chat(0.5)
