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
    
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_price": 565.99, "max_float": 0.2409, "key": "UV"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_price": 550.99, "max_float": 1.0, "key": "ST"}
    ]
    
    results = {}

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=15&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # On récupère le prix le plus bas trouvé pour le rapport
                lowest_price = data[0]['price'] / 100 if data else 0
                results[t['key']] = {"count": len(data), "lowest": lowest_price}

                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        price = i['price'] / 100
                        wear = i.get('item', {}).get('float_value', 0)
                        
                        # LOGIQUE D'ALERTE
                        if price <= t['max_price'] and wear <= t['max_float']:
                            send_triple_alert(t['name'], price, wear, item_id)
                            seen_items.add(item_id)
            else:
                results[t['key']] = {"count": "ERR", "lowest": 0}
        except:
            results[t['key']] = {"count": "TIMEOUT", "lowest": 0}

    # ENVOI DU RAPPORT DE CYCLE
    send_cycle_report(results)

def send_cycle_report(res):
    now = datetime.now().strftime('%H:%M:%S')
    report = (f"📊 *RAPPORT D'ANALYSE CSFLOAT*\n"
              f"🕒 Heure : `{now}`\n"
              f"--- \n"
              f"🟣 *UV FT* : `{res['UV']['count']}` items | Min : `{res['UV']['lowest']}€` \n"
              f"🔵 *ST FT* : `{res['ST']['count']}` items | Min : `{res['ST']['lowest']}€` \n"
              f"--- \n"
              f"✅ Statut : `Analyse terminée, en attente de prix cible...` ")
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_notification": True})
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚀 🚀 *CIBLE DÉTECTÉE !* 🚀 🚀\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [ACHETER MAINTENANT]({url})")
    
    try:
        # L'alerte d'achat n'est PAS silencieuse (disable_notification: False)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_notification": False})
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔔 **BIP BIP !**", "disable_notification": False})
    except: pass

def main():
    print("🚀 Sniper v48.0 (Rapports complets activés)")
    while True:
        get_market_data()
        # On attend 45 secondes entre les rapports pour ne pas spammer ton Telegram
        time.sleep(45)

if __name__ == "__main__":
    main()
