import os
import requests
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
STATUS_MSG_ID = os.getenv("TELEGRAM_STATUS_MSG_ID")

HEADERS = {"Authorization": CSFLOAT_API_KEY}

def update_status(text):
    """Édite le message de monitoring unique"""
    if not STATUS_MSG_ID or STATUS_MSG_ID == "0":
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload).json()
        if r.get("ok"):
            m_id = r["result"]["message_id"]
            print(f"📢 MESSAGE DE STATUT CRÉÉ ! ID : {m_id}")
            print(f"👉 AJOUTE CECI DANS RAILWAY : TELEGRAM_STATUS_MSG_ID = {m_id}")
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
        payload = {
            "chat_id": TELEGRAM_CHAT_ID,
            "message_id": STATUS_MSG_ID,
            "text": text,
            "parse_mode": "Markdown"
        }
        requests.post(url, json=payload)

def send_alert(text, image_url=None):
    """Envoie une vraie notification (fait vibrer le téléphone)"""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        if image_url:
            url = f"{base_url}/sendPhoto"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "Markdown"}
        else:
            url = f"{base_url}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur envoi alerte : {e}")

def is_good_deal(item):
    """Logique de filtrage précise"""
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    
    # 1. Butterfly Ultraviolet
    if "Butterfly Knife | Ultraviolet" in name:
        if "Field-Tested" in name:
            if price <= 515 or (wear <= 0.16 and price <= 585): return True
        if "Minimal Wear" in name: # NOUVEAU
            if price <= 600: return True

    # 2. Butterfly Freehand
    if "Butterfly Knife | Freehand" in name:
        if "(Factory New)" in name and price <= 600: return True
        if "(Minimal Wear)" in name and price <= 575: return True

    # 3. Butterfly Case Hardened
    if "Case Hardened" in name:
        if price <= 540: return True
        if item.get("item", {}).get("is_blue_gem", False): return True
                
    return False

def main():
    # Mise à jour de l'heure dans le message de statut
    now = datetime.now().strftime("%H:%M:%S")
    update_status(f"🛰️ *Sniper Actif*\nDernière vérification : `{now}`\nStatut : ✅ Scan en cours...")

    queries = [
        "Butterfly Knife | Ultraviolet",
        "Butterfly Knife | Freehand",
        "Butterfly Knife | Case Hardened"
    ]

    for q in queries:
        try:
            params = {"limit": 10, "market_hash_name": q, "sort_by": "most_recent"}
            r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
            
            if r.status_code != 200: continue
            
            items = r.json().get("data", [])
            for item in items:
                if is_good_deal(item):
                    item_id = item['id']
                    name = item['item']['market_hash_name']
                    price_eur = item['price'] / 100
                    wear = item['item']['float_value']
                    img = item['item'].get('screenshot', item['item'].get('image'))
                    
                    msg = (f"🎯 *AFFAIRE DÉTECTÉE !*\n\n"
                           f"🔪 *{name}*\n"
                           f"💰 *Prix : {price_eur}€*\n"
                           f"📉 *Float :* `{wear:.5f}`\n\n"
                           f"🔗 [Acheter sur CSFloat](https://csfloat.com/item/{item_id})")
                    
                    send_alert(msg, image_url=img)
        except Exception as e:
            print(f"Erreur lors du scan de {q} : {e}")

if __name__ == "__main__":
    main()
