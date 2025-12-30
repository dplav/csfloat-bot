import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
# On nettoie l'API KEY de tout espace ou guillemet invisible
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

seen_items = set()
dashboard_message_id = None

def get_market_data():
    """Requête simplifiée au maximum pour bypass les erreurs de filtrage"""
    headers = {
        "Authorization": API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # On demande tous les Butterfly (category=1) triés par prix
    url = "https://csfloat.com/api/v1/listings?category=1&limit=50&sort_by=lowest_price"
    
    uv_deals, st_deals = [], []
    uv_tot, st_tot = 0, 0
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        # LOG DE DEBUG : Vérifie tes logs Railway pour voir ça
        print(f"DEBUG API: Status {r.status_code}")
        
        if r.status_code != 200:
            print(f"ERREUR API: {r.text}")
            return [], 0, [], 0

        data = r.json().get("data", [])
        for i in data:
            item = i.get('item', {})
            name = item.get('market_hash_name', '')
            price = i['price'] / 100
            wear = item.get('float_value', 0.0)
            item_id = i['id']

            # On vérifie si c'est l'un de nos deux couteaux
            if "Ultraviolet" in name:
                uv_tot += 1
                # Filtre UV FT : Max 565€ et Float < 0.24
                if "Field-Tested" in name and price <= 565.99 and wear <= 0.2409:
                    if item_id not in seen_items:
                        send_alert(name, price, wear, item_id, i.get('screenshot_url') or item.get('icon_url'))
                        seen_items.add(item_id)
                    uv_deals.append(item_id)

            elif "Stained" in name:
                st_tot += 1
                # Filtre Stained : Max 550€
                if price <= 550.99:
                    if item_id not in seen_items:
                        send_alert(name, price, wear, item_id, i.get('screenshot_url') or item.get('icon_url'))
                        seen_items.add(item_id)
                    st_deals.append(item_id)

        return uv_deals, uv_tot, st_deals, st_tot
    except Exception as e:
        print(f"CRASH: {e}")
        return [], 0, [], 0

def send_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    msg = f"🎯 *OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR]({url})"
    try:
        if img:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    global dashboard_message_id
    print("🚀 Sniper v37.0 (Debug Mode)")
    
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "🛰️ Scan v37.0 en cours..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        uv_d, uv_t, st_d, st_t = get_market_data()
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n🕒 *Dernier scan :* `{now}`\n--- \n"
                  f"🟣 *Ultraviolet*\n    └ En ligne : `{uv_t}` | Deals : `{len(uv_d)}` \n\n"
                  f"🔵 *Stained*\n    └ En ligne : `{st_t}` | Deals : `{len(st_d)}` \n\n"
                  f"⚙️ *API Status :* `Connecté` ")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        time.sleep(30)

if __name__ == "__main__":
    main()
