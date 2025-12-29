import os
import requests
import time
import sys
import ed25519
from datetime import datetime

sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

# Identifiants DMarket via Railway
DMARKET_PUB = os.getenv("DMARKET_PUBLIC_KEY") 
DMARKET_SEC = os.getenv("DMARKET_SECRET_KEY")

RECHERCHES_CS = [
    "Butterfly Knife Ultraviolet <585€ newest",
    "Butterfly Knife Stained <550€ newest"
]

def update_status(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_notification": True}
    r = requests.post(url, json=payload).json()
    return r.get("result", {}).get("message_id")

def delete_message(msg_id):
    if msg_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id})

def is_good_deal(name, price, wear):
    # Criteres Ultraviolet - MIS À JOUR À 520€
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price <= 520: return True
        if wear <= 0.16 and price <= 580: return True
    
    # Criteres Stained
    if "Stained" in name and "Field-Tested" in name:
        if price <= 545 and wear <= 0.30: return True
        
    return False

def scan_csfloat():
    headers = {"Authorization": CSFLOAT_API_KEY}
    for query in RECHERCHES_CS:
        params = {"limit": 30, "full_text": query, "sort_by": "most_recent"}
        try:
            r = requests.get("https://csfloat.com/api/v1/listings", headers=headers, params=params, timeout=10)
            if r.status_code == 200:
                items = r.json().get("data", [])
                for item in items:
                    name = item['item']['market_hash_name']
                    price = item['price'] / 100
                    wear = item['item'].get('float_value', 0.0)
                    if is_good_deal(name, price, wear):
                        send_alert(name, price, wear, f"https://csfloat.com/item/{item['id']}", "CSFloat")
        except Exception as e:
            print(f"⚠️ Erreur CSFloat : {e}")

def scan_dmarket():
    if not DMARKET_PUB or not DMARKET_SEC:
        return

    method = "GET"
    path = "/exchange/v1/market/items?side=cash&title=Butterfly%20Knife&orderBy=updatedAt&orderDir=desc&limit=50&currency=EUR"
    timestamp = str(int(time.time()))
    
    sig_string = method + path + "" + timestamp
    try:
        signing_key = ed25519.SigningKey(bytes.fromhex(DMARKET_SEC[:64]))
        signature = signing_key.sign(sig_string.encode('utf-8')).hex()
        
        headers = {
            "X-Api-Key": DMARKET_PUB,
            "X-Sign": signature,
            "X-Timestamp": timestamp
        }
        
        r = requests.get(f"https://api.dmarket.com{path}", headers=headers, timeout=10)
        if r.status_code == 200:
            items = r.json().get("objects", [])
            print(f"🔎 DMarket : {len(items)} Butterfly vérifiés.")
            for item in items:
                name = item.get("title", "")
                if "Ultraviolet" in name or "Stained" in name:
                    price = int(item['price']['EUR']) / 100
                    wear = item.get("extra", {}).get("floatValue", 0.0)
                    if is_good_deal(name, price, wear):
                        url = f"https://dmarket.com/ingame-items/item-list/csgo-skins?title={name}"
                        send_alert(name, price, wear, url, "DMarket")
    except Exception as e:
        print(f"⚠️ Erreur DMarket : {e}")

def send_alert(name, price, wear, url, source):
    msg = (f"🎯 *ALERTE {source.upper()} !*\n\n"
           f"🔪 *{name}*\n"
           f"💰 *Prix : {price}€*\n"
           f"📉 *Float :* `{wear:.5f}`\n\n"
           f"🔗 [LIEN DIRECT]({url})")
    requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                  json={"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})

def main():
    last_msg_id = None
    for i in range(6):
        now = datetime.now().strftime("%H:%M:%S")
        delete_message(last_msg_id)
        last_msg_id = update_status(f"🛰️ *Sniper Ultra-Actif*\nCycle : `{i+1}/6` | `{now}`\nCibles : UV & Stained")
        
        scan_csfloat()
        scan_dmarket()
        
        if i < 5:
            time.sleep(40)
    delete_message(last_msg_id)

if __name__ == "__main__":
    main()
