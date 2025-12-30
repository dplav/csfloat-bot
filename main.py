import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
# Nettoyage strict de la clé API
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Taux de conversion actualisé (Ajuste si besoin)
USD_TO_EUR = 0.908 

seen_items = set()

def get_market_data():
    # Headers renforcés pour éviter le blocage 403
    headers = {
        "Authorization": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json"
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
                if data:
                    # Conversion Dollar -> Euro
                    low_p_usd = data[0]['price'] / 100
                    low_p_eur = low_p_usd * USD_TO_EUR
                    results[t['key']] = {"status": "OK", "count": len(data), "lowest": low_p_eur}

                    for i in data:
                        item_id = i['id']
                        if item_id not in seen_items:
                            price_eur = (i['price'] / 100) * USD_TO_EUR
                            wear = i.get('item', {}).get('float_value', 0)
                            
                            # Comparaison en Euros
                            if price_eur <= t['max_p'] and wear <= t['max_f']:
                                send_triple_alert(t['name'], price_eur, wear, item_id)
                                seen_items.add(item_id)
                else:
                    results[t['key']] = {"status": "VIDE", "count": 0, "lowest": 0}
            
            elif r.status_code == 429:
                results[t['key']] = {"status": "LIMITE (429)", "count": 0, "lowest": 0}
                time.sleep(10) # Pause courte si on est bridé
            else:
                results[t['key']] = {"status": f"ERREUR {r.status_code}", "count": 0, "lowest": 0}
                
        except Exception as e:
            results[t['key']] = {"status": "TIMEOUT", "count": 0, "lowest": 0}

    send_cycle_report(results)

def send_cycle_report(res):
    now = datetime.now().strftime('%H:%M:%S')
    
    # Construction du message de rapport
    msg = f"🛰️ **MONITORING CSFLOAT v56**\n🕒 `{now}`\n\n"
    for k, v in res.items():
        icon = "🟣" if k == "UV" else "🔵"
        msg += f"{icon} **{k}** : {v['status']}\n"
        if v['status'] == "OK":
            msg += f"   └ Vus: `{v['count']}` | Min: `{v['lowest']:.2f}€` \n"
    
    msg += f"\n💱 Taux: `1$ = {USD_TO_EUR}€`"
    
    try:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown", "disable_notification": True})
    except: pass

def send_triple_alert(name, price, wear, item_id):
    url = f"https://csfloat.com/item/{item_id}"
    alert_text = (f"🔥 **CIBLE DÉTECTÉE !** 🔥\n\n"
                  f"🔪 {name}\n"
                  f"💰 Prix: **{price:.2f}€**\n"
                  f"📉 Float: `{wear:.5f}`\n\n"
                  f"🛒 [ACHETER SUR CSFLOAT]({url})")
    try:
        # 3 envois successifs pour garantir la sonnerie
        for _ in range(3):
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": alert_text, "parse_mode": "Markdown"})
            time.sleep(0.5)
    except: pass

def main():
    print("🚀 Sniper v56.0 - Opérationnel")
    while True:
        get_market_data()
        time.sleep(40) # Délai de sécurité pour éviter le bannissement IP

if __name__ == "__main__":
    main()
