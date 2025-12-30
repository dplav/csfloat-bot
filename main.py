import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_LIMIT = 50
CHECK_INTERVAL = 30
last_report_id = None
last_update_id = 0 

# Mémoire des items (ID: {price, name})
seen_items = {}

def get_updates():
    """Récupère les commandes /test envoyées au bot"""
    global last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}&timeout=1"
    try:
        r = requests.get(url, timeout=5).json()
        if "result" in r:
            for update in r["result"]:
                last_update_id = update["update_id"]
                if "message" in update and "text" in update["message"]:
                    msg = update["message"]["text"]
                    print(f"Commande reçue : {msg}") # Debug
                    if msg == "/test1":
                        trigger_test(1)
                    elif msg == "/test3":
                        trigger_test(3)
    except Exception as e:
        print(f"Erreur getUpdates : {e}")

def trigger_test(count):
    """Force une alerte test"""
    headers = {"Authorization": API_KEY}
    # On prend n'importe quel couteau pour le test
    url = f"https://csfloat.com/api/v1/listings?limit={count}&sort_by=lowest_price"
    try:
        r = requests.get(url, headers=headers).json()
        data = r.get("data", [])
        for i in data:
            name = i['item']['market_hash_name']
            price = i['price']/100
            wear = i['item']['float_value']
            send_urgent_alert(name, price, wear, i['id'], is_test=True)
    except:
        send_telegram_msg("❌ Erreur test API")

def get_market_data():
    global last_report_id
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.99, "max_f": 0.2409, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 520.00, "max_f": 1.0, "id": "ST_FT"},
        {"name": "★ Butterfly Knife | Stained (Well-Worn)", "max_p": 480.00, "max_f": 1.0, "id": "ST_WW"}
    ]
    
    status_data = []
    current_scan_ids = set()

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit={SCAN_LIMIT}&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                low_p = data[0]['price'] / 100 if data else 0
                status_data.append(f"📍 {t['id']}: {len(data)} vus | Min: ${low_p}")

                for i in data:
                    item_id = i['id']
                    current_scan_ids.add(item_id)
                    price = i['price'] / 100
                    wear = i.get('item', {}).get('float_value', 0)

                    if price <= t['max_p'] and wear <= t['max_f']:
                        if item_id not in seen_items:
                            send_urgent_alert(t['name'], price, wear, item_id)
                            seen_items[item_id] = {"price": price, "name": t['name']}
            else:
                status_data.append(f"❌ {t['id']}: ERR {r.status_code}")
        except:
            status_data.append(f"⚠️ {t['id']}: Timeout")

    check_sold_items(current_scan_ids)
    update_report(status_data)

def check_sold_items(current_ids):
    sold_ids = []
    for sid, info in seen_items.items():
        if sid not in current_ids:
            send_telegram_msg(f"✅ **VENDU**\n{info['name']} à ${info['price']}")
            sold_ids.append(sid)
    for sid in sold_ids:
        del seen_items[sid]

def update_report(lines):
    global last_report_id
    text = f"📊 **STATUT SNIPER** ({datetime.now().strftime('%H:%M:%S')})\n" + "\n".join(lines)
    text += f"\n\n⚙️ Commandes : `/test1` | `/test3`"
    
    if last_report_id is None:
        res = send_telegram_msg(text, silent=True)
        if res and "result" in res: 
            last_report_id = res['result']['message_id']
    else:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown"})

def send_urgent_alert(name, price, wear, item_id, is_test=False):
    prefix = "🧪 [TEST] " if is_test else "🚀 "
    url = f"https://csfloat.com/item/{item_id}"
    msg = f"{prefix}**ALERTE !**\n\n🔪 {name}\n💰 **${price:.2f}**\n📉 Float: `{wear:.5f}`\n\n🔗 [VOIR]({url})"
    for _ in range(3):
        send_telegram_msg(msg)
        time.sleep(0.3)

def send_telegram_msg(text, silent=False):
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_notification": silent})
        return r.json()
    except: return None

if __name__ == "__main__":
    print("Démarrage v1.2...")
    while True:
        # On vérifie les commandes plusieurs fois pendant la pause
        for _ in range(30): 
            get_updates()
            time.sleep(1)
        # Scan du marché toutes les 30 sec environ
        get_market_data()
