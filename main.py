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

# Mémoire du bot pour ne pas envoyer 100 fois le même couteau
seen_items = set()

def is_good_deal(name, price_eur, wear):
    """Vérification stricte de tes critères + tolérance 5€"""
    if "Field-Tested" not in name:
        return False
    
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    
    # CRITÈRES UV : 525€ (Base) ou 585€ (si float < 0.16)
    if is_uv:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    
    # CRITÈRES STAINED : 550€
    if is_stained:
        if price_eur <= 550: return True
        
    return False

def scan_target(skin_name):
    """Scanne 50 annonces et filtre selon tes critères"""
    headers = {"Authorization": CSFLOAT_API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # On prend les 50 moins chers pour être sûr de voir tout ce qui est dans ton budget
    url = f"https://csfloat.com/api/v1/listings?limit=50&sort_by=lowest_price&full_text=Butterfly Knife {skin_name}"
    
    try:
        r = requests.get(url, headers=headers, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            in_criteria = 0
            
            for i in items:
                item_id = i['id']
                item_data = i.get('item', {})
                name = item_data.get('market_hash_name', '')
                
                # On ne traite que si c'est le bon skin
                if skin_name in name:
                    price = i['price'] / 100
                    wear = item_data.get('float_value', 0.0)
                    
                    if is_good_deal(name, price, wear):
                        in_criteria += 1
                        # Alerte seulement si on ne l'a pas déjà vu
                        if item_id not in seen_items:
                            send_alert(name, price, wear, f"https://csfloat.com/item/{item_id}", "CSFLOAT")
                            seen_items.add(item_id)
            
            return len(items), in_criteria
        else:
            print(f"❌ Erreur API {skin_name}: {r.status_code}")
            return 0, 0
    except Exception as e:
        print(f"⚠️ Erreur technique {skin_name}: {e}")
        return 0, 0

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *NOUVELLE OFFRE {source} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper v16.0 (Mémoire intelligente + Critères FT)")
    
    while True:
        now = datetime.now().strftime('%H:%M:%S')
        
        # Scan des deux catégories
        uv_total, uv_match = scan_target("Ultraviolet")
        st_total, st_match = scan_target("Stained")
        
        print(f"[{now}] Rapport :")
        print(f"   🔹 UV      : {uv_total} vus | {uv_match} correspondent à tes critères")
        print(f"   🔹 Stained : {st_total} vus | {st_match} correspondent à tes critères")
        
        # Nettoyage de la mémoire si elle devient trop grosse (optionnel)
        if len(seen_items) > 1000:
            seen_items.clear()
            
        time.sleep(45) # Fréquence de scan

if __name__ == "__main__":
    main()
