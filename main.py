import os
import requests
import time
import sys
from datetime import datetime

# Force l'affichage des logs immédiatement sur Railway
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
HEADERS = {"Authorization": CSFLOAT_API_KEY}

# Syntaxe optimisée incluant le nouveau Butterfly Stained
RECHERCHES = [
    "Butterfly Knife Ultraviolet <560€ newest",
    "Butterfly Knife Freehand <560€ newest",
    "Butterfly Knife Case Hardened <540€ newest",
    "Butterfly Knife Case Hardened >25% newest",
    "Butterfly Knife Stained <545€ newest"  # Nouvelle recherche pour le Stained
]

def update_status(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_notification": True}
    r = requests.post(url, json=payload).json()
    return r.get("result", {}).get("message_id")

def delete_message(msg_id):
    if msg_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id})

def is_good_deal(item):
    """Vérification précise des prix et du float (incluant le Stained)"""
    item_data = item.get("item", {})
    name = item_data.get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item_data.get("float_value", 0.0)
    
    # 1. Butterfly Ultraviolet
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price <= 515 or (wear <= 0.16 and price <= 580):
            return True
        return False

    # 2. Butterfly Stained (Tes nouveaux critères)
    if "Stained" in name:
        # On vérifie si c'est bien un Field-Tested avec float < 0.30
        if "Field-Tested" in name:
            if price <= 545 and wear <= 0.30:
                return True
        return False
        
    # Pour Freehand et Case Hardened, les filtres de la recherche suffisent
    return True

def run_scan():
    for query in RECHERCHES:
        params = {
            "limit": 15,
            "full_text": query,
            "sort_by": "most_recent"
        }
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", [])
                print(f"🔎 {query} : {len(items)} items analysés.")
                for item in items:
                    if is_good_deal(item):
                        send_alert(item)
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ Erreur sur {query} : {e}")

def send_alert(item):
    item_data = item.get("item", {})
    name = item_data.get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item_data.get("float_value", 0.0)
    img = item_data.get('screenshot', item_data.get('image'))
    url = f"https://csfloat.com/item/{item['id']}"
    
    blue = item_data.get("blue_gem_percentage")
    blue_str = f"💎 *Bleu :* `{blue}%`" if blue else ""

    msg = (f"🎯 *OFFRE DÉTECTÉE !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n"
           f"{blue_str}\n\n"
           f"🔗 [VOIR SUR CSFLOAT]({url})")
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})

def main():
    last_msg_id = None
    for i in range(6):
        now = datetime.now().strftime("%H:%M:%S")
        delete_message(last_msg_id)
        last_msg_id = update_status(f"🛰️ *Sniper Expert Pro*\nCycle : `{i+1}/6` | `{now}`\nCibles : UV, Freehand, CH, Stained")
        
        run_scan()
        if i < 5:
            time.sleep(40)
    delete_message(last_msg_id)

if __name__ == "__main__":
    main()
