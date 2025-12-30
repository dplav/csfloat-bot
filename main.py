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
    # 1. ULTRAVIOLET FT (Max 565€ / Float <= 0.24)
    if "Ultraviolet" in name and "Field-Tested" in name:
        return price_eur <= 565 and wear <= 0.24

    # 2. STAINED (Toutes usures pour le scan, mais filtre prix à 550€)
    if "Stained" in name:
        return price_eur <= 550
            
    return False

def get_combined_data():
    """Récupère les 50 Butterfly les moins chers et trie en local"""
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    # On scanne les Butterfly les moins chers globalement pour ne rien rater
    url = "https://csfloat.com/api/v1/listings?limit=50&sort_by=lowest_price&type=butterfly_knife"
    
    uv_deals, st_deals = {}, {}
    uv_total, st_total = 0, 0
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                price = i['price'] / 100
                wear = item_data.get('float_value', 0.0)
                item_id = i['id']
                img = i.get('screenshot_url') or item_data.get('icon_url')

                # Tri Ultraviolet
                if "Ultraviolet" in name and "Field-Tested" in name:
                    uv_total += 1
                    if is_good_deal(name, price, wear):
                        uv_deals[item_id] = f"{name} ({price}€)"
                        if item_id not in seen_items:
                            send_alert(name, price, wear, item_id, img)
                            seen_items.add(item_id)
                
                # Tri Stained
                if "Stained" in name:
                    st_total += 1
                    if is_good_deal(name, price, wear):
                        st_deals[item_id] = f"{name} ({price}€)"
                        if item_id not in seen_items:
                            send_alert(name, price, wear, item_id, img)
                            seen_items.add(item_id)
                            
            return uv_deals, uv_total, st_deals, st_total
        return {}, 0, {}, 0
    except: return {}, 0, {}, 0

def send_alert(name, price, wear, item_id, img_url):
    url = f"https://csfloat.com/item/{item_id}"
    text = (f"🎯 *BONNE AFFAIRE DÉTECTÉE !*\n\n"
            f"🔪 *{name}*\n"
            f"💰 *Prix : {price:.2f}€*\n"
            f"📉 *Float :* `{wear:.5f}`\n\n"
            f"🔗 [VOIR SUR CSFLOAT]({url})")
    
    try:
        if img_url:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "photo": img_url, "caption": text, "parse_mode": "Markdown"}, timeout=10)
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v30.0 (Correction Détection)")
    
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "⏳ Initialisation DASHBOARD BFK..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        uv_d, uv_t, st_d, st_t = get_combined_data()
        all_deals_now = {**uv_d, **st_d}
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 *Dernier scan :* `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *UV FT (Max 565€ / Fl < 0.24)*\n"
                  f"    └ En ligne : `{uv_t}` | Deals : `{len(uv_d)}` \n\n"
                  f"🔵 *Stained (Max 550€)*\n"
                  f"    └ En ligne : `{st_t}` | Deals : `{len(st_d)}` \n\n"
                  f"✅ *Surveillance active.*")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                          json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        
        current_deals_inventory = all_deals_now
        time.sleep(45)

if __name__ == "__main__":
    main()
