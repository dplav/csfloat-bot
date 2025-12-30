import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY").strip() if os.getenv("CSFLOAT_API_KEY") else ""

seen_items = set()
current_deals_inventory = {}
dashboard_message_id = None

def is_good_deal(name, price_eur, wear):
    # 1. ULTRAVIOLET FT (Max 545€ / Float <= 0.24)
    if "Ultraviolet" in name and "Field-Tested" in name:
        return price_eur <= 545 and wear <= 0.24

    # 2. STAINED WW (Max 490€)
    if "Stained" in name and "Well-Worn" in name:
        return price_eur <= 490
            
    return False

def get_market_data(full_hash_name):
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    params = {"limit": 50, "sort_by": "lowest_price", "market_hash_name": full_hash_name}
    
    found_deals = {}
    total_count = 0
    
    try:
        r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                total_count += 1
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                price = i['price'] / 100
                wear = item_data.get('float_value', 0.0)
                item_id = i['id']
                
                # Image
                img = i.get('screenshot_url') or item_data.get('icon_url')

                if is_good_deal(name, price, wear):
                    found_deals[item_id] = f"{name} ({price}€)"
                    if item_id not in seen_items:
                        send_alert(name, price, wear, item_id, img)
                        seen_items.add(item_id)
            return found_deals, total_count
        return {}, 0
    except: return {}, 0

def send_alert(name, price, wear, item_id, img_url):
    url = f"https://csfloat.com/item/{item_id}"
    text = (f"🎯 *BONNE AFFAIRE DÉTECTÉE !*\n\n"
            f"🔪 *{name}*\n"
            f"💰 *Prix : {price:.2f}€*\n"
            f"📉 *Float :* `{wear:.5f}`\n\n"
            f"🔗 [VOIR SUR CSFLOAT]({url})")
    
    # Tentative d'envoi avec photo
    try:
        if img_url:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "photo": img_url, "caption": text, "parse_mode": "Markdown"}, timeout=10)
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except:
        # Secours : envoi texte seul si l'image bloque
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)

def update_dashboard(text, message_id):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id, "text": text, "parse_mode": "Markdown"})

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v29.0 (Dashboard BFK + Alertes Fix)")
    
    # Init Dashboard
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "⏳ Initialisation DASHBOARD BFK..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Scans ciblés
        uv_deals, uv_tot = get_market_data("★ Butterfly Knife | Ultraviolet (Field-Tested)")
        st_deals, st_tot = get_market_data("★ Butterfly Knife | Stained (Well-Worn)")
        
        all_deals_now = {**uv_deals, **st_deals}
        
        # Dashboard au format exact demandé
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 *Dernier scan :* `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *UV FT (Max 530€ / Fl < 0.24)*\n"
                  f"   └ En ligne : `{uv_tot}` | Deals : `{len(uv_deals)}` \n\n"
                  f"🔵 *Stained WW (Max 490€)*\n"
                  f"   └ En ligne : `{st_tot}` | Deals : `{len(st_deals)}` \n\n"
                  f"✅ *Surveillance active.*")
        
        update_dashboard(report, dashboard_message_id)
        current_deals_inventory = all_deals_now
        time.sleep(45)

if __name__ == "__main__":
    main()

