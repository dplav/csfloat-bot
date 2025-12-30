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
    
    # TES FILTRES PRÉCIS
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.99, "max_f": 0.2409, "key": "UV FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 550.99, "max_f": 1.0, "key": "ST FT"}
    ]
    
    results = {}

    for t in targets:
        # AJOUT DE currency=EUR ET type=buy_now POUR ÉVITER LES ERREURS
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=50&sort_by=lowest_price&type=buy_now&currency=EUR"
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # Prix min trouvé
                low_p = data[0]['price'] / 100 if data else 0
                results[t['key']] = {
                    "count": len(data), 
                    "lowest": low_p, 
                    "filter_p": t['max_p']
                }

                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        price = i['price'] / 100
                        wear = i.get('item', {}).get('float_value', 0)
                        
                        # ALERTE SI LE PRIX CORRESPOND
                        if price <= t['max_p'] and wear <= (t.get('max_f') or 1.0):
                            send_triple_alert(t['name'], price, wear, item_id)
                            seen_items.add(item_id)
            else:
                results[t['key']] = {"count": "ERR " + str(r.status_code), "lowest": 0, "filter_p": t['max_p']}
        except Exception as e:
            results[t['key']] = {"count": "TIMEOUT", "lowest": 0, "filter_p": t['max_p']}

    send_cycle_report(results)

def send_cycle_report(res):
    now = datetime.now().strftime('%H:%M:%S')
    report = (f"📊 *RAPPORT D'ANALYSE (FIX EUR)*\n"
              f"🕒 Heure : `{now}`\n"
              f"--- \n"
              f"🟣 *UV FT* : `{res['UV FT']['count']}` items\n"
              f"   └ Min : `{res['UV FT']['lowest']}€` (Cible: <{res['UV FT']['filter_p']}€)\n\n"
              f"🔵 *ST FT* : `{res['ST FT']['count']}` items\n"
              f"   └ Min : `{res['ST FT']['lowest']}€` (Cible: <{res['ST FT']['filter_p']}€)\n"
              f"--- \n"
              f"⚙️ *Paramètres* : `EUR` | `Buy Now` | `FT Only` ")
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_notification": True})
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚀 🚀 *CIBLE TROUVÉE !* 🚀 🚀\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [LIEN DIRECT]({url})")
    try:
        for _ in range(3):
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_notification": False})
    except: pass

def main():
    print("🚀 Sniper v52.0 (Fix Devise EUR)")
    while True:
        get_market_data()
        time.sleep(30)

if __name__ == "__main__":
    main()
