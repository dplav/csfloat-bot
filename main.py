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

# On ne garde pas la mémoire entre les redémarrages pour ne rien rater
seen_items = set()
dashboard_message_id = None

def get_market_data():
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # On cible TRÈS large pour être sûr
    uv_name = "★ Butterfly Knife | Ultraviolet (Field-Tested)"
    st_name = "★ Butterfly Knife | Stained (Well-Worn)"
    
    uv_alerts, st_alerts = 0, 0
    uv_tot, st_tot = 0, 0

    for target_name in [uv_name, st_name]:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={target_name}&limit=50&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                items = r.json().get("data", [])
                for i in items:
                    # Comptage total pour le Dashboard
                    if "Ultraviolet" in target_name: uv_tot += 1
                    else: st_tot += 1
                    
                    item_data = i.get('item', {})
                    price = i['price'] / 100
                    wear = item_data.get('float_value', 0.0)
                    item_id = i['id']
                    
                    # FILTRES ULTRA SOUPLES (Ton image: 561.10€ / 0.1800)
                    if "Ultraviolet" in target_name:
                        if price <= 575.00 and wear <= 0.28: # Augmenté à 575€
                            if item_id not in seen_items:
                                send_alert(target_name, price, wear, item_id, i.get('screenshot_url'))
                                seen_items.add(item_id)
                                uv_alerts += 1
                    
                    elif "Stained" in target_name:
                        if price <= 555.00:
                            if item_id not in seen_items:
                                send_alert(target_name, price, wear, item_id, i.get('screenshot_url'))
                                seen_items.add(item_id)
                                st_alerts += 1
        except: pass

    return uv_alerts, uv_tot, st_alerts, st_tot

def send_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🎯 *OFFRE TROUVÉE !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [OUVRIR SUR CSFLOAT]({url})")
    try:
        if img:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    global dashboard_message_id
    print("🚀 Sniper v42.0 (Reset Mémoire & Force Capture)")
    
    # Message d'initialisation
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "♻️ Mémoire vidée. Scan v42.0 en cours..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        uv_a, uv_t, st_a, st_t = get_market_data()
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 *Dernier scan :* `{now}`\n"
                  f"--- \n"
                  f"🟣 *Ultraviolet FT (Max 575€)*\n"
                  f"    └ En ligne : `{uv_t}` | Alertes envoyées : `{uv_a}` \n\n"
                  f"🔵 *Stained WW (Max 555€)*\n"
                  f"    └ En ligne : `{st_t}` | Alertes envoyées : `{st_a}` \n\n"
                  f"✅ *Statut :* `Recherche active...` ")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        time.sleep(30)

if __name__ == "__main__":
    main()
