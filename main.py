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
    
    # On sépare les termes de recherche pour éviter les erreurs d'URL
    queries = ["Butterfly Knife Ultraviolet", "Butterfly Knife Stained"]
    
    for q in queries:
        params = {
            "limit": 30,
            "full_text": q,
            "sort_by": "most_recent",
            "category": "knife"
        }
        try:
            # On laisse requests gérer l'encodage des paramètres
            r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                for item in data:
                    item_info = item.get("item", {})
                    name = item_info.get("market_hash_name", "")
                    price = item.get("price", 0) / 100
                    wear = item_info.get("float_value", 0.0)
                    if is_good_deal(name, price, wear):
                        send_alert(name, price, wear, f"https://csfloat.com/item/{item['id']}", "CSFloat")
            else:
                print(f"❌ Erreur CSFloat API {r.status_code}: {r.text[:50]}")
        except Exception as e:
            print(f"⚠️ Erreur CSFloat: {e}")

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC:
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] 🔍 Scan DMarket...")
    pub_key = DMARKET_PUB.strip()
    sec_key = DMARKET_SEC.strip()

    # DMarket est très strict sur l'ordre alphabétique des paramètres pour la signature
    path = "/exchange/v1/market/items"
    params = {
        "currency": "USD",
        "limit": "50",
        "orderBy": "updatedAt",
        "orderDir": "desc",
        "side": "cash",
        "title": "Butterfly Knife"
    }
    
    # Reconstruction manuelle de la query string triée pour la signature
    query_string = "&".join([f"{k}={v}".replace(" ", "%20") for k, v in sorted(params.items())])
    full_path_for_sig = f"{path}?{query_string}"
    
    timestamp = str(int(time.time()))
    sig_string = "GET" + full_path_for_sig + "" + timestamp
    
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
        
        # On utilise le full_path_for_sig pour être sûr que l'URL appelée = URL signée
        r = requests.get(f"https://api.dmarket.com{full_path_for_sig}", headers=headers, timeout=15)
        
        if r.status_code == 200:
            items = r.json().get("objects", [])
            print(f"✅ DMarket : {len(items)} items vérifiés.")
            for item in items:
                name = item.get("title", "")
                if any(x in name for x in ["Ultraviolet", "Stained"]):
                    try:
                        price_usd = int(item['price']['USD']) / 100
                        price_eur = price_usd * USD_TO_EUR
                        wear = item.get("extra", {}).get("floatValue", 0.0)
                        if is_good_deal(name, price_eur, wear):
                            url = f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}"
                            send_alert(name, price_eur, wear, url, "DMarket")
                    except: continue
        else:
            print(f"❌ DMarket Erreur {r.status_code}: {r.text[:100]}")
    except Exception as e:
        print(f"⚠️ Erreur DMarket: {e}")

def send_alert(name, price, wear, url, source):
    print(f"🎯 ALERTE TROUVÉE sur {source} !")
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price:.2f}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [VOIR L'OFFRE]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    print("🚀 Sniper Expert démarré...")
    while True:
        scan_csfloat()
        scan_dmarket()
        time.sleep(60) # Augmentation du délai pour éviter les bans IP

if __name__ == "__main__":
    main()
