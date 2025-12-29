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

# Mémoire
seen_items = set()
current_deals_inventory = {}
dashboard_message_id = None # Stocke l'ID du message à modifier

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
                            # Alerte critique : on envoie un NOUVEAU message pour faire sonner le tel
                            send_telegram(f"🎯 *NOUVELLE OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR](https://csfloat.com/item/{item_id})")
                            seen_items.add(item_id)
            return found_this_turn
        return {}
    except: return {}

def send_telegram(text):
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
    return r.json().get("result", {}).get("message_id")

def update_dashboard(text, message_id):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id, "text": text, "parse_mode": "Markdown"})

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v20.0 (Dashboard Dynamique)")
    
    # Création du message de base
    dashboard_message_id = send_telegram("⏳ Initialisation du Dashboard...")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Scans
        uv_found = scan_target("Ultraviolet")
        st_found = scan_target("Stained")
        all_found_now = {**uv_found, **st_found}
        
        # Détection des ventes (Alerte message séparé)
        for old_id, old_name in current_deals_inventory.items():
            if old_id not in all_found_now:
                send_telegram(f"💸 *VENDU !*\n🔪 *{old_name}*")
        
        # Mise à jour du Dashboard
        status_icon = "🟢" if (len(all_found_now) > 0) else "⚪"
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n"
                  f"🕒 Dernier scan : `{now_str}`\n"
                  f"--- \n"
                  f"{status_icon} *Deals en ligne :* `{len(all_found_now)}` \n"
                  f"   └ 🟣 Ultraviolet : `{len(uv_found)}` \n"
                  f"   └ 🔵 Stained : `{len(st_found)}` \n\n"
                  f"✅ Surveillance active sur 100 annonces.")
        
        update_dashboard(report, dashboard_message_id)
        
        current_deals_inventory = all_found_now
        print(f"[{now_str}] Dashboard mis à jour.")
        time.sleep(45)

if __name__ == "__main__":
    main()
