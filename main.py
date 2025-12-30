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
    headers = {
        "Authorization": API_KEY,
        "User-Agent": "Mozilla/5.0"
    }
    
    # URL simplifiée à l'extrême : Uniquement Butterfly (category=1)
    # On ne filtre PAS par prix ou par nom ici pour tout recevoir
    url = "https://csfloat.com/api/v1/listings?category=1&limit=50"
    
    uv_deals, st_deals = [], []
    uv_tot, st_tot = 0, 0
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        print(f"DEBUG: Status {r.status_code} | Items reçus: {len(r.json().get('data', []))}")
        
        if r.status_code == 200:
            data = r.json().get("data", [])
            for i in data:
                item = i.get('item', {})
                name = item.get('market_hash_name', '')
                price = i['price'] / 100
                wear = item.get('float_value', 0.0)
                item_id = i['id']

                # Analyse Ultraviolet
                if "Ultraviolet" in name:
                    uv_tot += 1
                    # Filtre large pour le test : 566€ / Float 0.25
                    if price <= 566 and wear <= 0.25:
                        if item_id not in seen_items:
                            send_alert(name, price, wear, item_id, i.get('screenshot_url'))
                            seen_items.add(item_id)
                        uv_deals.append(item_id)

                # Analyse Stained
                elif "Stained" in name:
                    st_tot += 1
                    if price <= 551:
                        if item_id not in seen_items:
                            send_alert(name, price, wear, item_id, i.get('screenshot_url'))
                            seen_items.add(item_id)
                        st_deals.append(item_id)

        return uv_deals, uv_tot, st_deals, st_tot
    except Exception as e:
        print(f"ERREUR: {e}")
        return [], 0, [], 0

def send_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    msg = f"🎯 *OFFRE TROUVÉE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR L'ITEM]({url})"
    try:
        if img:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    global dashboard_message_id
    print("🚀 Sniper v38.0 (Mode Force Brute)")
    
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "🛰️ Démarrage Scan v38.0..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        uv_d, uv_t, st_d, st_t = get_market_data()
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 *Dernier scan :* `{now}`\n"
                  f"--- \n"
                  f"🟣 *Ultraviolet*\n"
                  f"    └ En ligne : `{uv_t}` | Deals : `{len(uv_d)}` \n\n"
                  f"🔵 *Stained*\n"
                  f"    └ En ligne : `{st_t}` | Deals : `{len(st_d)}` \n\n"
                  f"⚙️ *API Status :* `OK` (200)")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        time.sleep(30)

if __name__ == "__main__":
    main()
