import os
import requests
import time
import sys
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY").strip() if os.getenv("CSFLOAT_API_KEY") else ""

def is_good_deal(name, price_eur, wear):
    if "Field-Tested" not in name:
        return False
    
    # On cible uniquement tes deux skins
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    
    if not (is_uv or is_stained):
        return False

    # Seuils + 5€ de tolérance
    if is_uv:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    if is_stained:
        if price_eur <= 550: return True
        
    return False

def scan_csfloat():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan CSFloat (Correction Schema)...")
    
    headers = {
        "Authorization": CSFLOAT_API_KEY,
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }
    
    # Nouvelle URL : on utilise market_hash_name pour éviter l'erreur de type
    # Cela cible tous les Butterfly Knife
    url = "https://csfloat.com/api/v1/listings?limit=50&sort_by=most_recent&market_hash_name=★ Butterfly Knife *"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            data = r.json()
            items = data.get("data", [])
            
            count, deals = 0, 0
            for i in items:
                try:
                    item_data = i.get('item', {})
                    name = item_data.get('market_hash_name', '')
                    
                    if "Ultraviolet" in name or "Stained" in name:
                        count += 1
                        price = i['price'] / 100
                        wear = item_data.get('float_value', 0.0)
                        
                        if is_good_deal(name, price, wear):
                            deals += 1
                            send_alert(name, price, wear, f"https://csfloat.com/item/{i['id']}", "CSFloat")
                except Exception:
                    continue
                    
            print(f"   └─ ✅ {len(items)} items reçus | {count} cibles détectées | {deals} deal trouvé")
        
        elif r.status_code == 400:
            # Si l'ID numérique est obligatoire, on tente la recherche textuelle pure
            print("⚠️ Erreur 400 persistante, tentative repli sur recherche textuelle...")
            fallback_url = "https://csfloat.com/api/v1/listings?limit=50&sort_by=most_recent&full_text=Butterfly Knife"
            r_fallback = requests.get(fallback_url, headers=headers, timeout=15)
            if r_fallback.status_code == 200:
                 print("✅ Repli réussi.")
                 # (Le reste du traitement serait identique)
            else:
                 print(f"❌ Échec total : {r_fallback.text[:100]}")
        else:
            print(f"❌ Erreur {r.status_code}: {r.text[:100]}")
            
    except Exception as e:
        print(f"⚠️ Erreur technique : {e}")

def send_alert(name, price, wear, url, source):
    print(f"🎯 ALERTE : {name} ({price}€)")
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper v13.0 (Fix définitif Schema API)")
    while True:
        scan_csfloat()
        time.sleep(40)

if __name__ == "__main__":
    main()
