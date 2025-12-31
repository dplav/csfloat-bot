import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_INTERVAL = 60  # 1 minute pour la sécurité
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
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=50&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            
            # GESTION DU BLOCAGE (Rate Limit)
            if r.status_code == 429:
                print("⚠️ BLOCAGE DÉTECTÉ (Erreur 429). Mise en sommeil...")
                send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": "🛑 **CSFloat me bloque (Trop de requêtes).**\nJe m'endors pendant 10 minutes pour débloquer l'IP."})
                is_blocked = True
                break # On arrête tout de suite

            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    low_p, low_f = data[0]['price']/100, data[0]['item']['float_value']
                    status_lines.append(f"✅ `{t['id']}`: {len(data)} items | **${low_p:.2f}** (f: `{low_f:.4f}`)")
                    for i in data:
                        current_scan_ids.add(i['id'])
                        if i['price']/100 <= t['max_p'] and i['item']['float_value'] <= t['max_f']:
                            if i['id'] not in seen_items:
                                send_urgent_alert(t['name'], i['price']/100, i['item']['float_value'], i['id'])
                                seen_items[i['id']] = {"price": i['price']/100, "name": t['name']}
            else:
                status_lines.append(f"❌ `{t['id']}`: Erreur {r.status_code}")
        except:
            status_lines.append(f"⚠️ `{t['id']}`: Timeout")

    if is_blocked:
        time.sleep(600) # Pause de 10 minutes
        return

    total_scans_done += 1
    
    # Gestion des vendus
    sold_ids = [sid for sid in seen_items if sid not in current_scan_ids]
    for sid in sold_ids:
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": f"📦 **VENDU**\n{seen_items[sid]['name']} @ ${seen_items[sid]['price']}"})
        del seen_items[sid]

    update_report(status_lines)

def update_report(lines):
    global last_report_id
    text = (f"🛡️ **SNIPER v2.3 (Anti-Ban)**\n"
            f"🕒 `{datetime.now().strftime('%H:%M:%S')}` | Scans: `{total_scans_done}`\n"
            f"---\n" + "\n".join(lines))
    
    if last_report_id is None:
        res = send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
        if res and res.get("ok"): last_report_id = res['result']['message_id']
    else:
        send_telegram_request("editMessageText", {"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown"})

def send_urgent_alert(name, price, wear, item_id):
    msg = f"🚀 **ALERTE ACHAT** 🚀\n\n🔪 {name}\n💰 **${price:.2f}**\n📉 Float: `{wear:.5f}`\n\n🔗 https://csfloat.com/item/{item_id}"
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        time.sleep(0.5)

if __name__ == "__main__":
    print("Démarrage Sniper v2.3...")
    send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": "🚀 **Sniper v2.3 lancé (Intervalle 60s).**"})
    
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
