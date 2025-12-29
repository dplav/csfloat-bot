import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
# .strip() est vital pour éviter d'envoyer un espace dans l'en-tête Authorization
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY").strip() if os.getenv("CSFLOAT_API_KEY") else ""

def is_good_deal(name, price_eur, wear):
    if "Field-Tested" not in name:
        return False
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    if is_uv:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    if is_stained:
        if price_eur <= 550: return True
    return False

def scan_csfloat():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan CSFloat (URL Directe)...")
    
    headers = {
        "Authorization": CSFLOAT_API_KEY,
        "User-Agent": "Mozilla/5.0" # Ajout d'un User-Agent pour éviter le blocage
    }
    
    # URL brute avec les filtres déjà encodés (Butterfly + Most Recent + Limit 50)
    url = "https://csfloat.com/api/v1/listings?limit=50&sort_by=most_recent&type=butterfly_knife"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            # Si le JSON est dans une clé 'data'
            items = data.get("data", data) if isinstance(data, dict) else data
            
            count, deals = 0, 0
            for i in items:
                try:
                    name = i['item']['market_hash_name']
                    if "Ultraviolet" in name or "Stained" in name:
                        count += 1
                        price = i['price'] / 100
                        wear = i['item'].get('float_value', 0.0)
                        if is_good_deal(name, price, wear):
                            deals += 1
                            send_alert(name, price, wear, f"https://csfloat.com/item/{i['id']}", "CSFloat")
                except KeyError:
                    continue
            print(f"   └─ ✅ {len(items)} items reçus | {count} cibles analysées | {deals} deal")
        
        elif r.status_code == 401:
            print("❌ Erreur 401 : Ta clé API CSFloat est invalide ou mal copiée.")
        else:
            print(f"❌ CSFloat Error {r.status_code}: {r.text[:100]}")
            
    except Exception as e:
        print(f"⚠️ Erreur technique : {e}")

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *ALERTE {source} !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper v12.0 (Mode URL Directe)")
    while True:
        scan_csfloat()
        time.sleep(35)

if __name__ == "__main__":
    main()
