import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
HEADERS = {"Authorization": CSFLOAT_API_KEY}

# On définit nos recherches en utilisant la syntaxe que tu as trouvée
RECHERCHES = [
    "Butterfly Knife Ultraviolet <560€ newest", # Filtre prix direct
    "Butterfly Knife Freehand <560€ newest",
    "Butterfly Knife Case Hardened <540€ newest"
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

def run_scan():
    for query in RECHERCHES:
        # On utilise 'full_text' pour envoyer ta syntaxe directement à CSFloat
        params = {
            "limit": 10,
            "full_text": query,
            "sort_by": "most_recent"
        }
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", [])
                print(f"🔎 Recherche : '{query}' -> {len(items)} items trouvés.")
                for item in items:
                    # On garde une petite sécurité is_good_deal au cas où
                    if is_good_deal(item):
                        send_alert(item)
            time.sleep(1.5)
        except Exception as e:
            print(f"⚠️ Erreur sur {query} : {e}")

def is_good_deal(item):
    # Sécurité supplémentaire pour le float de l'Ultraviolet
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    
    # Si c'est un UV Field-Tested, on ne veut que les bons prix ou bons floats
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price <= 515 or (wear <= 0.16 and price <= 580):
            return True
        return False
    return True # Pour les autres, le filtre 'full_text' a déjà fait le travail

def send_alert(item):
    name = item['item']['market_hash_name']
    price = item['price'] / 100
    img = item['item'].get('screenshot', item['item'].get('image'))
    url = f"https://csfloat.com/item/{item['id']}"
    
    msg = (f"🎯 *OFFRE FILTRÉE DÉTECTÉE !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price}€*\n"
           f"📉 *Float :* `{item['item']['float_value']:.5f}`\n\n"
           f"🔗 [VOIR SUR CSFLOAT]({url})")
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})

def main():
    last_msg_id = None
    for i in range(6):
        now = datetime.now().strftime("%H:%M:%S")
        delete_message(last_msg_id)
        last_msg_id = update_status(f"🛰️ *Sniper Expert ON*\nCycle : `{i+1}/6` | `{now}`\nSyntaxe : *Smart Filters*")
        
        run_scan()
        if i < 5:
            time.sleep(40)
    delete_message(last_msg_id)

if __name__ == "__main__":
    main()
