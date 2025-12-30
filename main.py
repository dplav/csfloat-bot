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
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    
    # On retire le filtre (Field-Tested) du nom pour l'API, on filtrera nous-mêmes.
    # On utilise l'ID de définition pour le Butterfly (def_index=507)
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet", "search": "★ Butterfly Knife | Ultraviolet", "max_p": 565.99, "max_f": 0.2409, "key": "UV"},
        {"name": "★ Butterfly Knife | Stained", "search": "★ Butterfly Knife | Stained", "max_p": 550.99, "max_f": 0.45, "key": "ST"}
    ]
    
    results = {}

    for t in targets:
        # On demande 100 items d'un coup pour être sûr de tout ratisser
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['search']}&limit=100&sort_by=lowest_price&type=buy_now"
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                valid_items = []
                for i in data:
                    item_data = i.get('item', {})
                    wear = item_data.get('float_value', 0)
                    price = i['price'] / 100
                    
                    # FILTRE MANUEL DU CODE (On ne garde que le FT : 0.15 < float < 0.38)
                    if 0.15 <= wear <= 0.38:
                        valid_items.append(i)
                        
                        # ALERTE SI DANS TES PRIX
                        if price <= t['max_p'] and wear <= t['max_f']:
                            if i['id'] not in seen_items:
                                send_triple_alert(t['name'], price, wear, i['id'])
                                seen_items.add(i['id'])

                # Données pour le rapport
                low_p = valid_items[0]['price'] / 100 if valid_items else (data[0]['price']/100 if data else 0)
                results[t['key']] = {"count": len(valid_items), "total_api": len(data), "lowest": low_p}
            else:
                results[t['key']] = {"count": 0, "total_api": "ERR", "lowest": 0}
        except:
            results[t['key']] = {"count": 0, "total_api": "TIME", "lowest": 0}

    send_cycle_report(results)

def send_cycle_report(res):
    now = datetime.now().strftime('%H:%M:%S')
    report = (f"🔍 *SCAN BRUT CSFLOAT*\n"
              f"🕒 `{now}`\n"
              f"--- \n"
              f"🟣 *UV* : `{res['UV']['count']}` FT trouvés (sur {res['UV']['total_api']} items)\n"
              f"   └ Moins cher FT : `{res['UV']['lowest']}€` \n\n"
              f"🔵 *ST* : `{res['ST']['count']}` FT trouvés (sur {res['ST']['total_api']} items)\n"
              f"   └ Moins cher FT : `{res['ST']['lowest']}€` \n"
              f"--- \n"
              f"📡 *Mode* : `Scan 100 + Filtre Manuel FT` ")
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_notification": True})
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚀 *ALERTE ACHAT IMMÉDIAT* 🚀\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [LIEN CSFLOAT]({url})")
    try:
        for _ in range(3):
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    print("🚀 Sniper v53.0 (Scan Brut 100)")
    while True:
        get_market_data()
        time.sleep(30)

if __name__ == "__main__":
    main()
