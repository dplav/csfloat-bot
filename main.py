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

# TAUX DE CHANGE (1 USD = ~0.91 EUR)
# On utilise 0.90 pour être sécuritaire et ne rater aucune offre
USD_TO_EUR = 0.905 

seen_items = set()

def get_market_data():
    headers = {
        "Authorization": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.99, "max_f": 0.2409, "key": "UV"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 550.99, "max_f": 1.0, "key": "ST"}
    ]
    
    results = {}

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=30&sort_by=lowest_price"
        
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # Conversion du prix le plus bas pour le rapport
                low_p_usd = data[0]['price'] / 100 if data else 0
                low_p_eur = low_p_usd * USD_TO_EUR
                
                results[t['key']] = {"count": len(data), "lowest_eur": low_p_eur, "target": t['max_p']}

                for i in data:
                    item_id = i['id']
                    if item_id not in seen_items:
                        price_usd = i['price'] / 100
                        # CONVERSION REELLE ICI
                        price_eur = price_usd * USD_TO_EUR
                        
                        item_data = i.get('item', {})
                        wear = item_data.get('float_value', 0)
                        
                        # VERIFICATION AVEC LE PRIX CONVERTI EN EUROS
                        if price_eur <= t['max_p'] and wear <= t['max_f']:
                            send_triple_alert(t['name'], price_eur, wear, item_id)
                            seen_items.add(item_id)
            else:
                results[t['key']] = {"count": "ERR", "lowest_eur": 0, "target": t['max_p']}
        except:
            results[t['key']] = {"count": "TIME", "lowest_eur": 0, "target": t['max_p']}

    send_cycle_report(results)

def send_cycle_report(res):
    now = datetime.now().strftime('%H:%M:%S')
    report = (f"🔍 *STATUT SNIPER (CONVERSION $/€)*\n"
              f"🕒 `{now}`\n"
              f"--- \n"
              f"🟣 *UV FT* : `{res['UV']['count']}` vus | Min : `{res['UV']['lowest_eur']:.2f}€` \n"
              f"🔵 *ST FT* : `{res['ST']['count']}` vus | Min : `{res['ST']['lowest_eur']:.2f}€` \n"
              f"--- \n"
              f"💱 *Taux utilisé* : `1$ = {USD_TO_EUR}€` \n"
              f"✅ *Statut* : Prix API convertis en Euros.")
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": report, "parse_mode": "Markdown", "disable_notification": True})
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🚀 *OBJET DÉTECTÉ (PRIX CONVERTI)* 🚀\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix estimé : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR SUR CSFLOAT]({url})")
    try:
        for _ in range(3):
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    print("🚀 Sniper v55.0 - Mode Conversion Monnaie")
    while True:
        get_market_data()
        time.sleep(35)

if __name__ == "__main__":
    main()
