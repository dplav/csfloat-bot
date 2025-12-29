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
    # On s'assure que c'est bien un Field-Tested
    if "Field-Tested" not in name: return False
    
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    
    if is_uv:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    if is_stained:
        if price_eur <= 550: return True
    return False

def scan_csfloat():
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    # On utilise l'ID de catégorie 'butterfly_knife' pour tout ramener d'un coup
    url = "https://csfloat.com/api/v1/listings?limit=50&sort_by=lowest_price&type=butterfly_knife"
    
    uv_list, st_list = [], []
    uv_deals, st_deals = {}, {}
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                
                # On ne traite que les Field-Tested Ultraviolet et Stained
                if "Field-Tested" in name:
                    price = i['price'] / 100
                    wear = item_data.get('float_value', 0.0)
                    item_id = i['id']

                    if "Ultraviolet" in name:
                        uv_list.append(item_id)
                        if is_good_deal(name, price, wear):
                            uv_deals[item_id] = f"{name} ({price}€)"
                            if item_id not in seen_items:
                                send_telegram(f"🎯 *NOUVELLE OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR](https://csfloat.com/item/{item_id})")
                                seen_items.add(item_id)
                    
                    elif "Stained" in name:
                        st_list.append(item_id)
                        if is_good_deal(name, price, wear):
                            st_deals[item_id] = f"{name} ({price}€)"
                            if item_id not in seen_items:
                                send_telegram(f"🎯 *NOUVELLE OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR](https://csfloat.com/item/{item_id})")
                                seen_items.add(item_id)
            
            return uv_deals, len(uv_list), st_deals, len(st_list)
        return {}, 0, {}, 0
    except: return {}, 0, {}, 0

def send_telegram(text):
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    return r.json().get("result", {}).get("message_id")

def update_dashboard(text, message_id):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id, "text": text, "parse_mode": "Markdown"})

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v23.0 (Scan Global Butterfly)")
    dashboard_message_id = send_telegram("⏳ Synchronisation du marché...")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        uv_d, uv_tot, st_d, st_tot = scan_csfloat()
        all_deals_now = {**uv_d, **st_d}
        
        # Détection des ventes
        for old_id, old_name in current_deals_inventory.items():
            if old_id not in all_deals_now:
                send_telegram(f"💸 *VENDU !*\n🔪 *{old_name}*")
        
        # Dashboard
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 Dernier scan : `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *Ultraviolet FT*\n"
                  f"   └ En ligne : `{uv_tot}`\n"
                  f"   └ (`{len(uv_d)}` bonne affaire)\n\n"
                  f"🔵 *Stained FT*\n"
                  f"   └ En ligne : `{st_tot}`\n"
                  f"   └ (`{len(st_d)}` bonne affaire)\n\n"
                  f"⚙️ Status : `Scan de 50 annonces globales` ")
        
        update_dashboard(report, dashboard_message_id)
        current_deals_inventory = all_deals_now
        time.sleep(45)

if __name__ == "__main__":
    main()
