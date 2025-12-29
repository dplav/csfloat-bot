import os
import requests
import time
import sys
import nacl.signing
from datetime import datetime

# Force l'affichage des logs sur Railway
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
DMARKET_PUB = os.getenv("DMARKET_PUBLIC_KEY") 
DMARKET_SEC = os.getenv("DMARKET_SECRET_KEY")

# Taux de change pour la conversion (Ajuste si besoin)
# 1 USD est environ 0.95 EUR
USD_TO_EUR = 0.95

def is_good_deal(name, price_eur, wear):
    """Critères de sélection en Euros"""
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price_eur <= 520: return True
        if wear <= 0.16 and price_eur <= 580: return True
    
    if "Stained" in name and "Field-Tested" in name:
        if price_eur <= 545 and wear <= 0.30: return True
        
    return False

def scan_csfloat():
    """Scan CSFloat"""
    headers = {"Authorization": CSFLOAT_API_KEY}
    queries = [
        "Butterfly Knife Ultraviolet <585€ newest",
        "Butterfly Knife Stained <550€ newest"
    ]
    for query in queries:
        params = {"limit": 30, "full_text": query, "sort_by": "most_recent"}
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                for item in r.json().get("data", []):
                    item_info = item.get("item", {})
                    name = item_info.get("market_hash_name", "")
                    price = item.get("price", 0) / 100
                    wear = item_info.get("float_value", 0.0)
                    if is_good_deal(name, price, wear):
                        send_alert(name, price, wear, f"https://csfloat.com/item/{item['id']}", "CSFloat")
        except:
            pass

def scan_dmarket():
    """Scan DMarket avec devise USD explicite"""
    if not DMARKET_PUB or not DMARKET_SEC:
        return

    pub_key = DMARKET_PUB.strip()
    sec_key = DMARKET_SEC.strip()

    method = "GET"
    # On force currency=USD pour satisfaire l'API
    path = "/exchange/v1/market/items?side=cash&title=Butterfly%20Knife&orderBy=updatedAt&orderDir=desc&limit=50&currency=USD"
    timestamp = str(int(time.time()))
    
    sig_string = method + path + "" + timestamp
    try:
        seed = bytes.fromhex(sec_key[:64])
        signing_key = nacl.signing.SigningKey(seed)
        signature = signing_key.sign(sig_string.encode('utf-8')).signature.hex()
        
        headers = {
            "X-Api-Key": pub_key,
            "X-Sign": signature,
            "X-Timestamp": timestamp,
            "Content-Type": "application/json"
        }
        
        r = requests.get(f"https://api.dmarket.com{path}", headers=headers, timeout=10)
        
        if r.status_code == 200:
            data = r.json()
            items = data.get("objects", [])
            print(f"🔎 DMarket : {len(items)} items vérifiés (USD).")
            for item in items:
                name = item.get("title", "")
                if "Ultraviolet" in name or "Stained" in name:
                    # Extraction du prix en USD et conversion en EUR pour le filtre
                    try:
                        price_usd = int(item['price']['USD']) / 100
                        price_eur = price_usd * USD_TO_EUR
                        
                        wear = item.get("extra", {}).get("floatValue", 0.0)
                        if is_good_deal(name, price_eur, wear):
                            url = f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}"
                            send_alert(name, price_eur, wear, url, "DMarket")
                    except KeyError:
                        continue
        else:
            print(f"❌ DMarket Erreur {r.status_code} : {r.text}")
    except Exception as e:
        print(f"⚠️ Erreur technique DMarket : {e}")

def send_alert(name, price, wear, url, source):
    """Envoie l'alerte sur Telegram"""
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix approx : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper démarré (Fix Currency USD)...")
    while True:
        # On fait 6 cycles par exécution Railway
        for _ in range(6):
            scan_csfloat()
            scan_dmarket()
            time.sleep(40)
        # Petit sleep de sécurité entre les gros blocs
        time.sleep(1)

if __name__ == "__main__":
    main()
