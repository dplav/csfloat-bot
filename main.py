import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_INTERVAL = 45
current_rate = 0.851 
last_report_id = None
seen_items = {}
total_scans_done = 0

def send_telegram_request(method, payload):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/{method}"
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except: return None

def get_market_data():
    global last_report_id, total_scans_done
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 615.00, "max_f": 0.2400, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 570.00, "max_f": 1.0, "id": "ST_FT"},
        {"name": "★ Butterfly Knife | Stained (Well-Worn)", "max_p": 540.00, "max_f": 1.0, "id": "ST_WW"}
    ]
    
    status_lines = []
    current_scan_ids = set()

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=50&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                best_item = None
                for i in data:
                    current_scan_ids.add(i['id'])
                    p_usd = i['price'] / 100
                    f_val = i['item']['float_value']
                    
                    if f_val <= t['max_f']:
                        if best_item is None:
                            best_item = i
                        if p_usd <= t['max_p'] and i['id'] not in seen_items:
                            send_urgent_alert(t['name'], p_usd, f_val, i['id'])
                            seen_items[i['id']] = {"p": p_usd}

                if best_item:
                    p_eur = (best_item['price'] / 100) * current_rate
                    f_raw = best_item['item']['float_value']
                    i_id = best_item['id']
                    # Lien direct sur le prix
                    status_lines.append(
                        f"🎯 `{t['id']}`: {len(data)} items\n"
                        f"└ [**{p_eur:.2f}€**](https://csfloat.com/item/{i_id}) | f: `{f_raw:.10f}` | ID: `...{i_id[-4:]}`"
                    )
                else:
                    status_lines.append(f"❌ `{t['id']}`: Aucun item < {t['max_f']}")
        except:
            status_lines.append(f"📡 `{t['id']}`: Timeout")

    total_scans_done += 1
    update_report(status_lines)

def update_report(lines):
    global last_report_id
    # Heure du dernier scan, nombre total et taux conservés
    text = (f"🛡️ **SNIPER v1.17**\n"
            f"🕒 Dernier scan : `{datetime.now().strftime('%H:%M:%S')}`\n"
            f"📈 Total scans : `{total_scans_done}` | Taux : `{current_rate}`\n"
            f"--- \n" + "\n".join(lines))
    
    if last_report_id:
        send_telegram_request("editMessageText", {"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True})
    else:
        res = send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True})
        if res: last_report_id = res.get('result', {}).get('message_id')

def send_urgent_alert(name, p_usd, wear, item_id):
    p_eur = p_usd * current_rate
    msg = (f"🚀 **CIBLE DÉTECTÉE !**\n\n"
           f"🔪 {name}\n"
           f"💰 **{p_eur:.2f}€**\n"
           f"📉 Float: `{wear:.10f}`\n"
           f"🔗 [VOIR L'ANNONCE](https://csfloat.com/item/{item_id})")
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        time.sleep(0.5)

if __name__ == "__main__":
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
