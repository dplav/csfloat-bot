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

# Mémoire pour les alertes et le suivi des ventes
seen_items = set()        # Pour ne pas spammer les alertes
current_deals_in_inventory = {}  # {item_id: name} pour savoir ce qui est en ligne

def is_good_deal(name, price_eur, wear):
    if "Field-Tested" not in name:
        return False
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
    
    found_this_turn = {} # Pour stocker ce qu'on voit maintenant
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            in_criteria_count = 0
            
            for i in items:
                item_id = i['id']
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                
                if skin_name in name:
                    price = i['price'] / 100
                    wear = item_data.get('float_value', 0.0)
                    
                    if is_good_deal(name, price, wear):
                        in_criteria_count += 1
                        found_this_turn[item_id] = f"{name} ({price}€)"
                        
                        # Alerte si nouveau
                        if item_id not in seen_items:
                            send_telegram(f"🎯 *NOUVELLE OFFRE !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR L'OFFRE](https://csfloat.com/item/{item_id})")
                            seen_items.add(item_id)
            
            return len(items), in_criteria_count, found_this_turn
        return 0, 0, {}
    except:
        return 0, 0, {}

def send_telegram(text):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def main():
    global current_deals_in_inventory
    print("🚀 Sniper v17.0 (Suivi des Ventes Actif)")
    
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        
        # Scan
        uv_total, uv_match, uv_found = scan_target("Ultraviolet")
        st_total, st_match, st_found = scan_target("Stained")
        
        # Fusion des résultats actuels
        all_found_now = {**uv_found, **st_found}
        
        # VÉRIFICATION DES VENTES
        # Si un item était là au tour d'avant mais n'est plus là maintenant
        for old_id, old_name in current_deals_in_inventory.items():
            if old_id not in all_found_now:
                msg = f"🔔 *VENDU !*\n\nL'item suivant a quitté le marché :\n🔪 *{old_name}*"
                print(f"[{now}] 💸 Vendu : {old_name}")
                send_telegram(msg)
        
        # Mise à jour de l'inventaire pour le prochain tour
        current_deals_in_inventory = all_found_now
        
        print(f"[{now}] Rapport : UV {uv_match} deals | Stained {st_match} deals")
        time.sleep(45)

if __name__ == "__main__":
    main()
