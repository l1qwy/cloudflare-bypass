import os
import requests
import json

# Очищаем секреты от случайных символов форматирования (звездочек, пробелов, кавычек)
CF_API_TOKEN = os.environ.get("CF_API_TOKEN", "").replace("*", "").strip()
CF_ACCOUNT_ID = os.environ.get("CF_ACCOUNT_ID", "").replace("*", "").strip()

LIST_NAME = "AI_Bypass_List"
DOMAINS_URL = "https://githubusercontent.com"

# ИСУПРАВЛЕНО: Правильный базовый URL для Cloudflare API v4 Gateway
BASE_URL = f"https://api.cloudflare.com/client/v4/accounts/{CF_ACCOUNT_ID}/gateway/lists"

headers = {
    "Authorization": f"Bearer {CF_API_TOKEN}",
    "Content-Type": "application/json"
}

def get_domains():
    try:
        response = requests.get(DOMAINS_URL, timeout=10)
    except Exception as e:
        print(f"❌ Ошибка сети при запросе к Geohide: {e}")
        exit(1)

    # Проверяем, что сайт отдал успешный ответ, а не ошибку сервера
    if response.status_code != 200 or "<!DOCTYPE html>" in response.text:
        print(f"❌ Не удалось получить список доменов. Статус: {response.status_code}")
        print("Возможно, сайт geohide.ru временно недоступен или включил защиту от ботов.")
        exit(1)

    valid_domains = []
    for line in response.text.splitlines():
        line = line.strip()
        # Отсекаем пустые строки, комментарии, пробелы внутри строк и адреса с портами (где есть ":")
        if line and not line.startswith("#") and ":" not in line and " " not in line:
            # На всякий случай проверяем, что строка похожа на домен (содержит точку)
            if "." in line:
                valid_domains.append(line)

    print(f"📥 Успешно загружено валидных доменов с Geohide: {len(valid_domains)}")
    return valid_domains

def get_existing_lists():
    url = BASE_URL
    print(f"📡 Отправляем запрос на URL: {url.replace(CF_ACCOUNT_ID, '***')}")
    
    response = requests.get(url, headers=headers)
    
    if response.status_code != 200:
        print(f"❌ Сервер вернул статус-код: {response.status_code}")
        print(f"📄 Сырой ответ сервера: {response.text}")
        exit(1)
        
    res = response.json()
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
        
        url = f"{BASE_URL}/{list_id}"
        payload = {"name": LIST_NAME, "type": "DOMAIN", "items": chunks[0] if chunks else []}
        res = requests.put(url, headers=headers, json=payload).json()
        
        if not res.get("success"):
            print(f"❌ PUT Error: {json.dumps(res.get('errors'))}")
            exit(1)
            
        for chunk in chunks[1:]:
            url = f"{BASE_URL}/{list_id}/items"
            res = requests.post(url, headers=headers, json={"append": chunk}).json()
            if not res.get("success"):
                print(f"❌ Append Error: {json.dumps(res.get('errors'))}")
                exit(1)
                
        print(f"✅ Успешно обновлено. Всего доменов: {len(domains)}")
    else:
        print(f"➕ Создаем новый список {LIST_NAME}...")
        url = BASE_URL
        
        payload = {"name": LIST_NAME, "type": "DOMAIN", "description": "ChatGPT Bypass", "items": chunks[0] if chunks else []}
        res = requests.post(url, headers=headers, json=payload).json()
        
        if not res.get("success"):
            print(f"❌ POST Error: {json.dumps(res.get('errors'))}")
            exit(1)
            
        list_id = res["result"]["id"]
        
        for chunk in chunks[1:]:
            url = f"{BASE_URL}/{list_id}/items"
            res = requests.post(url, headers=headers, json={"append": chunk}).json()
            if not res.get("success"):
                print(f"❌ Population Error: {json.dumps(res.get('errors'))}")
                exit(1)
                
        print(f"✅ Новый список создан. Всего доменов: {len(domains)}")

if __name__ == "__main__":
    create_or_update_list()
