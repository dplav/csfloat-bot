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
    
    # Stratégie v40 : On utilise le paramètre 'market_hash_name' AVEC l'étoile encodée
    # pour forcer l'API à nous donner le listing complet de ce modèle précis.
    uv_name = "★ Butterfly Knife | Ultraviolet (Field-Tested)"
    st_name = "★ Butterfly Knife | Stained (Well-Worn)"
    
    uv_deals, st_deals = [], []
    uv_tot, st_tot = 0, 0

    for target_name in [uv_name, st_name]:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={target_name}&limit=30&sort_by=lowest_price"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for i in data:
                    # On compte tout ce qui arrive
                    if "Ultraviolet" in target_name: uv_tot += 1
                    else: st_tot += 1
                    
                    item = i.get('item', {})
                    price = i['price'] / 100
                    wear = item.get('float_value', 0.0)
                    item_id = i['id']
                    
                    # FILTRES DE DÉTECTION
                    is_uv = "Ultraviolet" in target_name and price <= 568 and wear <= 0.245
                    is_st = "Stained" in target_name and price <= 555
                    
                    if (is_uv or is_st) and item_id not in seen_items:
                        send_alert(target_name, price, wear, item_id, i.get('screenshot_url'))
                        seen_items.add(item_id)
                        if is_uv: uv_deals.append(item_id)
                        else: st_deals.append(item_id)
        except Exception as e:
            print(f"Erreur sur {target_name}: {e}")

    return uv_deals, uv_tot, st_deals, st_tot

def send_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    msg = f"🎯 *OFFRE FORCÉE DÉTECTÉE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR SUR CSFLOAT]({url})"
    try:
        if img:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
    except: pass

def main():
    global dashboard_message_id
    print("🚀 Sniper v40.0 (Mode Référence Directe)")
    
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "🛰️ Scan v40.0 (Force Offline)..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        uv_d, uv_t, st_d, st_t = get_market_data()
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 *Dernier scan :* `{now}`\n"
                  f"--- \n"
                  f"🟣 *Ultraviolet FT*\n"
                  f"    └ En ligne : `{uv_t}` | Deals : `{len(uv_d)}` \n\n"
                  f"🔵 *Stained WW*\n"
                  f"    └ En ligne : `{st_t}` | Deals : `{len(st_d)}` \n\n"
                  f"⚙️ *API Status :* `OK` | *Mode :* `Forçage Référence` ")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        time.sleep(30)

if __name__ == "__main__":
    main()
