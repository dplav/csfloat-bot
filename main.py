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

# Syntaxe optimisée basée sur tes recherches
RECHERCHES = [
    "Butterfly Knife Ultraviolet <560€ newest",
    "Butterfly Knife Freehand <560€ newest",
    "Butterfly Knife Case Hardened <540€ newest",
    "Butterfly Knife Case Hardened >25% newest" # Spécial Blue Gem
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
    """Vérification sécurisée pour éviter l'erreur float_value"""
    # On récupère les infos de manière sécurisée
    item_data = item.get("item", {})
    name = item_data.get("market_hash_name", "")
    price = item.get("price", 0) / 100
    
    # Correction de l'erreur : on utilise .get() avec 0.0 par défaut
    wear = item_data.get("float_value")
    if wear is None:
        wear = 0.0  # Valeur par défaut si absent
    
    # Filtre spécifique Ultraviolet FT (car le float compte beaucoup ici)
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price <= 515 or (wear <= 0.16 and price <= 580):
            return True
        return False
        
    # Pour les autres, si l'API l'a trouvé via full_text, c'est que c'est bon
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
                print(f"🔎 {query} : {len(items)} items.")
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
    
    # Ajout du pourcentage de bleu dans l'alerte si disponible
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
        last_msg_id = update_status(f"🛰️ *Sniper Expert Pro*\nCycle : `{i+1}/6` | `{now}`\nStatut : ✅ Scan intelligent")
        
        run_scan()
        if i < 5:
            time.sleep(40)
    delete_message(last_msg_id)

if __name__ == "__main__":
    main()
