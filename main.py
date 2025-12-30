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

# Mémoire des items pour éviter les doublons
seen_items = set()

def get_market_data():
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # --- FILTRES UNIQUEMENT FIELD-TESTED ---
    targets = [
        {
            "name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", 
            "max_p": 565.99, "max_f": 0.2409, "key": "UV FT"
        },
        {
            "name": "★ Butterfly Knife | Stained (Field-Tested)", 
            "max_p": 550.99, "max_f": 1.0, "key": "ST FT"
        }
    ]
    
    results = {}

    for t in targets:
        # On encode l'URL pour gérer les caractères spéciaux (★, |)
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=10&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # Récupération du prix le plus bas pour le rapport
                low_p = data[0]['price'] / 100 if data else 0
                results[t['key']] = {
                    "count": len(data), 
                    "lowest": low_p, 
                    "filter_p": t['max_p'], 
                    "filter_f": t['max_f']
                }

                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        price = i['price'] / 100
                        wear = i.get('item', {}).get('float_value', 0)
                        
                        # LOGIQUE D'ALERTE STRICTE
                        if price <= t['max_p'] and wear <= t['max_f']:
                            send_triple_alert(t['name'], price, wear, item_id)
                            seen_items.add(item_id)
            else:
                results[t['key']] = {"count": "ERR", "lowest": 0, "filter_p": t['max_p'], "filter_f": t['max_f']}
        except:
            results[t['key']] = {"count": "TIMEOUT", "lowest": 0, "filter_p": t['max_p'], "filter_f": t['max_f']}

    send_cycle_report(results)

def send_cycle_report(res):
    now = datetime.now().strftime('%H:%M:%S')
    report = (f"📊 *RAPPORT D'ANALYSE CSFLOAT*\n"
              f"🕒 Heure : `{now}`\n"
              f"--- \n"
              f"🟣 *{res['UV FT']['count']}* Ultraviolet FT en ligne\n"
              f"   └ Min : `{res['UV FT']['lowest']}€` (Cible: <{res['UV FT']['filter_p']}€ / F<{res['UV FT']['filter_f']})\n\n"
              f"🔵 *{res['ST FT']['count']}* Stained FT en ligne\n"
              f"   └ Min : `{res['ST FT']['lowest']}€` (Cible: <{res['ST FT']['filter_p']}€)\n"
              f"--- \n"
              f"✅ Statut : `Scan Field-Tested uniquement` ")
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_notification": True})
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚀 🚀 *CIBLE FT DÉTECTÉE !* 🚀 🚀\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [ACHETER MAINTENANT]({url})")
    
    try:
        # Alertes bruyantes pour l'achat
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_notification": False})
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔔 **ALERTE ACHAT !**", "disable_notification": False})
    except: pass

def main():
    print("🚀 Sniper v50.0 (Uniquement Field-Tested)")
    while True:
        get_market_data()
        # Intervalle de 45 secondes pour le rapport
        time.sleep(45)

if __name__ == "__main__":
    main()
