import requests
import json

# URL-ul serviciului de Chat
url = "http://localhost:8000/chat"

# Payload-ul cererii de testare
payload = {
    "intrebare": "Care este tema cursului si ce subiecte se discuta?",
    "studentId": 101,
    "cursId": 1,
    "maxSaptamanaParcursa": 5
}

headers = {
    "Content-Type": "application/json"
}

print("[+] Trimitere cerere POST /chat...")
try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}\n")
    print("--- Raspuns RAG Primit de la Serviciul din Docker ---")
    print(json.dumps(response.json(), indent=2, ensure_ascii=False))
except Exception as e:
    print(f"[ERR] Eroare la trimiterea cererii: {e}")
