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
    
    # 1. Ultraviolet FT
    # 2. Stained (On scanne tout le Stained pour ne rien rater)
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_price": 568, "max_float": 0.245},
        {"name": "★ Butterfly Knife | Stained", "max_price": 555, "max_float": 1.0}
    ]
    
    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=20&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        item_info = i.get('item', {})
                        price = i['price'] / 100
                        wear = item_info.get('float_value', 0)
                        
                        # Vérification des filtres
                        if price <= t['max_price'] and wear <= t['max_float']:
                            send_triple_alert(t['name'], price, wear, item_id)
                            seen_items.add(item_id)
        except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚨 🚨 *APPEL DU SNIPER* 🚨 🚨\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🚀 [ACHETER IMMÉDIATEMENT]({url})")
    
    try:
        # TRIPLE ENVOI POUR FORCER LE RÉVEIL DU TÉLÉPHONE
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "📢 VITE ! VITE ! VITE !"})
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔔 CLIQUE SUR LE LIEN AU-DESSUS !"})
    except: pass

def main():
    print("🚀 Sniper v45.0 (Opérationnel : UV & Stained)")
    # Message de confirmation
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": "🎯 Sniper v45.0 Actif !\nSurveillance : UV FT (<568€) & Stained (<555€)"})
    
    while True:
        get_market_data()
        time.sleep(25) # Rythme soutenu pour ne pas se faire bannir mais être réactif

if __name__ == "__main__":
    main()
