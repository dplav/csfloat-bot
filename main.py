import os
import requests
import time
import sys
from datetime import datetime

# Force l'affichage des logs immédiatement sur Railway
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
# Assure-toi que ces lignes sont bien alignées tout à gauche
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
HEADERS = {"Authorization": CSFLOAT_API_KEY}

# Configuration des cibles avec leurs IDs techniques
CIBLES = {
    "Ultraviolet": {"id": 98},
    "Freehand": {"id": 588},
    "Case Hardened": {"id": 44}
}

def update_status(text):
    """Envoie un message de suivi silencieux"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown", 
        "disable_notification": True
    }
    r = requests.post(url, json=payload).json()
    return r.get("result", {}).get("message_id")

def delete_message(msg_id):
    """Supprime l'ancien message de statut"""
    if msg_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id})

def is_good_deal(item):
    """Vérification précise des prix et de l'usure"""
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    
    # 1. Butterfly Ultraviolet
    if "Ultraviolet" in name:
        if "Field-Tested" in name:
            if price <= 515 or (wear <= 0.16 and price <= 580): return True
        if "Minimal Wear" in name and price <= 600: return True

    # 2. Butterfly Freehand
    if "Freehand" in name:
        if "Factory New" in name and price <= 600: return True
        if "Minimal Wear" in name and price <= 570: return True

    # 3. Butterfly Case Hardened
    if "Case Hardened" in name:
        if price <= 540: return True
        if item.get("item", {}).get("is_blue_gem", False): return True
                
    return False

def run_scan():
    """Scan par skin pour une précision maximale"""
    for nom, config in CIBLES.items():
        params = {
            "limit": 20,
            "defindex": 507,
            "paint_index": config["id"],
            "sort_by": "most_recent"
        }
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", [])
                print(f"🔎 {nom} : {len(items)} items vérifiés.")
                for item in items:
                    if is_good_deal(item):
                        send_alert(item)
            else:
                print(f"❌ Erreur API sur {nom} : {r.status_code}")
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Erreur lors du scan de {nom} : {e}")

def send_alert(item):
    """Envoie l'alerte avec photo et lien direct"""
    name = item['item']['market_hash_name']
    price = item['price'] / 100
    img = item['item'].get('screenshot', item['item'].get('image'))
    url = f"https://csfloat.com/item/{item['id']}"
    
    msg = (f"🎯 *AUBAINE DÉTECTÉE !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price}€*\n"
           f"📉 *Float :* `{item['item']['float_value']:.5f}`\n\n"
           f"🔗 [ACHETER SUR CSFLOAT]({url})")
    
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "photo": img, "caption": msg, "parse_mode": "Markdown"})

def main():
    last_msg_id = None
    # 6 cycles de ~45 secondes pour couvrir le créneau Railway
    for i in range(6):
        now = datetime.now().strftime("%H:%M:%S")
        
        # Mise à jour du message de suivi
        delete_message(last_msg_id)
        last_msg_id = update_status(f"🛰️ *Sniper Précision ON*\nCycle : `{i+1}/6` | `{now}`\nCibles : UV, Freehand, CH")
        
        run_scan()
        
        if i < 5:
            time.sleep(40)
    
    # Nettoyage final
    delete_message(last_msg_id)

if __name__ == "__main__":
    main()
