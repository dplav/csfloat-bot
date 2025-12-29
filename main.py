import os
import requests
import time
import sys
import nacl.signing
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
DMARKET_PUB = os.getenv("DMARKET_PUBLIC_KEY")
DMARKET_SEC = os.getenv("DMARKET_SECRET_KEY")

USD_TO_EUR = 0.95

def is_good_deal(name, price_eur, wear):
    # On s'assure que c'est bien un Butterfly Knife et qu'il est FT
    if "Butterfly Knife" not in name or "Field-Tested" not in name:
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
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan CSFloat...")
    headers = {"Authorization": CSFLOAT_API_KEY.strip() if CSFLOAT_API_KEY else ""}
    
    # Utilisation de 'full_text' au lieu de 'type' pour éviter l'erreur de schéma
    params = {
        "limit": 50, 
        "full_text": "Butterfly Knife",
        "sort_by": "most_recent"
    }
    
    try:
        r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=15)
        if r.status_code == 200:
            items = r.json().get("data", [])
            count, deals = 0, 0
            for i in items:
                name = i['item']['market_hash_name']
                if "Ultraviolet" in name or "Stained" in name:
                    count += 1
                    price = i['price'] / 100
                    wear = i['item'].get('float_value', 0.0)
                    if is_good_deal(name, price, wear):
                        deals += 1
                        send_alert(name, price, wear, f"https://csfloat.com/item/{i['id']}", "CSFloat")
            print(f"   └─ ✅ {len(items)} Butterfly scannés | {count} cibles trouvées | {deals} deal")
        else:
            print(f"❌ CSFloat Error {r.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur CSFloat: {e}")

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC: return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan DMarket...")
    
    pub, sec = DMARKET_PUB.strip(), DMARKET_SEC.strip()
    path = "/exchange/v1/market/items"
    # Query simplifiée à l'extrême
    query = "currency=USD&limit=50&side=cash&title=Butterfly"
    timestamp = str(int(time.time()))
    
    # Signature v10 (Strict respect de la concaténation)
    sig_string = f"GET{path}?{query}{timestamp}"
    
    try:
        signing_key = nacl.signing.SigningKey(bytes.fromhex(sec[:64]))
        signature = signing_key.sign(sig_string.encode('utf-8')).signature.hex()
        
        headers = {
            "X-Api-Key": pub,
            "X-Sign": signature,
            "X-Timestamp": timestamp
        }
        
        r = requests.get(f"https://api.dmarket.com{path}?{query}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            items = r.json().get("objects", [])
            count, deals = 0, 0
            for it in items:
                name = it.get("title", "")
                if "Butterfly Knife" in name and any(x in name for x in ["Ultraviolet", "Stained"]):
                    count += 1
                    p_eur = (int(it['price']['USD']) / 100) * USD_TO_EUR
                    wear = it.get("extra", {}).get("floatValue", 0.0)
                    if is_good_deal(name, p_eur, wear):
                        deals += 1
                        send_alert(name, p_eur, wear, "https://dmarket.com", "DMarket")
            print(f"   └─ ✅ {count} Butterfly cibles sur DMarket | {deals} deal")
        else:
            print(f"❌ DMarket Error {r.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur DMarket: {e}")

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper v10.0 (Mode Recherche Textuelle)")
    while True:
        scan_csfloat()
        scan_dmarket()
        time.sleep(60)

if __name__ == "__main__":
    main()
