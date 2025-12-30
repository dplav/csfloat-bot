import os
import requests
import time
import sys
from datetime import datetime

# Assure que les logs s'affichent en temps réel sur Railway
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
# Nettoyage de la clé API au cas où
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Liste pour ne pas envoyer deux fois le même couteau
seen_items = set()

def get_market_data():
    headers = {
        "Authorization": API_KEY, 
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # --- TEST SUR LE SKIN FREEHAND (Très actif pour tester le son) ---
    target_name = "★ Butterfly Knife | Freehand (Field-Tested)"
    url = f"https://csfloat.com/api/v1/listings?market_hash_name={target_name}&limit=5&sort_by=lowest_price"
    
    try:
        r = requests.get(url, headers=headers, timeout=10)
        
        if r.status_code == 200:
            items = r.json().get("data", [])
            print(f"[{datetime.now().strftime('%H:%M:%S')}] Scan effectué : {len(items)} items trouvés.")
            
            for i in items:
                item_id = i['id']
                if item_id not in seen_items:
                    item_info = i.get('item', {})
                    price = i['price'] / 100
                    wear = item_info.get('float_value', 0)
                    img = i.get('screenshot_url') or item_info.get('icon_url')
                    
                    # ENVOI DE L'ALERTE DOUBLE
                    send_urgent_alert(target_name, price, wear, item_id, img)
                    seen_items.add(item_id)
        else:
            print(f"Erreur API: Status {r.status_code}")
            
    except Exception as e:
        print(f"Erreur de connexion : {e}")

def send_urgent_alert(name, price, wear, item_id, img):
    url = f"https://csfloat.com/item/{item_id}"
    
    # Message principal avec détails
    msg = (f"🔔 🚨 *ALERTE PRIORITAIRE* 🚨 🔔\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🚀 [ACHETER MAINTENANT]({url})")
    
    try:
        # 1. Envoi de la Photo (déclenche la 1ère notification)
        if img:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendPhoto", 
                          json={
                              "chat_id": TELEGRAM_CHAT_ID, 
                              "photo": img, 
                              "caption": msg, 
                              "parse_mode": "Markdown",
                              "disable_notification": False
                          }, timeout=10)
        else:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                          json={
                              "chat_id": TELEGRAM_CHAT_ID, 
                              "text": msg, 
                              "parse_mode": "Markdown",
                              "disable_notification": False
                          }, timeout=10)
        
        # 2. Envoi d'un second message texte flash (déclenche la 2ème notification immédiate)
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={
                          "chat_id": TELEGRAM_CHAT_ID, 
                          "text": "⚠️ **VITE ! UNE OFFRE VIENT DE TOMBER !** ⚠️", 
                          "parse_mode": "Markdown",
                          "disable_notification": False 
                      }, timeout=10)
        
        print(f"Alerte envoyée pour l'item {item_id}")
    except Exception as e:
        print(f"Erreur lors de l'envoi Telegram : {e}")

def main():
    print("🚀 Sniper v44.1 démarré (Test Freehand + Double Son)")
    
    # Message de confirmation au lancement
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": "🔊 Sniper v44.1 Actif.\nTest en cours sur : Butterfly Freehand.\nVérifie ton volume !"})
    
    while True:
        get_market_data()
        # Scan toutes le 20 secondes pour une réactivité maximale
        time.sleep(20)

if __name__ == "__main__":
    main()
