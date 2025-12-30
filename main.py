import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

seen_items = set()

def get_market_data():
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    # On reste sur Freehand pour le test de son
    target_name = "★ Butterfly Knife | Freehand (Field-Tested)"
    url = f"https://csfloat.com/api/v1/listings?market_hash_name={target_name}&limit=5&sort_by=lowest_price"
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                item_id = i['id']
                if item_id not in seen_items:
                    price = i['price'] / 100
                    wear = i.get('item', {}).get('float_value', 0)
                    send_triple_alert(target_name, price, wear, item_id)
                    seen_items.add(item_id)
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    
    # 1. Le message d'alerte principal
    msg = (f"🚨 *ALERTE !* 🚨\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n\n🚀 [ACHETER]({url})")
    
    try:
        # ENVOI TRIPLE POUR FORCER LE SON
        # Message 1
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_notification": False})
        
        # Message 2 (Flash)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔔 REVEILLE-TOI ! 🔔", "disable_notification": False})
        
        # Message 3 (Flash)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ VITE VITE VITE ! ⚠️", "disable_notification": False})
    except: pass

def main():
    print("🚀 Sniper v44.2 (Triple Notification)")
    while True:
        get_market_data()
        time.sleep(20)

if __name__ == "__main__":
    main()
