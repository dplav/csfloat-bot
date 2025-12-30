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
    if "Ultraviolet" in name and "Field-Tested" in name:
        return price_eur <= 565.99 and wear <= 0.2409
    if "Stained" in name:
        return price_eur <= 550.99
    return False

def get_data_by_id(def_index):
    """Scan par ID technique (541=UV, 539=Stained)"""
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    # On cible l'ID du skin et le type Butterfly (category=1)
    url = f"https://csfloat.com/api/v1/listings?limit=50&sort_by=lowest_price&category=1&def_index={def_index}"
    
    found_deals = {}
    total_count = 0
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                total_count += 1
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                price = i['price'] / 100
                wear = item_data.get('float_value', 0.0)
                item_id = i['id']
                img = i.get('screenshot_url') or item_data.get('icon_url')

                if is_good_deal(name, price, wear):
                    found_deals[item_id] = f"{name} ({price}€)"
                    if item_id not in seen_items:
                        send_alert(name, price, wear, item_id, img)
                        seen_items.add(item_id)
            return found_deals, total_count
        return {}, 0
    except:
        return {}, 0

def send_alert(name, price, wear, item_id, img_url):
    url = f"https://csfloat.com/item/{item_id}"
    caption = (f"🎯 *OFFRE DÉTECTÉE !*\n\n🔪 *{name}*\n💰 *Prix : {price:.2f}€*\n📉 *Float :* `{wear:.5f}`\n\n🔗 [VOIR SUR CSFLOAT]({url})")
    try:
        if img_url:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "photo": img_url, "caption": caption, "parse_mode": "Markdown"}, timeout=10)
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"}, timeout=10)
    except:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"}, timeout=10)

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v36.0 (Mode Technique ID)")
    
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔄 Connexion aux flux techniques..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # 541 = Ultraviolet | 539 = Stained
        uv_deals, uv_t = get_data_by_id(541)
        st_deals, st_t = get_data_by_id(539)
        
        all_deals_now = {**uv_deals, **st_deals}
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 *Dernier scan :* `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *UV (ID 541)*\n"
                  f"    └ En ligne : `{uv_t}` | Deals : `{len(uv_deals)}` \n\n"
                  f"🔵 *Stained (ID 539)*\n"
                  f"    └ En ligne : `{st_t}` | Deals : `{len(st_deals)}` \n\n"
                  f"📡 *Status :* `Scan par ID direct` ")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        
        current_deals_inventory = all_deals_now
        time.sleep(30)

if __name__ == "__main__":
    main()
