import os
import requests
import json

# Принудительно очищаем секреты от любых случайных символов форматирования (звездочек, пробелов, кавычек)
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "").replace("*", "").strip()
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "").replace("*", "").strip()

LIST_NAME = "AI_Bypass_List"
DOMAINS_URL = "https://raw.githubusercontent.com/Geohide/geohide-node/main/lists/gpt.txt"

headers = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

def get_domains():
    response = requests.get(DOMAINS_URL)
    return [line.strip() for line in response.text.splitlines() if line.strip() and not line.startswith("#")]

def get_existing_lists():
    url = f"https://cloudflare.com{CF_ACCOUNT_ID}/gateway/lists"
    res = requests.get(url, headers=headers).json()
    if not res.get("success"):
        print(f"❌ API Error: {json.dumps(res.get('errors'))}")
        exit(1)
    return res.get("result", [])

def create_or_update_list():
    domains = get_domains()
    lists = get_existing_lists()
    
    target_list = next((l for l in lists if l["name"] == LIST_NAME), None)
    items = [{"value": d} for d in domains]
    
    chunk_size = 800
    chunks = [items[i:i + chunk_size] for i in range(0, len(items), chunk_size)]

    if target_list:
        list_id = target_list["id"]
        print(f"🔄 Список {LIST_NAME} найден (ID: {list_id}). Обновляем...")
        
        url = f"https://cloudflare.com{CF_ACCOUNT_ID}/gateway/lists/{list_id}"
        payload = {"name": LIST_NAME, "type": "DOMAIN", "items": chunks}
        res = requests.put(url, headers=headers, json=payload).json()
        
        if not res.get("success"):
            print(f"❌ PUT Error: {json.dumps(res.get('errors'))}")
            exit(1)
            
        for chunk in chunks[1:]:
            url = f"https://cloudflare.com{CF_ACCOUNT_ID}/gateway/lists/{list_id}/items"
            res = requests.post(url, headers=headers, json=chunk).json()
            if not res.get("success"):
                print(f"❌ Append Error: {json.dumps(res.get('errors'))}")
                exit(1)
                
        print(f"✅ Успешно обновлено. Всего доменов: {len(domains)}")
    else:
        print(f"➕ Создаем новый список {LIST_NAME}...")
        url = f"https://cloudflare.com{CF_ACCOUNT_ID}/gateway/lists"
        
        payload = {"name": LIST_NAME, "type": "DOMAIN", "description": "ChatGPT Bypass", "items": chunks}
        res = requests.post(url, headers=headers, json=payload).json()
        
        if not res.get("success"):
            print(f"❌ POST Error: {json.dumps(res.get('errors'))}")
            exit(1)
            
        list_id = res["result"]["id"]
        
        for chunk in chunks[1:]:
            url = f"https://cloudflare.com{CF_ACCOUNT_ID}/gateway/lists/{list_id}/items"
            res = requests.post(url, headers=headers, json=chunk).json()
            if not res.get("success"):
                print(f"❌ Population Error: {json.dumps(res.get('errors'))}")
                exit(1)
                
        print(f"✅ Новый список создан. Всего доменов: {len(domains)}")

if __name__ == "__main__":
    create_or_update_list()
