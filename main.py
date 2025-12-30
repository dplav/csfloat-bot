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
    # ULTRAVIOLET FT : Max 565€ et Float <= 0.24
    if "Ultraviolet" in name and "Field-Tested" in name:
        return price_eur <= 565.99 and wear <= 0.2409
    # STAINED : Max 550€
    if "Stained" in name:
        return price_eur <= 550.99
    return False

def scan_specific_category(skin_name):
    """Demande spécifiquement 100 exemplaires de ce skin précis au serveur"""
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    # On utilise 'category=1' pour Butterfly et 'market_hash_name' pour filtrer AVANT l'envoi
    url = f"https://csfloat.com/api/v1/listings?limit=100&sort_by=lowest_price&type=butterfly_knife&market_hash_name=★ Butterfly Knife | {skin_name} (Field-Tested)"
    
    # Pour le Stained, on élargit si besoin
    if skin_name == "Stained":
        url = f"https://csfloat.com/api/v1/listings?limit=100&sort_by=lowest_price&type=butterfly_knife&market_hash_name=★ Butterfly Knife | Stained"

    found_deals = {}
    total_on_market = 0
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                total_on_market += 1
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
            return found_deals, total_on_market
        return {}, 0
    except: return {}, 0

def send_alert(name, price, wear, item_id, img_url):
    url = f"https://csfloat.com/item/{item_id}"
    caption = (f"🎯 *OFFRE DÉTECTÉE !*\n\n🔪 *{name}*\n💰 *Prix : {price:.2f}€*\n📉 *Float :* `{wear:.5f}`\n\n🔗 [VOIR SUR CSFLOAT]({url})")
    try:
        if img_url:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": img_url, "caption": caption, "parse_mode": "Markdown"}, timeout=10)
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"}, timeout=10)
    except:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": caption, "parse_mode": "Markdown"}, timeout=10)

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v35.0 (Ciblage Double Canal)")
    
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔄 Activation du Scan Double Canal..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        
        # Requête 1 : Uniquement les UV
        uv_deals, uv_t = scan_specific_category("Ultraviolet")
        # Requête 2 : Uniquement les Stained
        st_deals, st_t = scan_specific_category("Stained")
        
        all_deals_now = {**uv_deals, **st_deals}
        
        report = (f"🖥️ *DASHBOARD SNIPER BFK*\n🕒 *Dernier scan :* `{now_str}`\n--- \n"
                  f"🟣 *UV FT (Max 565€ / Fl < 0.24)*\n    └ En ligne : `{uv_t}` | Deals : `{len(uv_deals)}` \n\n"
                  f"🔵 *Stained (Max 550€)*\n    └ En ligne : `{st_t}` | Deals : `{len(st_d)}` \n\n"
                  f"🛰️ *Status :* `Scan Double Canal (200 items)`")
        
        try:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", json={"chat_id": TELEGRAM_CHAT_ID, "message_id": dashboard_message_id, "text": report, "parse_mode": "Markdown"})
        except: pass
        
        current_deals_inventory = all_deals_now
        time.sleep(30)

if __name__ == "__main__":
    main()
