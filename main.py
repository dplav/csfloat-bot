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

# Mémoire pour ne pas spammer le même item
seen_items = set()

def get_market_data():
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # --- TES FILTRES PRÉCIS ---
    targets = [
        {
            "name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", 
            "max_price": 565.99, 
            "max_float": 0.2409
        },
        {
            "name": "★ Butterfly Knife | Stained (Field-Tested)", 
            "max_price": 550.99, 
            "max_float": 1.0  # Pas de limite de float sur le Stained
        }
    ]
    
    for t in targets:
        # On demande les 20 moins chers
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=20&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                total_on_market = len(data)
                
                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        item_info = i.get('item', {})
                        price = i['price'] / 100
                        wear = item_info.get('float_value', 0)
                        
                        # VÉRIFICATION DES FILTRES
                        if price <= t['max_price'] and wear <= t['max_float']:
                            send_triple_alert(t['name'], price, wear, item_id, total_on_market)
                            seen_items.add(item_id)
            
            elif r.status_code == 429:
                print("⚠️ Trop de requêtes (Rate Limit). Pause...")
                time.sleep(60)
        except:
            pass

def send_triple_alert(name, price, wear, item_id, total_count):
    url = f"https://csfloat.com/item/{item_id}"
    
    msg = (f"🎯 *OFFRE DÉTECTÉE !* 🎯\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n"
           f"📊 *Total en ligne :* `{total_count}`\n\n"
           f"🚀 [ACHETER MAINTENANT]({url})")
    
    try:
        # TRIPLE NOTIFICATION POUR LE SON
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔔 **BIP BIP BIP !**", "parse_mode": "Markdown"})
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "⚠️ **OUVRE VITE !**", "parse_mode": "Markdown"})
    except:
        pass

def main():
    print("🚀 Sniper v47.0 (Opérationnel avec filtres réels)")
    
    # Message de confirmation au lancement
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": "🎯 **Sniper v47.0 lancé !**\n\nSurveillance :\n- UV FT < 566€ (Float < 0.24)\n- Stained < 551€"})
    
    while True:
        get_market_data()
        # Scan toutes les 25 secondes pour être réactif sans être banni
        time.sleep(25)

if __name__ == "__main__":
    main()
