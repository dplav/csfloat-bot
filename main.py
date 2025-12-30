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
    # 1. ULTRAVIOLET FT (Max 530€ / Float < 0.24)
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price_eur <= 530 and wear <= 0.24:
            return True

    # 2. STAINED WW (Max 490€)
    if "Stained" in name and "Well-Worn" in name:
        if price_eur <= 490:
            return True

    # 3. TEST : HUNTSMAN DOPPLER PHASE 3 MW (Pas de budget)
    if "Huntsman Knife" in name and "Doppler" in name and "Minimal Wear" in name:
        if "Phase 3" in name:
            return True
            
    return False

def get_market_data(full_hash_name):
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    params = {
        "limit": 50,
        "sort_by": "lowest_price",
        "market_hash_name": full_hash_name
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
                        send_telegram(f"🎯 *ALERTE CRITÈRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR](https://csfloat.com/item/{item_id})")
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
    print("🚀 Sniper v26.0 (MAJ Critères + Test Huntsman)")
    dashboard_message_id = send_telegram("⏳ Démarrage du Dashboard v26.0...")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Scans ciblés
        uv_deals, uv_tot = get_market_data("★ Butterfly Knife | Ultraviolet (Field-Tested)")
        st_deals, st_tot = get_market_data("★ Butterfly Knife | Stained (Well-Worn)")
        ht_deals, ht_tot = get_market_data("★ Huntsman Knife | Doppler (Minimal Wear)")
        
        all_deals_now = {**uv_deals, **st_deals, **ht_deals}
        
        # Détection des ventes
        for old_id, old_name in current_deals_inventory.items():
            if old_id not in all_deals_now:
                send_telegram(f"💸 *VENDU !*\n🔪 *{old_name}*")
        
        # Rapport
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 Dernier scan : `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *UV FT (Max 530€ / Fl < 0.24)*\n"
                  f"   └ En ligne : `{uv_tot}` | Deals : `{len(uv_deals)}` \n\n"
                  f"🔵 *Stained WW (Max 490€)*\n"
                  f"   └ En ligne : `{st_tot}` | Deals : `{len(st_deals)}` \n\n"
                  f"🗡️ *TEST: Huntsman Doppler MW*\n"
                  f"   └ En ligne : `{ht_tot}` | Deals (P3) : `{len(ht_deals)}` \n\n"
                  f"✅ Surveillance active.")
        
        update_dashboard(report, dashboard_message_id)
        current_deals_inventory = all_deals_now
        time.sleep(45)

if __name__ == "__main__":
    main()
