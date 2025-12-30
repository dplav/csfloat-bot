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
    
    # Noms exacts pour le listing complet
    uv_name = "★ Butterfly Knife | Ultraviolet (Field-Tested)"
    st_name = "★ Butterfly Knife | Stained (Well-Worn)"
    
    uv_deals, st_deals = [], []
    uv_tot, st_tot = 0, 0

    for target_name in [uv_name, st_name]:
        # On demande les 50 moins chers pour chaque modèle
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={target_name}&limit=50&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for i in data:
                    item = i.get('item', {})
                    price = i['price'] / 100
                    wear = item.get('float_value', 0.0)
                    item_id = i['id']
                    
                    if "Ultraviolet" in target_name:
                        uv_tot += 1
                        # FILTRE UV : On monte à 568€ et float 0.26 pour être large (Ton image est à 561€ / 0.18)
                        if price <= 568.00 and wear <= 0.26:
                            if item_id not in seen_items:
                                send_alert(target_name, price, wear, item_id, i.get('screenshot_url') or item.get('icon_url'))
                                seen_items.add(item_id)
                            uv_deals.append(item_id)
                    
                    else:
                        st_tot += 1
                        # FILTRE STAINED : On monte à 555€
                        if price <= 555.00:
                            if item_id not in seen_items:
                                send_alert(target_name, price, wear, item_id, i.get('screenshot_url') or item.get('icon_url'))
                                seen_items.add(item_id)
                            st_deals.append(item_id)
                            
        except Exception as e:
            print(f"Erreur: {e}")

    return uv_deals, uv_tot, st_deals, st_tot

def send_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    msg = (f"🎯 *ALERTE BONNE AFFAIRE !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR SUR CSFLOAT]({url})")
    try:
        if img:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except:
        pass

def main():
    global dashboard_message_id
    print("🚀 Sniper v41.0 (Filtres Élargis)")
    
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "✅ Scan v41.0 opérationnel..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        uv_d, uv_t, st_d, st_t = get_market_data()
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 *Dernier scan :* `{now}`\n"
                  f"--- \n"
                  f"🟣 *Ultraviolet FT*\n"
                  f"    └ En ligne : `{uv_t}` | Alertes : `{len(uv_d)}` \n\n"
                  f"🔵 *Stained WW*\n"
                  f"    └ En ligne : `{st_t}` | Alertes : `{len(st_d)}` \n\n"
                  f"⚙️ *Status :* `Surveillance Active` ")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        time.sleep(30)

if __name__ == "__main__":
    main()
