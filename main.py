import os
import requests
import time
import sys
from datetime import datetime

# Force l'affichage des logs immédiatement sur Railway
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"  # Ton ID fixé en dur pour plus de simplicité
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

HEADERS = {"Authorization": CSFLOAT_API_KEY}
# Variable globale pour garder l'ID en mémoire pendant que le bot tourne
CURRENT_MSG_ID = None

def update_status(text):
    """Gère le message de suivi unique sans variable externe"""
    global CURRENT_MSG_ID
    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    
    # Si on n'a pas encore l'ID du message pour ce cycle
    if not CURRENT_MSG_ID:
        url = f"{base_url}/sendMessage"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload).json()
        if r.get("ok"):
            CURRENT_MSG_ID = r["result"]["message_id"]
    else:
        # On essaie d'éditer le message existant
        url = f"{base_url}/editMessageText"
        payload = {"chat_id": TELEGRAM_CHAT_ID, "message_id": CURRENT_MSG_ID, "text": text, "parse_mode": "Markdown"}
        r = requests.post(url, json=payload).json()
        # Si le message a été supprimé, on en crée un nouveau au prochain tour
        if not r.get("ok"):
            CURRENT_MSG_ID = None
            update_status(text)

def send_alert(text, image_url=None):
    """Envoie une alerte qui fait vibrer le téléphone"""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    try:
        if image_url:
            requests.post(f"{base_url}/sendPhoto", json={"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "Markdown"}, timeout=10)
        else:
            requests.post(f"{base_url}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
    except Exception as e:
        print(f"❌ Erreur envoi alerte : {e}")

def is_good_deal(item):
    """Ta stratégie de prix personnalisée"""
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    
    # 1. Butterfly Ultraviolet
    if "Butterfly Knife | Ultraviolet" in name:
        if "Field-Tested" in name and price <= 515: return True
        if "Field-Tested" in name and wear <= 0.16 and price <= 580: return True
        if "Minimal Wear" in name and price <= 600: return True

    # 2. Butterfly Freehand
    if "Butterfly Knife | Freehand" in name:
        if "Factory New" in name and price <= 600: return True
        if "Minimal Wear" in name and price <= 570: return True

    # 3. Butterfly Case Hardened
    if "Case Hardened" in name:
        if price <= 540: return True
        if item.get("item", {}).get("is_blue_gem", False): return True
                
    return False

def run_scan():
    """Scan des 30 derniers items par skin"""
    queries = [
        "Butterfly Knife | Ultraviolet",
        "Butterfly Knife | Freehand",
        "Butterfly Knife | Case Hardened"
    ]
    
    for q in queries:
        try:
            # Limite à 30 pour couvrir les pauses du bot
            params = {"limit": 30, "market_hash_name": q, "sort_by": "most_recent"}
            r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
            
            if r.status_code == 200:
                items = r.json().get("data", [])
                print(f"🔎 {q} : {len(items)} items vérifiés.")
                for item in items:
                    if is_good_deal(item):
                        msg = (f"🔥 *AFFAIRE TROUVÉE !*\n\n"
                               f"🔪 *{item['item']['market_hash_name']}*\n"
                               f"💰 *Prix : {item['price']/100}€*\n"
                               f"📉 *Float :* `{item['item']['float_value']:.5f}`\n\n"
                               f"🔗 [Acheter sur CSFloat](https://csfloat.com/item/{item['id']})")
                        img = item['item'].get('screenshot', item['item'].get('image'))
                        send_alert(msg, image_url=img)
        except Exception as e:
            print(f"⚠️ Erreur sur {q} : {e}")

def main():
    print("🚀 Démarrage du cycle de scan...")
    # 6 répétitions de 45 secondes = ~4min30 d'activité par réveil Railway
    for i in range(6):
        now = datetime.now().strftime("%H:%M:%S")
        update_status(f"🛰️ *Sniper Butterfly en ligne*\n🔄 Scan cycle : `{i+1}/6`\n🕒 Dernier passage : `{now}`\n✅ Statut : Surveillance active")
        
        run_scan()
        
        if i < 5:
            time.sleep(45)
    print("💤 Fin du cycle, mise en veille jusqu'au prochain Cron.")

if __name__ == "__main__":
    main()
