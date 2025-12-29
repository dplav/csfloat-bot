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

def scan_target(skin_name):
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    # On cherche spécifiquement le modèle Field-Tested pour le comptage
    url = f"https://csfloat.com/api/v1/listings?limit=50&sort_by=lowest_price&full_text=Butterfly Knife {skin_name} Field-Tested"
    
    deals_found = {}
    total_on_market = 0
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                item_id = i['id']
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                
                # On compte uniquement si c'est exactement le bon skin en FT
                if skin_name in name and "Field-Tested" in name:
                    total_on_market += 1
                    price = i['price'] / 100
                    wear = item_data.get('float_value', 0.0)
                    
                    if is_good_deal(name, price, wear):
                        deals_found[item_id] = f"{name} ({price}€)"
                        if item_id not in seen_items:
                            send_telegram(f"🎯 *NOUVELLE OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR](https://csfloat.com/item/{item_id})")
                            seen_items.add(item_id)
            return deals_found, total_on_market
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
    print("🚀 Sniper v22.0 (Inventaire complet)")
    dashboard_message_id = send_telegram("⏳ Analyse du marché en cours...")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Scans
        uv_deals, uv_total = scan_target("Ultraviolet")
        st_deals, st_total = scan_target("Stained")
        all_deals_now = {**uv_deals, **st_deals}
        
        # Détection des ventes
        for old_id, old_name in current_deals_inventory.items():
            if old_id not in all_deals_now:
                send_telegram(f"💸 *VENDU !*\n🔪 *{old_name}*")
        
        # Construction du Dashboard
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 Dernier scan : `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *Ultraviolet Field-Tested*\n"
                  f"   └ En ligne : `{uv_total}`\n"
                  f"   └ (`{len(uv_deals)}` bonne affaire)\n\n"
                  f"🔵 *Stained Field-Tested*\n"
                  f"   └ En ligne : `{st_total}`\n"
                  f"   └ (`{len(st_deals)}` bonne affaire)\n\n"
                  f"⚙️ Status : `Recherche active...`")
        
        update_dashboard(report, dashboard_message_id)
        current_deals_inventory = all_deals_now
        time.sleep(45)

if __name__ == "__main__":
    main()
