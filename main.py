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
    if "Field-Tested" not in name: return False
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    if is_uv:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    if is_stained:
        if price_eur <= 550: return True
    return False

def get_market_data(skin_name):
    """Scan ciblé via paramètres de filtrage CSFloat"""
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # On utilise market_hash_name avec le nom exact pour ne ramener QUE ce skin
    # ★ Butterfly Knife | Ultraviolet (Field-Tested)
    full_skin_name = f"★ Butterfly Knife | {skin_name} (Field-Tested)"
    
    params = {
        "limit": 50,
        "sort_by": "lowest_price",
        "market_hash_name": full_skin_name
    }
    
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

                if is_good_deal(name, price, wear):
                    found_deals[item_id] = f"{name} ({price}€)"
                    if item_id not in seen_items:
                        send_telegram(f"🎯 *NOUVELLE OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR](https://csfloat.com/item/{item_id})")
                        seen_items.add(item_id)
            return found_deals, total_count
        return {}, 0
    except: return {}, 0

def send_telegram(text):
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    return r.json().get("result", {}).get("message_id")

def update_dashboard(text, message_id):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id, "text": text, "parse_mode": "Markdown"})

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v25.0 (Ciblage Ultra-Précis)")
    dashboard_message_id = send_telegram("⏳ Connexion aux flux Ultraviolet et Stained...")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Scan exclusif des deux types
        uv_deals, uv_tot = get_market_data("Ultraviolet")
        st_deals, st_tot = get_market_data("Stained")
        
        all_deals_now = {**uv_deals, **st_deals}
        
        # Détection des ventes
        for old_id, old_name in current_deals_inventory.items():
            if old_id not in all_found_now:
                send_telegram(f"💸 *VENDU !*\n🔪 *{old_name}*")
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 Dernier scan : `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *Ultraviolet FT*\n"
                  f"   └ En ligne : `{uv_tot}`\n"
                  f"   └ (`{len(uv_deals)}` bonne affaire)\n\n"
                  f"🔵 *Stained FT*\n"
                  f"   └ En ligne : `{st_tot}`\n"
                  f"   └ (`{len(st_deals)}` bonne affaire)\n\n"
                  f"🎯 *Mode :* `Scan ciblé exclusif` ")
        
        update_dashboard(report, dashboard_message_id)
        current_deals_inventory = all_deals_now
        time.sleep(45)

if __name__ == "__main__":
    main()
