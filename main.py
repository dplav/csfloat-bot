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
    
    # --- CONFIGURATION DE TEST : PRIX À 800€ ---
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_price": 800},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_price": 800}
    ]
    
    total_alerts_sent = 0
    
    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=10&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                total_on_market = len(data)
                
                # Le bot affiche dans les logs combien il en a trouvé
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {t['name']} : {total_on_market} en ligne.")

                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        price = i['price'] / 100
                        wear = i.get('item', {}).get('float_value', 0)
                        
                        # Vérification du prix à 800€
                        if price <= t['max_price']:
                            send_triple_alert(t['name'], price, wear, item_id, total_on_market)
                            seen_items.add(item_id)
                            total_alerts_sent += 1
        except Exception as e:
            print(f"Erreur technique : {e}")

    return total_alerts_sent

def send_triple_alert(name, price, wear, item_id, total_count):
    url = f"https://csfloat.com/item/{item_id}"
    
    # Le message inclut maintenant le nombre d'items en ligne
    msg = (f"🚨 🚨 *ALERTE PRIX (<800€)* 🚨 🚨\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n"
           f"📊 *Total en ligne :* `{total_count}` items\n\n"
           f"🚀 [ACHETER MAINTENANT]({url})")
    
    try:
        # TRIPLE ENVOI POUR FORCER LE SON
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔔 ALERTE SONORE 1/2"})
        
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔔 ALERTE SONORE 2/2"})
    except: pass

def main():
    print("🚀 Sniper v46.0 (Mode Test 800€ + Compteur)")
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": "🛠 Test 800€ activé.\nLe bot va sonner pour TOUS les items sous 800€."})
    
    while True:
        get_market_data()
        time.sleep(20)

if __name__ == "__main__":
    main()
