import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
HEADERS = {"Authorization": CSFLOAT_API_KEY}

# Configuration des cibles avec leurs IDs techniques (plus fiable que le nom)
 CIBLES = {
    "Ultraviolet": {"id": 98, "max_price": 600},
    "Freehand": {"id": 588, "max_price": 600},
    "Case Hardened": {"id": 44, "max_price": 600}
}

def update_status(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_notification": True}
    return requests.post(url, json=payload).json().get("result", {}).get("message_id")

def delete_message(msg_id):
    if msg_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id})

def is_good_deal(item):
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    
    if "Ultraviolet" in name:
        if "Field-Tested" in name and (price <= 515 or (wear <= 0.16 and price <= 580)): return True
        if "Minimal Wear" in name and price <= 600: return True

    if "Freehand" in name:
        if "Factory New" in name and price <= 600: return True
        if "Minimal Wear" in name and price <= 570: return True

    if "Case Hardened" in name:
        if price <= 540 or item.get("item", {}).get("is_blue_gem", False): return True
                
    return False

def run_scan():
    for nom, config in CIBLES.items():
        # Paramètres de recherche ultra-spécifiques
        params = {
            "limit": 20,
            "defindex": 507, # ID du Butterfly Knife
            "paint_index": config["id"],
            "sort_by": "most_recent"
        }
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", [])
                print(f"🔎 {nom} : {len(items)} derniers items vérifiés.")
                for item in items:
                    if is_good_deal(item):
                        send_alert(item)
            time.sleep(1) # Petite pause pour ne pas saturer l'API
        except Exception as e:
            print(f"⚠️ Erreur sur {nom} : {e}")

def send_alert(item):
    name = item['item']['market_hash_name']
    price = item['price'] / 100
    img = item['item'].get('screenshot', item['item'].get('image'))
    url = f"https://csfloat.com/item/{item['id']}"
    
    msg = (f"🎯 *AUBAINE DÉTECTÉE !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price}€*\n"
           f"📉 *Float :* `{item['item']['float_value']:.5f}`\n\n"
           f"🔗 [VOIR SUR CSFLOAT]({url})")
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})

def main():
    last_msg_id = None
    # 6 cycles de ~45 sec pour couvrir le Cron de 5 min
    for i in range(6):
        now = datetime.now().strftime("%H:%M:%S")
        delete_message(last_msg_id)
        last_msg_id = update_status(f"🛰️ *Sniper Précision ON*\nCycle : `{i+1}/6` | `{now}`\nCibles : UV, Freehand, CH")
        
        run_scan()
        if i < 5:
            time.sleep(40)
    
    delete_message(last_msg_id)

if __name__ == "__main__":
    main()
