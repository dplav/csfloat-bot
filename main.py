import os
import requests
import time
import sys
import nacl.signing
from datetime import datetime

# Force l'affichage immédiat des logs sur Railway
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
DMARKET_PUB = os.getenv("DMARKET_PUBLIC_KEY") 
DMARKET_SEC = os.getenv("DMARKET_SECRET_KEY")

USD_TO_EUR = 0.95  # Taux de conversion pour DMarket

def is_good_deal(name, price_eur, wear):
    """Vérifie si l'item correspond à tes critères de prix et de float"""
    # Butterfly Ultraviolet (Field-Tested)
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price_eur <= 520: return True
        if wear <= 0.16 and price_eur <= 580: return True
    
    # Butterfly Stained (Field-Tested)
    if "Stained" in name and "Field-Tested" in name:
        if price_eur <= 545 and wear <= 0.30: return True
        
    return False

def scan_csfloat():
    """Scan CSFloat avec logs détaillés"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan CSFloat...")
    headers = {"Authorization": CSFLOAT_API_KEY.strip() if CSFLOAT_API_KEY else ""}
    queries = ["Butterfly Knife Ultraviolet", "Butterfly Knife Stained"]
    
    total_found = 0
    deals_found = 0

    for q in queries:
        params = {"limit": 30, "full_text": q, "sort_by": "most_recent"}
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                total_found += len(data)
                for item in data:
                    item_info = item.get("item", {})
                    name = item_info.get("market_hash_name", "")
                    price = item.get("price", 0) / 100
                    wear = item_info.get("float_value", 0.0)
                    if is_good_deal(name, price, wear):
                        deals_found += 1
                        send_alert(name, price, wear, f"https://csfloat.com/item/{item['id']}", "CSFloat")
            else:
                print(f"❌ Erreur CSFloat API {r.status_code}")
        except Exception as e:
            print(f"⚠️ Erreur technique CSFloat: {e}")

    print(f"   └─ {total_found} Butterfly analysés sur CSFloat. ({deals_found} bonne(s) affaire(s) trouvée(s))")

def scan_dmarket():
    """Scan DMarket avec signature corrigée et logs détaillés"""
    if not DMARKET_PUB or not DMARKET_SEC: return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan DMarket...")
    pub_key = DMARKET_PUB.strip()
    sec_key = DMARKET_SEC.strip()

    method = "GET"
    path = "/exchange/v1/market/items"
    query = "currency=USD&limit=50&side=cash&title=Butterfly"
    timestamp = str(int(time.time()))
    
    # Signature Ed25519 (Ordre : Method + Path + Query + Timestamp)
    sig_string = f"{method}{path}?{query}{timestamp}"
    
    total_found = 0
    deals_found = 0

    try:
        seed = bytes.fromhex(sec_key[:64])
        signing_key = nacl.signing.SigningKey(seed)
        signature = signing_key.sign(sig_string.encode('utf-8')).signature.hex()
        
        headers = {
            "X-Api-Key": pub_key,
            "X-Sign": signature,
            "X-Timestamp": timestamp,
            "Accept": "application/json"
        }
        
        r = requests.get(f"https://api.dmarket.com{path}?{query}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            items = r.json().get("objects", [])
            for item in items:
                name = item.get("title", "")
                if "Butterfly Knife" in name and any(x in name for x in ["Ultraviolet", "Stained"]):
                    total_found += 1
                    try:
                        price_usd = int(item['price']['USD']) / 100
                        price_eur = price_usd * USD_TO_EUR
                        wear = item.get("extra", {}).get("floatValue", 0.0)
                        if is_good_deal(name, price_eur, wear):
                            deals_found += 1
                            url = f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}"
                            send_alert(name, price_eur, wear, url, "DMarket")
                    except: continue
            print(f"   └─ {total_found} Butterfly UV/Stained analysés sur DMarket. ({deals_found} bonne(s) affaire(s) trouvée(s))")
        else:
            print(f"❌ DMarket Error {r.status_code}: {r.text[:100]}")
            print(f"   Debug Sig String: {sig_string}")
    except Exception as e:
        print(f"⚠️ Erreur DMarket Signature: {e}")

def send_alert(name, price, wear, url, source):
    """Envoie une alerte sur Telegram"""
    print(f"🎯 ALERTE TROUVÉE sur {source} : {name} à {price:.2f}€")
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper Expert Dual-Site lancé...")
    print(f"Critères : UV FT <= 520€ (ou 580€ si float < 0.16) | Stained FT <= 545€ (float < 0.30)")
    
    while True:
        scan_csfloat()
        scan_dmarket()
        print(f"[{datetime.now().strftime('%H:%M:%S')}] 💤 En attente du prochain cycle (60s)...")
        time.sleep(60)

if __name__ == "__main__":
    main()
