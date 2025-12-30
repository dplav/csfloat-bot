import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_INTERVAL = 40
SCANS_PER_CYCLE = 7
last_report_id = None
last_update_id = 0 
seen_items = {}
total_scans_done = 0

session = requests.Session()

def send_telegram_request(method, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    try:
        headers = {"Connection": "close"}
        r = session.post(url, json=payload, headers=headers, timeout=15)
        return r.json()
    except Exception as e:
        print(f"DEBUG TG: {e}")
        return None

def get_updates():
    global last_update_id
    payload = {"offset": last_update_id + 1, "timeout": 0}
    r = send_telegram_request("getUpdates", payload)
    if r and r.get("ok") and r.get("result"):
        for update in r["result"]:
            last_update_id = update["update_id"]
            if "message" in update and "text" in update["message"]:
                msg = update["message"]["text"]
                if msg == "/test1": trigger_test(1)
                elif msg == "/test3": trigger_test(3)

def trigger_test(count):
    headers = {"Authorization": API_KEY}
    url = f"https://csfloat.com/api/v1/listings?limit={count}&sort_by=lowest_price"
    try:
        r = session.get(url, headers=headers, timeout=15).json()
        for i in r.get("data", []):
            send_urgent_alert(i['item']['market_hash_name'], i['price']/100, i['item']['float_value'], i['id'], is_test=True)
    except: pass

def get_market_data():
    global last_report_id, total_scans_done
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    total_scans_done += 1
    
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.99, "max_f": 0.2409, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 520.00, "max_f": 1.0, "id": "ST_FT"},
        {"name": "★ Butterfly Knife | Stained (Well-Worn)", "max_p": 480.00, "max_f": 1.0, "id": "ST_WW"}
    ]
    
    status_lines = []
    current_scan_ids = set()
    errors_encountered = []

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=50&sort_by=lowest_price&type=buy_now"
        try:
            r = session.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    best_item = data[0]
                    low_p = best_item['price'] / 100
                    low_f = best_item['item']['float_value']
                    count = len(data)
                    
                    # Affichage : ID | Nombre | Prix | Float du moins cher
                    status_lines.append(f"✅ `{t['id']}`: {count} scans | **${low_p:.2f}** (f: `{low_f:.4f}`)")
                else:
                    status_lines.append(f"⚪ `{t['id']}`: Aucun item en vente")

                for i in data:
                    item_id = i['id']
                    current_scan_ids.add(item_id)
                    price = i['price']/100
                    wear = i['item']['float_value']
                    if price <= t['max_p'] and wear <= t['max_f']:
                        if item_id not in seen_items:
                            send_urgent_alert(t['name'], price, wear, item_id)
                            seen_items[item_id] = {"price": price, "name": t['name']}
            else:
                errors_encountered.append(f"{t['id']}: Erreur {r.status_code}")
        except Exception as e:
            errors_encountered.append(f"{t['id']}: Timeout")

    # Gestion des vendus
    sold_ids = [sid for sid in seen_items if sid not in current_scan_ids]
    for sid in sold_ids:
        item = seen_items[sid]
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": f"📦 **VENDU / RETIRÉ**\n{item['name']} @ ${item['price']}"})
        del seen_items[sid]

    update_report(status_lines, errors_encountered)

def update_report(lines, errors):
    global last_report_id
    now = datetime.now().strftime('%H:%M:%S')
    
    text = f"🛡️ **SNIPER v1.9 - EXPERT**\n"
    text += f"🕒 MAJ : `{now}` | Scan total : `{total_scans_done}`\n"
    text += f"--- \n"
    text += "\n".join(lines)
    
    if errors:
        text += f"\n\n⚠️ **LOGS :**\n" + "\n".join([f"- {e}" for e in errors])
    
    text += f"\n\n⚙️ `/test1` | `/test3`"
    
    if last_report_id is None:
        res = send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
        if res and res.get("ok"): 
            last_report_id = res['result']['message_id']
    else:
        send_telegram_request("editMessageText", {"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown"})

def send_urgent_alert(name, price, wear, item_id, is_test=False):
    prefix = "🧪 [TEST] " if is_test else "🚀 "
    msg = f"{prefix}**ALERTE !**\n\n🔪 {name}\n💰 **${price:.2f}**\n📉 Float: `{wear:.5f}`\n\n🔗 [LIEN](https://csfloat.com/item/{item_id})"
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        time.sleep(0.5)

if __name__ == "__main__":
    send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": "🛠️ **Lancement Sniper Expert v1.9...**"})
    while True:
        for _ in range(SCANS_PER_CYCLE):
            get_updates()
            get_market_data()
            time.sleep(SCAN_INTERVAL)
        time.sleep(10)
