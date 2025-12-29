import os
import requests
import time
import sys
import nacl.signing
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

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
    q_list = ["Butterfly Knife Ultraviolet", "Butterfly Knife Stained"]
    total, deals = 0, 0
    for q in q_list:
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", 
                             headers=headers, 
                             params={"limit": 30, "full_text": q, "sort_by": "most_recent"}, timeout=15)
            if r.status_code == 200:
                items = r.json().get("data", [])
                total += len(items)
                for i in items:
                    name = i['item']['market_hash_name']
                    price = i['price'] / 100
                    wear = i['item'].get('float_value', 0.0)
                    if is_good_deal(name, price, wear):
                        deals += 1
                        send_alert(name, price, wear, f"https://csfloat.com/item/{i['id']}", "CSFloat")
        except: pass
    print(f"   └─ {total} Butterfly analysés sur CSFloat. ({deals} affaire(s))")

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC: return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan DMarket...")
    
    pub, sec = DMARKET_PUB.strip(), DMARKET_SEC.strip()
    path, query = "/exchange/v1/market/items", "currency=USD&limit=50&side=cash&title=Butterfly"
    timestamp = str(int(time.time()))
    
    # Signature STRICTE : Method + Path + ? + Query + Body(vide) + Timestamp
    sig_string = f"GET{path}?{query}{timestamp}"
    
    try:
        signing_key = nacl.signing.SigningKey(bytes.fromhex(sec[:64]))
        signature = signing_key.sign(sig_string.encode('utf-8')).signature.hex()
        
        headers = {"X-Api-Key": pub, "X-Sign": signature, "X-Timestamp": timestamp}
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
                        send_alert(name, p_eur, wear, f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}", "DMarket")
            print(f"   └─ {count} Butterfly UV/Stained sur DMarket. ({deals} affaire(s))")
        else:
            print(f"❌ DMarket Error {r.status_code}")
            print(f"   Debug Sig: {sig_string}")
    except Exception as e: print(f"⚠️ Erreur DMarket: {e}")

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *ALERTE {source} !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [LIEN]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper Opérationnel...")
    while True:
        scan_csfloat()
        scan_dmarket()
        time.sleep(60)

if __name__ == "__main__":
    main()
