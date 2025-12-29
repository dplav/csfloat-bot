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
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price_eur <= 520: return True
        if wear <= 0.16 and price_eur <= 580: return True
    if "Stained" in name and "Field-Tested" in name:
        if price_eur <= 545 and wear <= 0.30: return True
    return False

def scan_csfloat():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan CSFloat...")
    headers = {"Authorization": CSFLOAT_API_KEY.strip() if CSFLOAT_API_KEY else ""}
    for q in ["Butterfly Knife Ultraviolet", "Butterfly Knife Stained"]:
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", 
                             headers=headers, 
                             params={"limit": 30, "full_text": q, "sort_by": "most_recent"}, 
                             timeout=15)
            if r.status_code == 200:
                for item in r.json().get("data", []):
                    name = item['item']['market_hash_name']
                    price = item['price'] / 100
                    wear = item['item'].get('float_value', 0.0)
                    if is_good_deal(name, price, wear):
                        send_alert(name, price, wear, f"https://csfloat.com/item/{item['id']}", "CSFloat")
        except: pass

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC: return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan DMarket...")
    
    # Nettoyage strict des clés
    api_key = DMARKET_PUB.replace(" ", "").strip()
    secret_key = DMARKET_SEC.replace(" ", "").strip()

    method = "GET"
    path = "/exchange/v1/market/items"
    query = "currency=USD&limit=50&side=cash&title=Butterfly"
    timestamp = str(int(time.time()))
    
    # Construction du message à signer
    sig_string = f"{method}{path}?{query}{timestamp}"
    
    try:
        # DMarket attend la signature du message : Method + Path + Query + Timestamp
        # Note: Pas de Body pour un GET
        signing_key = nacl.signing.SigningKey(bytes.fromhex(secret_key[:64]))
        signed = signing_key.sign(sig_string.encode('utf-8'))
        signature = signed.signature.hex()
        
        headers = {
            "X-Api-Key": api_key,
            "X-Sign": signature,
            "X-Timestamp": timestamp,
            "Accept": "application/json"
        }
        
        url = f"https://api.dmarket.com{path}?{query}"
        r = requests.get(url, headers=headers, timeout=15)
        
        if r.status_code == 200:
            items = r.json().get("objects", [])
            print(f"✅ DMarket : {len(items)} items analysés.")
            for item in items:
                name = item.get("title", "")
                if "Butterfly Knife" in name and any(x in name for x in ["Ultraviolet", "Stained"]):
                    try:
                        price_usd = int(item['price']['USD']) / 100
                        price_eur = price_usd * USD_TO_EUR
                        wear = item.get("extra", {}).get("floatValue", 0.0)
                        if is_good_deal(name, price_eur, wear):
                            send_alert(name, price_eur, wear, f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}", "DMarket")
                    except: continue
        else:
            print(f"❌ DMarket Error {r.status_code}: {r.text}")
            # Si erreur 400 persiste, on log la string de signature pour débugger
            if r.status_code == 400:
                print(f"Debug Sig String: {sig_string}")

    except Exception as e:
        print(f"⚠️ Erreur DMarket Signature: {e}")

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper Relancé - Test Signature v3...")
    while True:
        scan_csfloat()
        scan_dmarket()
        time.sleep(60)

if __name__ == "__main__":
    main()
