import requests
import json
import time

url = "http://localhost:8000/api/v1/chat/completions"

headers = {
    "Content-Type": "application/json",
    # 模拟前端的 Token，这里实际上后端可能没有校验 Token 的有效性，或者我们可以使用任意字符串如果配置了 ALLOW_ANY
    "Authorization": "Bearer eyJhbGciOiJIUzUxMiJ9.eyJzdWIiOiIiLCJsb2dpbl91c2VyX2tleSI6IjY5MTJlOTdjLWE1MGEtNDkyNS1hMWE4LWJjNThlNDJkZjNiMSJ9.2OLoaNTUN_6_9Ljx0N9gFJIFN-d2NcRxS7t1dQ_3_ViZqYE77yXV6fumTXdbMW7TBRPwVlbKvb1DiBfdCQhr4Q"
}

payload = {
    "query": "公司的报销流程是怎样的？",
    "top_k": 10,
    "score_threshold": 0.7,
    "use_rerank": True
}

print(f"Sending request to {url}...")
start_time = time.time()
try:
    response = requests.post(url, headers=headers, json=payload, timeout=300) # 300秒超时，等待模型下载
    print(f"Status Code: {response.status_code}")
    try:
        print("Response JSON:", json.dumps(response.json(), indent=2, ensure_ascii=False))
    except:
        print("Response Text:", response.text)
except requests.exceptions.Timeout:
    print("Request timed out after 60 seconds")
except Exception as e:
    print(f"An error occurred: {e}")
finally:
    print(f"Time taken: {time.time() - start_time:.2f} seconds")
