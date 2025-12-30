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
dashboard_message_id = None

def get_market_data():
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # On cible uniquement l'Ultraviolet pour ce test
    target_name = "★ Butterfly Knife | Ultraviolet (Field-Tested)"
    url = f"https://csfloat.com/api/v1/listings?market_hash_name={target_name}&limit=10&sort_by=lowest_price"
    
    alerts_count = 0
    total_found = 0

    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                total_found += 1
                item_id = i['id']
                
                # TEST ULTIME : On envoie une alerte pour ABSOLUMENT TOUT ce qu'on trouve
                if item_id not in seen_items:
                    price = i['price'] / 100
                    wear = i.get('item', {}).get('float_value', 0)
                    
                    # On force l'envoi
                    send_alert(target_name, price, wear, item_id, i.get('screenshot_url'))
                    seen_items.add(item_id)
                    alerts_count += 1
    except Exception as e:
        print(f"Erreur : {e}")

    return alerts_count, total_found

def send_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚨 *TEST FORCE : ITEM DÉTECTÉ*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix brut API : {price:.2f}* (Vérifie si c'est € ou $)\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [LIEN CSFLOAT]({url})")
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    global dashboard_message_id
    print("🚀 Sniper v43.0 (TEST SANS FILTRE)")
    
    # Message de lancement
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": "🛠 MODE TEST SANS FILTRE ACTIVE. Le bot va envoyer tous les Ultraviolet qu'il voit."})
    
    while True:
        a_count, t_count = get_market_data()
        print(f"Scan : {t_count} items vus, {a_count} nouvelles alertes.")
        time.sleep(30)

if __name__ == "__main__":
    main()
