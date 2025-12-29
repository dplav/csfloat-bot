import os
import requests
import time
import sys
from datetime import datetime

# Force l'affichage des logs
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

USD_TO_EUR = 0.95

def is_good_deal(name, price_eur, wear):
    # On vérifie que c'est bien un Butterfly Knife et qu'il est FT
    if "Field-Tested" not in name:
        return False
        
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    
    # Seuils avec tolérance +5€
    if is_uv:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    if is_stained:
        if price_eur <= 550: return True
    return False

def scan_csfloat():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan CSFloat (Turbo 100 items)...")
    headers = {"Authorization": CSFLOAT_API_KEY.strip() if CSFLOAT_API_KEY else ""}
    
    # On augmente la limite à 100 pour balayer plus large
    params = {
        "limit": 100, 
        "full_text": "Butterfly Knife",
        "sort_by": "most_recent"
    }
    
    try:
        r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            count, deals = 0, 0
            found_names = []
            
            for i in items:
                name = i['item']['market_hash_name']
                if "Ultraviolet" in name or "Stained" in name:
                    count += 1
                    price = i['price'] / 100
                    wear = i['item'].get('float_value', 0.0)
                    
                    # On garde trace de ce qu'on a vu pour les logs
                    found_names.append(f"{name.replace('Butterfly Knife | ', '')} ({price:.0f}€)")
                    
                    if is_good_deal(name, price, wear):
                        deals += 1
                        send_alert(name, price, wear, f"https://csfloat.com/item/{i['id']}", "CSFloat")
            
            # Affichage des skins cibles trouvés dans le scan actuel
            if found_names:
                print(f"   └─ 👀 Vus : {', '.join(list(set(found_names)))}")
            
            print(f"   └─ ✅ {len(items)} Butterfly scannés | {count} cibles trouvées | {deals} deal")
        else:
            print(f"❌ CSFloat Error {r.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur CSFloat: {e}")

def send_alert(name, price, wear, url, source):
    print(f"🎯 ALERTE ENVOYÉE : {name} à {price}€")
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper v11.0 (CSFloat Turbo Mode)")
    print("Cibles : UV FT (<=525€ ou <=585€ si float <0.16) | Stained FT (<=550€)")
    while True:
        scan_csfloat()
        # On réduit l'attente à 30 secondes pour être plus réactif
        time.sleep(30)

if __name__ == "__main__":
    main()
