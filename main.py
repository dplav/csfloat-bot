import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
STATUS_MSG_ID = os.getenv("TELEGRAM_STATUS_MSG_ID")

HEADERS = {"Authorization": CSFLOAT_API_KEY}

def update_status(text):
    """Met à jour le message de monitoring ou en crée un nouveau s'il est supprimé"""
    global STATUS_MSG_ID
    
    if not STATUS_MSG_ID or STATUS_MSG_ID == "0":
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        r = requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}).json()
        if r.get("ok"):
            STATUS_MSG_ID = str(r["result"]["message_id"])
            print(f"📢 NOUVEAU STATUS_MSG_ID : {STATUS_MSG_ID} (À mettre dans Railway !)")
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "message_id": STATUS_MSG_ID, "text": text, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload).json()
        # Si le message a été supprimé par l'utilisateur, on en recrée un
        if not r.get("ok"):
            STATUS_MSG_ID = "0"
            update_status(text)

def send_alert(text, image_url=None):
    """Envoie une vraie notification avec vibration"""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        if image_url:
            requests.post(f"{base_url}/sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "Markdown"}, timeout=10)
        else:
            requests.post(f"{base_url}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"Erreur alerte : {e}")

def is_good_deal(item):
    """Critères de sélection ultra-précis"""
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    is_stattrak = "StatTrak" in name

    # 1. Butterfly Ultraviolet
    if "Butterfly Knife | Ultraviolet" in name:
        if "Field-Tested" in name:
            if price <= 515: return True
            if wear <= 0.16 and price <= 580: return True
        if "Minimal Wear" in name and price <= 600: return True # Grosse affaire

    # 2. Butterfly Freehand
    if "Butterfly Knife | Freehand" in name:
        if "Factory New" in name and price <= 600: return True
        if "Minimal Wear" in name and price <= 570: return True

    # 3. Butterfly Case Hardened (Bleu)
    if "Case Hardened" in name:
        # Sniper prix bas
        if price <= 540: return True
        # Blue Gem détecté par l'API
        if item.get("item", {}).get("is_blue_gem", False): return True
                
    return False

def run_scan():
    """Effectue un tour complet du marché"""
    queries = [
        "Butterfly Knife | Ultraviolet",
        "Butterfly Knife | Freehand",
        "Butterfly Knife | Case Hardened"
    ]
    
    found_count = 0
    for q in queries:
        try:
            params = {"limit": 10, "market_hash_name": q, "sort_by": "most_recent"}
            r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
            if r.status_code != 200: continue
            
            items = r.json().get("data", [])
            for item in items:
                if is_good_deal(item):
                    # Alerte
                    name = item['item']['market_hash_name']
                    p_eur = item['price'] / 100
                    img = item['item'].get('screenshot', item['item'].get('image'))
                    msg = (f"🔥 *AFFAIRE TROUVÉE !*\n\n"
                           f"🔪 *{name}*\n"
                           f"💰 *Prix : {p_eur}€*\n"
                           f"📉 *Float :* `{item['item']['float_value']:.5f}`\n\n"
                           f"🔗 [Acheter sur CSFloat](https://csfloat.com/item/{item['id']})")
                    send_alert(msg, image_url=img)
                    found_count += 1
        except Exception as e:
            print(f"Erreur scan {q}: {e}")
    return found_count

def main():
    # On fait 6 scans espacés de 45 secondes pour couvrir les 5 minutes du Cron
    for i in range(6):
        now = datetime.now().strftime("%H:%M:%S")
        update_status(f"🛰️ *Sniper Actif (Cycle {i+1}/6)*\nDernier passage : `{now}`\nStatut : ✅ Surveillance en cours...")
        
        run_scan()
        
        if i < 5: # Attente entre les scans sauf le dernier
            time.sleep(45)

if __name__ == "__main__":
    main()
