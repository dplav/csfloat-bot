import os
import requests
import time
import sys
import nacl.signing
from datetime import datetime
from urllib.parse import urlencode

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
DMARKET_PUB = os.getenv("DMARKET_PUBLIC_KEY").strip() if os.getenv("DMARKET_PUBLIC_KEY") else None
DMARKET_SEC = os.getenv("DMARKET_SECRET_KEY").strip() if os.getenv("DMARKET_SECRET_KEY") else None

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
    headers = {"Authorization": CSFLOAT_API_KEY.strip()}
    queries = ["Butterfly Knife Ultraviolet", "Butterfly Knife Stained"]
    total, deals = 0, 0
    min_price = 9999
    
    for q in queries:
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", 
                             headers=headers, 
                             params={"limit": 30, "full_text": q, "sort_by": "most_recent"}, timeout=15)
            if r.status_code == 200:
                items = r.json().get("data", [])
                total += len(items)
                for i in items:
                    price = i['price'] / 100
                    if price < min_price: min_price = price
                    if is_good_deal(i['item']['market_hash_name'], price, i['item'].get('float_value', 0.0)):
                        deals += 1
                        send_alert(i['item']['market_hash_name'], price, i['item'].get('float_value', 0.0), f"https://csfloat.com/item/{i['id']}", "CSFloat")
        except: pass
    print(f"   └─ {total} Butterfly vus. Prix min trouvé: {min_price if min_price < 9999 else 'N/A'}€ | {deals} affaire(s)")

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC: return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan DMarket...")
    
    method = "GET"
    path = "/exchange/v1/market/items"
    # Paramètres triés par ordre alphabétique (obligatoire pour DMarket)
    params = {
        "currency": "USD",
        "limit": 50,
        "orderBy": "updatedAt",
        "orderDir": "desc",
        "side": "cash",
        "title": "Butterfly Knife"
    }
    
    query_string = urlencode(params)
    timestamp = str(int(time.time()))
    
    # Construction de la signature : METHOD + PATH + QUERY_STRING + TIMESTAMP
    # On n'ajoute RIEN entre la query et le timestamp
    sig_string = f"{method}{path}?{query_string}{timestamp}"
    
    try:
        signing_key = nacl.signing.SigningKey(bytes.fromhex(DMARKET_SEC[:64]))
        signature = signing_key.sign(sig_string.encode('utf-8')).signature.hex()
        
        headers = {
            "X-Api-Key": DMARKET_PUB,
            "X-Sign": signature,
            "X-Timestamp": timestamp
        }
        
        r = requests.get(f"https://api.dmarket.com{path}?{query_string}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            items = r.json().get("objects", [])
            count, deals = 0, 0
            min_p = 9999
            for it in items:
                name = it.get("title", "")
                if any(x in name for x in ["Ultraviolet", "Stained"]):
                    count += 1
                    p_eur = (int(it['price']['USD']) / 100) * USD_TO_EUR
                    if p_eur < min_p: min_p = p_eur
                    if is_good_deal(name, p_eur, it.get("extra", {}).get("floatValue", 0.0)):
                        deals += 1
                        send_alert(name, p_eur, it.get("extra", {}).get("floatValue", 0.0), f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}", "DMarket")
            print(f"   └─ {count} Butterfly UV/Stained vus. Prix min: {min_p if min_p < 9999 else 'N/A'}€ | {deals} affaire(s)")
        else:
            print(f"❌ DMarket Error {r.status_code}: {r.text[:50]}")
            print(f"   Debug Sig String: {sig_string}")
    except Exception as e:
        print(f"⚠️ Erreur DMarket: {e}")

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *ALERTE {source} !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [LIEN]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper Expert v4.0 (Correction Signature & Logs Prix)")
    while True:
        scan_csfloat()
        scan_dmarket()
        time.sleep(60)

if __name__ == "__main__":
    main()
