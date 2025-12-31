import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_INTERVAL = 45 # On peut redescendre un peu
TAUX_CONVERSION = 0.92 # Taux pour passer de $ à €
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
    
    # Cibles avec prix ajustés en Dollars (Valeurs approximatives à vérifier sur le site en USD)
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 615.00, "max_f": 0.2400, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 570.00, "max_f": 1.0, "id": "ST_FT"},
        {"name": "★ Butterfly Knife | Stained (Well-Worn)", "max_p": 540.00, "max_f": 1.0, "id": "ST_WW"}
    ]
    
    status_lines = []
    current_scan_ids = set()
    is_blocked = False

    for t in targets:
        # On force "Buy Now" pour avoir exactement les mêmes 18 skins que toi
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=50&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 429:
                is_blocked = True
                break

            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # On cherche le moins cher qui respecte le FLOAT (ici max_f=1.0 donc tous)
                best_item = None
                for i in data:
                    current_scan_ids.add(i['id'])
                    price_usd = i['price'] / 100
                    float_val = i['item']['float_value']
                    
                    if float_val <= t['max_f']:
                        if best_item is None:
                            best_item = i
                        
                        if price_usd <= t['max_p']:
                            if i['id'] not in seen_items:
                                send_urgent_alert(t['name'], price_usd, float_val, i['id'])
                                seen_items[i['id']] = {"p": price_usd}

                if best_item:
                    p_usd = best_item['price'] / 100
                    p_eur = p_usd * TAUX_CONVERSION
                    f_val = best_item['item']['float_value']
                    # On affiche le nombre d'items exact trouvé par l'API
                    status_lines.append(f"🎯 `{t['id']}`: {len(data)} skins | **{p_eur:.2f}€** (`${p_usd:.0f}`)")
                else:
                    status_lines.append(f"❌ `{t['id']}`: Aucun skin trouvé")
            else:
                status_lines.append(f"⚠️ `{t['id']}`: Erreur {r.status_code}")
        except:
            status_lines.append(f"📡 `{t['id']}`: Erreur Connexion")

    if is_blocked:
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": "🛑 Rate limit. Pause 10min."})
        time.sleep(600)
        return

    total_scans_done += 1
    # Nettoyage des vendus
    sold_ids = [sid for sid in seen_items if sid not in current_scan_ids]
    for sid in sold_ids: del seen_items[sid]

    update_report(status_lines)

def update_report(lines):
    global last_report_id
    text = (f"🛡️ **SNIPER v1.13** | `{datetime.now().strftime('%H:%M:%S')}`\n"
            f"📈 Scans réalisés: `{total_scans_done}`\n"
            f"--- \n" + "\n".join(lines))
    
    if last_report_id is None:
        res = send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
        if res and res.get("ok"): last_report_id = res['result']['message_id']
    else:
        send_telegram_request("editMessageText", {"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown"})

def send_urgent_alert(name, p_usd, wear, item_id):
    p_eur = p_usd * TAUX_CONVERSION
    msg = (f"🚀 **CIBLE DÉTECTÉE !** 🚀\n\n"
           f"🔪 {name}\n"
           f"💰 **{p_eur:.2f}€** (`${p_usd:.2f}`)\n"
           f"📉 Float: `{wear:.5f}`\n\n"
           f"🔗 https://csfloat.com/item/{item_id}")
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        time.sleep(0.5)

if __name__ == "__main__":
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
