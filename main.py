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
    # 1. ULTRAVIOLET FT (Max 530€ / Float <= 0.24)
    if "Ultraviolet" in name and "Field-Tested" in name:
        return price_eur <= 530 and wear <= 0.24

    # 2. STAINED WW (Max 490€)
    if "Stained" in name and "Well-Worn" in name:
        return price_eur <= 490

    # 3. TEST HUNTSMAN FN (On le garde encore pour voir la photo)
    if "Huntsman Knife" in name and "Doppler" in name and "Factory New" in name:
        return True
            
    return False

def get_market_data(full_hash_name):
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    params = {"limit": 20, "sort_by": "lowest_price", "market_hash_name": full_hash_name}
    
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
                
                # Récupération de l'image (screenshot CSFloat)
                image_url = i.get('screenshot_url') or item_data.get('icon_url')

                if is_good_deal(name, price, wear):
                    found_deals[item_id] = f"{name} ({price}€)"
                    if item_id not in seen_items:
                        send_telegram_with_photo(name, price, wear, item_id, image_url)
                        seen_items.add(item_id)
            return found_deals, total_count
        return {}, 0
    except: return {}, 0

def send_telegram_with_photo(name, price, wear, item_id, image_url):
    url = f"https://csfloat.com/item/{item_id}"
    caption = (f"🎯 *OFFRE DÉTECTÉE !*\n\n"
               f"🔪 *{name}*\n"
               f"💰 *Prix : {price:.2f}€*\n"
               f"📉 *Float :* `{wear:.5f}`\n\n"
               f"🔗 [OUVRIR SUR CSFLOAT]({url})")
    
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "caption": caption,
        "parse_mode": "Markdown",
        "photo": image_url if image_url else "https://community.cloudflare.steamstatic.com/economy/image/fWFc82js0fmoRAP-q6dfLQ--cyasH5mT95S7mVBv8G6l6VvPAn48-LswT9-rU-V_FA_uY-9BicS4Ff6DDeI_lsE9stYAl2RtkVQqZ7vmsmY1JFOTDqVfW_0_pA3tG3Z86p8zANHio-oFfFq64teSM7Z-No4fS8SFC_SMMV_4708xhaVfLpKA9Xvn3S3uJC5YRRtgqYpP"
    }
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", json=payload)

def update_dashboard(text, message_id):
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "message_id": message_id, "text": text, "parse_mode": "Markdown"})

def main():
    global current_deals_inventory, dashboard_message_id
    print("🚀 Sniper v28.0 (Photos activées)")
    
    # On envoie un message simple pour créer le dashboard
    r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": "⏳ Initialisation du Dashboard..."})
    dashboard_message_id = r.json().get("result", {}).get("message_id")
    
    while True:
        now_str = datetime.now().strftime('%H:%M:%S')
        uv_deals, uv_tot = get_market_data("★ Butterfly Knife | Ultraviolet (Field-Tested)")
        st_deals, st_tot = get_market_data("★ Butterfly Knife | Stained (Well-Worn)")
        ht_deals, ht_tot = get_market_data("★ Huntsman Knife | Doppler (Factory New)")
        
        all_deals_now = {**uv_deals, **st_deals, **ht_deals}
        
        # Dashboard
        report = (f"🖥️ *DASHBOARD SNIPER*\n"
                  f"🕒 `{now_str}`\n"
                  f"--- \n"
                  f"🟣 *UV FT (<0.24)* : `{uv_tot}` en ligne\n"
                  f"🔵 *Stained WW* : `{st_tot}` en ligne\n"
                  f"🗡️ *TEST: Huntsman Doppler FN* : `{ht_tot}` trouvé\n\n"
                  f"📸 Les alertes incluent désormais la photo.")
        
        update_dashboard(report, dashboard_message_id)
        current_deals_inventory = all_deals_now
        time.sleep(45)

if __name__ == "__main__":
    main()
