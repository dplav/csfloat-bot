import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

seen_items = set()

def get_market_data():
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # --- SKIN DE TEST : FREEHAND FT ---
    target_name = "★ Butterfly Knife | Freehand (Field-Tested)"
    url = f"https://csfloat.com/api/v1/listings?market_hash_name={target_name}&limit=5&sort_by=lowest_price"
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            items = r.json().get("data", [])
            for i in items:
                item_id = i['id']
                if item_id not in seen_items:
                    price = i['price'] / 100
                    wear = i.get('item', {}).get('float_value', 0)
                    
                    # On envoie l'alerte pour TOUS les Freehand trouvés pour tester la vitesse
                    send_urgent_alert(target_name, price, wear, item_id, i.get('screenshot_url'))
                    seen_items.add(item_id)
    except Exception as e:
        print(f"Erreur : {e}")

def send_urgent_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    
    # Le texte commence par des emojis d'alerte pour attirer l'attention
    msg = (f"🔔 🚨 *ALERTE PRIORITAIRE* 🚨 🔔\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🚀 [ACHETER MAINTENANT]({url})")
    
    try:
        # On envoie le message sans le mode silencieux pour qu'il sonne
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={
                          "chat_id": TELEGRAM_CHAT_ID, 
                          "text": msg, 
                          "parse_mode": "Markdown",
                          "disable_notification": False # Force la notification sonore
                      })
    except: pass

def main():
    print("🚀 Sniper v44.0 (Test Freehand - Alerte Sonore)")
    
    # Message de confirmation de lancement
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔊 Mode TEST FREEHAND activé. Vérifie que le son de ton Telegram est au max !"})
    
    while True:
        get_market_data()
        time.sleep(20) # Scan très rapide (20 sec) pour le test

if __name__ == "__main__":
    main()
