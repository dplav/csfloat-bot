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
    headers = {
        "Authorization": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    # Noms exacts attendus par l'API pour le Field-Tested
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.99, "max_f": 0.2409, "key": "UV"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 550.99, "max_f": 1.0, "key": "ST"}
    ]
    
    results = {}

    for t in targets:
        # On demande 30 items, triés par prix croissant
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=30&sort_by=lowest_price"
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # On récupère le vrai prix minimum affiché par l'API
                low_p = data[0]['price'] / 100 if data else 0
                results[t['key']] = {"count": len(data), "lowest": low_p, "target": t['max_p']}

                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        price = i['price'] / 100
                        item_data = i.get('item', {})
                        wear = item_data.get('float_value', 0)
                        
                        # VERIFICATION DES FILTRES
                        if price <= t['max_p'] and wear <= t['max_f']:
                            send_triple_alert(t['name'], price, wear, item_id)
                            seen_items.add(item_id)
            else:
                results[t['key']] = {"count": "ERREUR API", "lowest": r.status_code, "target": t['max_p']}
        except Exception as e:
            results[t['key']] = {"count": "TIMEOUT", "lowest": 0, "target": t['max_p']}

    send_cycle_report(results)

def send_cycle_report(res):
    now = datetime.now().strftime('%H:%M:%S')
    report = (f"🔍 *STATUT DU SNIPER FT*\n"
              f"🕒 `{now}`\n"
              f"--- \n"
              f"🟣 *UV FT* : `{res['UV']['count']}` vus | Min : `{res['UV']['lowest']}€` (Cible < {res['UV']['target']}€)\n"
              f"🔵 *ST FT* : `{res['ST']['count']}` vus | Min : `{res['ST']['lowest']}€` (Cible < {res['ST']['target']}€)\n"
              f"--- \n"
              f"✅ *Statut* : Recherche en cours...")
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_notification": True})
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚀 *OBJET TROUVÉ AU PRIX CIBLE !* 🚀\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [CLIQUE ICI POUR ACHETER]({url})")
    try:
        # 3 messages pour forcer la sonnerie
        for _ in range(3):
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    print("🚀 Sniper v54.0 - Reset & Precision")
    while True:
        get_market_data()
        time.sleep(35) # Un peu plus de temps pour éviter les blocages

if __name__ == "__main__":
    main()
