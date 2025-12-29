import os
import requests
import time
import sys
import nacl.signing
from datetime import datetime

# Force l'affichage des logs
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
DMARKET_PUB = os.getenv("DMARKET_PUBLIC_KEY")
DMARKET_SEC = os.getenv("DMARKET_SECRET_KEY")

USD_TO_EUR = 0.95

def is_good_deal(name, price_eur, wear):
    """Vérifie les critères avec tolérance +5€"""
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    
    if not (is_uv or is_stained) or "Field-Tested" not in name:
        return False

    # Ultraviolet : 520€ + 5€ = 525€ | Low Float : 580€ + 5€ = 585€
    if is_uv:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    
    # Stained : 545€ + 5€ = 550€
    if is_stained:
        if price_eur <= 550: return True
        
    return False

def scan_csfloat():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan CSFloat (Top 50 Butterfly)...")
    headers = {"Authorization": CSFLOAT_API_KEY.strip() if CSFLOAT_API_KEY else ""}
    
    # On scanne les 50 derniers Butterfly Knife pour être sûr de ne rien rater
    params = {
        "limit": 50, 
        "category": 2, # Couteaux
        "type": "butterfly_knife",
        "sort_by": "most_recent"
    }
    
    try:
        r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            count, deals = 0, 0
            for i in items:
                name = i['item']['market_hash_name']
                # Filtrage manuel sur les deux skins cibles
                if "Ultraviolet" in name or "Stained" in name:
                    count += 1
                    price = i['price'] / 100
                    wear = i['item'].get('float_value', 0.0)
                    if is_good_deal(name, price, wear):
                        deals += 1
                        send_alert(name, price, wear, f"https://csfloat.com/item/{i['id']}", "CSFloat")
            print(f"   └─ {count} Butterfly cibles trouvés sur les 50 derniers scans. ({deals} deal(s))")
        else:
            print(f"❌ CSFloat Error {r.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur technique CSFloat: {e}")

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC: return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan DMarket...")
    
    pub, sec = DMARKET_PUB.strip(), DMARKET_SEC.strip()
    path = "/exchange/v1/market/items"
    # Utilisation du format + pour l'espace dans la signature
    query = "currency=USD&limit=50&orderBy=updatedAt&orderDir=desc&side=cash&title=Butterfly+Knife"
    timestamp = str(int(time.time()))
    
    sig_string = f"GET{path}?{query}{timestamp}"
    
    try:
        seed = bytes.fromhex(sec[:64])
        signing_key = nacl.signing.SigningKey(seed)
        signature = signing_key.sign(sig_string.encode('utf-8')).signature.hex()
        
        headers = {"X-Api-Key": pub, "X-Sign": signature, "X-Timestamp": timestamp}
        r = requests.get(f"https://api.dmarket.com{path}?{query}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            items = r.json().get("objects", [])
            count, deals = 0, 0
            for it in items:
                name = it.get("title", "")
                if any(x in name for x in ["Ultraviolet", "Stained"]):
                    count += 1
                    p_eur = (int(it['price']['USD']) / 100) * USD_TO_EUR
                    wear = it.get("extra", {}).get("floatValue", 0.0)
                    if is_good_deal(name, p_eur, wear):
                        deals += 1
                        send_alert(name, p_eur, wear, "https://dmarket.com", "DMarket")
            print(f"   └─ {count} Butterfly cibles analysés sur DMarket. ({deals} deal(s))")
        else:
            print(f"❌ DMarket Error {r.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur DMarket: {e}")

def send_alert(name, price, wear, url, source):
    print(f"🎯 ALERTE ! {name} ({price}€)")
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper v8.0 Lancé (Scan Large 50 items + Tolérance 5€)")
    while True:
        scan_csfloat()
        scan_dmarket()
        time.sleep(60)

if __name__ == "__main__":
    main()
