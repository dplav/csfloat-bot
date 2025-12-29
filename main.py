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
    # FILTRE STRICT : Uniquement Ultraviolet ou Stained
    is_uv = "Ultraviolet" in name
    is_stained = "Stained" in name
    
    if not (is_uv or is_stained):
        return False

    # Seuils avec tolérance +5€
    if is_uv and "Field-Tested" in name:
        if price_eur <= 525: return True
        if wear <= 0.16 and price_eur <= 585: return True
    
    if is_stained and "Field-Tested" in name:
        if price_eur <= 550: return True
        
    return False

def scan_csfloat():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 CSFloat (UV & Stained)...")
    headers = {"Authorization": CSFLOAT_API_KEY.strip()}
    queries = ["Butterfly Knife Ultraviolet", "Butterfly Knife Stained"]
    total_scanned, deals = 0, 0
    min_found = 9999
    
    for q in queries:
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", 
                             headers=headers, 
                             params={"limit": 30, "full_text": q, "sort_by": "most_recent"}, timeout=15)
            if r.status_code == 200:
                items = r.json().get("data", [])
                for i in items:
                    name = i['item']['market_hash_name']
                    # On vérifie que c'est bien l'un des deux skins
                    if "Ultraviolet" in name or "Stained" in name:
                        total_scanned += 1
                        price = i['price'] / 100
                        wear = i['item'].get('float_value', 0.0)
                        
                        if 300 < price < min_found: min_found = price
                        
                        if is_good_deal(name, price, wear):
                            deals += 1
                            send_alert(name, price, wear, f"https://csfloat.com/item/{i['id']}", "CSFloat")
        except: pass
    print(f"   └─ {total_scanned} skins cibles vus. Prix min: {min_found if min_found < 9999 else 'N/A'}€ | {deals} deal(s)")

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC: return
    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 DMarket (UV & Stained)...")
    
    pub, sec = DMARKET_PUB.strip(), DMARKET_SEC.strip()
    path = "/exchange/v1/market/items"
    # On cherche "Butterfly" pour la signature, le filtre se fait après
    query = "currency=USD&limit=50&orderBy=updatedAt&orderDir=desc&side=cash&title=Butterfly"
    timestamp = str(int(time.time()))
    
    sig_string = f"GET{path}?{query}{timestamp}"
    
    try:
        signing_key = nacl.signing.SigningKey(bytes.fromhex(sec[:64]))
        signature = signing_key.sign(sig_string.encode('utf-8')).signature.hex()
        
        headers = {"X-Api-Key": pub, "X-Sign": signature, "X-Timestamp": timestamp}
        r = requests.get(f"https://api.dmarket.com{path}?{query}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            items = r.json().get("objects", [])
            count, deals = 0, 0
            min_p = 9999
            for it in items:
                name = it.get("title", "")
                # FILTRE UNIQUE : Uniquement les deux skins voulus
                if "Butterfly Knife" in name and any(x in name for x in ["Ultraviolet", "Stained"]):
                    count += 1
                    p_eur = (int(it['price']['USD']) / 100) * USD_TO_EUR
                    if 300 < p_eur < min_p: min_p = p_eur
                    wear = it.get("extra", {}).get("floatValue", 0.0)
                    if is_good_deal(name, p_eur, wear):
                        deals += 1
                        send_alert(name, p_eur, wear, f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}", "DMarket")
            print(f"   └─ {count} skins cibles vus. Prix min: {min_p if min_p < 9999 else 'N/A'}€ | {deals} deal(s)")
        else:
            print(f"❌ DMarket Error {r.status_code}")
    except Exception as e:
        print(f"⚠️ Erreur DMarket: {e}")

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *ALERTE {source} !*\n\n🔪 *{name}*\n💰 *{price:.2f}€*\n📉 *Float:* `{wear:.5f}`\n\n🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper Expert v6.0 (Filtre Sélectif UV/Stained)")
    while True:
        scan_csfloat()
        scan_dmarket()
        time.sleep(60)

if __name__ == "__main__":
    main()
