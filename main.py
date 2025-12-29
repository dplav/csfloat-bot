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

# Mémoire et Statistiques
seen_items = set()
current_deals_inventory = {}
new_announcements_count = 0
total_scans_done = 0

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

def scan_target(skin_name):
    global new_announcements_count
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    url = f"https://csfloat.com/api/v1/listings?limit=50&sort_by=lowest_price&full_text=Butterfly Knife {skin_name}"
    
    found_this_turn = {}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                item_id = i['id']
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                
                if skin_name in name:
                    price = i['price'] / 100
                    wear = item_data.get('float_value', 0.0)
                    
                    if is_good_deal(name, price, wear):
                        found_this_turn[item_id] = f"{name} ({price}€)"
                        
                        if item_id not in seen_items:
                            new_announcements_count += 1
                            send_telegram(f"🎯 *NOUVELLE OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR](https://csfloat.com/item/{item_id})")
                            seen_items.add(item_id)
            return found_this_turn
        return {}
    except:
        return {}

def send_telegram(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def main():
    global current_deals_inventory, new_announcements_count, total_scans_done
    print("🚀 Sniper v18.0 (Rapports Telegram Actifs)")
    
    last_report_time = time.time()
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Scans
        uv_found = scan_target("Ultraviolet")
        st_found = scan_target("Stained")
        all_found_now = {**uv_found, **st_found}
        
        # Détection des ventes
        for old_id, old_name in current_deals_inventory.items():
            if old_id not in all_found_now:
                send_telegram(f"💸 *VENDU !*\n\nL'item a disparu du marché :\n🔪 *{old_name}*")
        
        current_deals_inventory = all_found_now
        total_scans_done += 1

        # ENVOI DU RAPPORT TOUTES LES 15 MINUTES (900 secondes)
        if time.time() - last_report_time > 900:
            report_msg = (f"📊 *RAPPORT DE SURVEILLANCE*\n"
                          f"--- \n"
                          f"🔄 Cycles de scan : `{total_scans_done}`\n"
                          f"🆕 Nouvelles annonces détectées : `{new_announcements_count}`\n"
                          f"💎 Deals actuellement en ligne : `{len(current_deals_inventory)}`")
            send_telegram(report_msg)
            
            # Reset des compteurs de rapport
            new_announcements_count = 0
            last_report_time = time.time()

        print(f"[{now_str}] Scan OK. Deals en ligne: {len(current_deals_inventory)}")
        time.sleep(45)

if __name__ == "__main__":
    main()
