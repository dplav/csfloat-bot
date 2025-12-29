import os
import requests
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
# Cette variable est optionnelle au début
STATUS_MSG_ID = os.getenv("TELEGRAM_STATUS_MSG_ID")

def update_status(text):
    """Édite le message de monitoring pour montrer que le bot tourne"""
    if not STATUS_MSG_ID:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload).json()
        if r.get("ok"):
            m_id = r["result"]["message_id"]
            print(f"\n📢 PREMIER LANCEMENT RÉUSSI !")
            print(f"👉 AJOUTE CETTE VARIABLE SUR RAILWAY : TELEGRAM_STATUS_MSG_ID = {m_id}")
            print(f"Sans cela, le bot créera un nouveau message à chaque fois.\n")
    else:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "message_id": STATUS_MSG_ID, "text": text, "parse_mode": "Markdown"}
        requests.post(url, json=payload)

def send_real_alert(text, image_url=None):
    """CETTE fonction fait vibrer ton téléphone (vraie alerte)"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/"
    if image_url:
        requests.post(url + "sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "Markdown"})
    else:
        requests.post(url + "sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})

def is_good_deal(item):
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    if price > 600: return False
    # Tes critères
    if "Ultraviolet" in name and price <= 515: return True
    if "Freehand" in name and price <= 590: return True
    if "Case Hardened" in name and (price <= 540 or item.get("item", {}).get("is_blue_gem", False)): return True
    return False

def main():
    # 1. Mise à jour du statut (Silencieux)
    now = datetime.now().strftime("%d/%m %H:%M")
    update_status(f"🛰️ *Bot en veille...*\nDernier scan : `{now}`\nStatut : ✅ Actif")

    # 2. Scan des items
    queries = ["Butterfly Knife | Ultraviolet", "Butterfly Knife | Freehand", "Butterfly Knife | Case Hardened"]
    headers = {"Authorization": CSFLOAT_API_KEY}
    
    for q in queries:
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params={"limit": 10, "market_hash_name": q, "sort_by": "most_recent"}, timeout=10)
            items = r.json().get("data", [])
            for item in items:
                if is_good_deal(item):
                    img = item['item'].get('screenshot', item['item'].get('image'))
                    msg = f"🔥 *AFFAIRE TROUVÉE !*\n\n🔪 {item['item']['market_hash_name']}\n💰 *{item['price']/100}€*\n🔗 [Lien CSFloat](https://csfloat.com/item/{item['id']})"
                    send_real_alert(msg, image_url=img)
        except:
            pass

if __name__ == "__main__":
    main()
