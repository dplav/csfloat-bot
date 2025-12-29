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

# Les skins que tu acceptes
SKINS_INTERESSANTS = ["Ultraviolet", "Freehand", "Case Hardened"]

def update_status(text):
    """Envoie un message de suivi silencieux"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown", 
        "disable_notification": True
    }
    return requests.post(url, json=payload).json().get("result", {}).get("message_id")

def delete_message(msg_id):
    """Supprime l'ancien message de statut pour garder le chat propre"""
    if msg_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id})

def is_good_deal(item):
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    
    # On ne garde que tes 3 skins
    if not any(s in name for s in SKINS_INTERESSANTS):
        return False

    # Logique de prix
    if "Ultraviolet" in name:
        if "Field-Tested" in name and (price <= 515 or (wear <= 0.16 and price <= 580)): return True
        if "Minimal Wear" in name and price <= 600: return True

    if "Freehand" in name:
        if "Factory New" in name and price <= 600: return True
        if "Minimal Wear" in name and price <= 570: return True

    if "Case Hardened" in name:
        if price <= 540 or item.get("item", {}).get("is_blue_gem", False): return True
                
    return False

def run_scan():
    # On récupère les 50 derniers Butterfly du marché
    params = {
        "limit": 50, 
        "market_hash_name": "Butterfly Knife",
        "sort_by": "most_recent"
    }
    try:
        r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
        if r.status_code == 200:
            items = r.json().get("data", [])
            # On filtre pour les logs
            targets = [i for i in items if any(s in i['item']['market_hash_name'] for s in SKINS_INTERESSANTS)]
            print(f"🔎 {len(targets)} Butterfly (UV/Freehand/CH) trouvés sur les 50 derniers mis en ligne.")
            
            for item in items:
                if is_good_deal(item):
                    send_alert(item)
        else:
            print(f"❌ Erreur API : {r.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur : {e}")

def send_alert(item):
    name = item['item']['market_hash_name']
    price = item['price'] / 100
    img = item['item'].get('screenshot', item['item'].get('image'))
    url = f"https://csfloat.com/item/{item['id']}"
    
    msg = (f"🎯 *AUBAINE DÉTECTÉE !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price}€*\n"
           f"📉 *Float :* `{item['item']['float_value']:.5f}`\n\n"
           f"🔗 [VOIR SUR CSFLOAT]({url})")
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})

def main():
    last_msg_id = None
    for i in range(5):
        now = datetime.now().strftime("%H:%M:%S")
        
        # Supprime l'ancien message de statut et envoie le nouveau
        delete_message(last_msg_id)
        last_msg_id = update_status(f"🛰️ *Sniper en cours...*\nCycle : `{i+1}/5` | Heure : `{now}`\nCibles : UV, Freehand, CH")
        
        run_scan()
        if i < 4:
            time.sleep(55)
    
    # Nettoyage final pour ne pas laisser de traces
    delete_message(last_msg_id)

if __name__ == "__main__":
    main()
