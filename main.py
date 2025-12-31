import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_INTERVAL = 60
TAUX_CONVERSION = 0.92  # 1 USD = 0.92 EUR (ajustable)
last_report_id = None
seen_items = {}
total_scans_done = 0

def send_telegram_request(method, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except:
        return None

def get_market_data():
    global last_report_id, total_scans_done
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.99, "max_f": 0.2409, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 520.00, "max_f": 1.0, "id": "ST_FT"},
        {"name": "★ Butterfly Knife | Stained (Well-Worn)", "max_p": 480.00, "max_f": 1.0, "id": "ST_WW"}
    ]
    
    status_lines = []
    current_scan_ids = set()
    is_blocked = False

    for t in targets:
        # Ajout de type=buy_now pour exclure les enchères
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=50&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            
            if r.status_code == 429:
                is_blocked = True
                break

            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    # On cherche le moins cher ABSOLU (pour le rapport)
                    best_any = data[0]
                    abs_p_usd = best_any['price']/100
                    abs_p_eur = abs_p_usd * TAUX_CONVERSION
                    abs_f = best_any['item']['float_value']
                    
                    status_lines.append(f"✅ `{t['id']}`: {len(data)} vus | **{abs_p_eur:.2f}€** (f: `{abs_f:.4f}`)")

                    # On scanne les 50 pour trouver une cible qui respecte tes critères
                    for i in data:
                        item_id = i['id']
                        current_scan_ids.add(item_id)
                        price_usd = i['price']/100
                        wear = i['item']['float_value']
                        
                        if price_usd <= t['max_p'] and wear <= t['max_f']:
                            if item_id not in seen_items:
                                send_urgent_alert(t['name'], price_usd, wear, item_id)
                                seen_items[item_id] = {"price": price_usd, "name": t['name']}
                else:
                    status_lines.append(f"⚪ `{t['id']}`: Aucun item")
            else:
                status_lines.append(f"❌ `{t['id']}`: Erreur {r.status_code}")
        except:
            status_lines.append(f"⚠️ `{t['id']}`: Timeout")

    if is_blocked:
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": "🛑 Rate Limit CSFloat ! Pause 10min."})
        time.sleep(600)
        return

    total_scans_done += 1
    
    # Gestion des vendus
    sold_ids = [sid for sid in seen_items if sid not in current_scan_ids]
    for sid in sold_ids:
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": f"📦 **VENDU**\n{seen_items[sid]['name']}"})
        del seen_items[sid]

    update_report(status_lines)

def update_report(lines):
    global last_report_id
    now = datetime.now().strftime('%H:%M:%S')
    text = (f"🛡️ **SNIPER v1.10 (EUR/USD)**\n"
            f"🕒 `{now}` | Scans: `{total_scans_done}`\n"
            f"---\n" + "\n".join(lines))
    
    if last_report_id is None:
        res = send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
        if res and res.get("ok"): last_report_id = res['result']['message_id']
    else:
        send_telegram_request("editMessageText", {"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown"})

def send_urgent_alert(name, price_usd, wear, item_id):
    price_eur = price_usd * TAUX_CONVERSION
    msg = (f"🚀 **ALERTE ACHAT** 🚀\n\n"
           f"🔪 {name}\n"
           f"💰 **{price_eur:.2f}€** (${price_usd:.2f})\n"
           f"📉 Float: `{wear:.5f}`\n\n"
           f"🔗 https://csfloat.com/item/{item_id}")
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        time.sleep(0.5)

if __name__ == "__main__":
    send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": "🛠️ **Lancement v1.10 (Filtre Buy Now + EUR)**"})
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
