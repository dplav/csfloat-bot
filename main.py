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
current_rate = 0.92  # Valeur par défaut si l'API de change échoue
last_report_id = None
seen_items = {}
total_scans_done = 0

def update_exchange_rate():
    """Récupère le taux de change réel (USD -> EUR)"""
    global current_rate
    try:
        # Utilisation d'une API gratuite et sans clé pour le taux de change
        r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
        if r.status_code == 200:
            data = r.json()
            current_rate = data['rates']['EUR']
            print(f"Mise à jour taux : 1 USD = {current_rate:.4f} EUR")
    except:
        print("Erreur mise à jour taux, conservation de l'ancien.")

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
    is_blocked = False

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=50&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 429:
                is_blocked = True
                break

            if r.status_code == 200:
                data = r.json().get("data", [])
                
                best_item = None
                for i in data:
                    current_scan_ids.add(i['id'])
                    p_usd = i['price'] / 100
                    f_val = i['item']['float_value']
                    
                    # On cherche le moins cher qui respecte ton float cible
                    if f_val <= t['max_f']:
                        if best_item is None:
                            best_item = i
                        
                        if p_usd <= t['max_p']:
                            if i['id'] not in seen_items:
                                send_urgent_alert(t['name'], p_usd, f_val, i['id'])
                                seen_items[i['id']] = {"p": p_usd}

                if best_item:
                    p_eur = (best_item['price'] / 100) * current_rate
                    f_val = best_item['item']['float_value']
                    status_lines.append(f"🎯 `{t['id']}`: {len(data)} items\n└ **{p_eur:.2f}€** | Float: `{f_val:.4f}`")
                else:
                    status_lines.append(f"❌ `{t['id']}`: Aucun item < {t['max_f']}")
            else:
                status_lines.append(f"⚠️ `{t['id']}`: Erreur {r.status_code}")
        except:
            status_lines.append(f"📡 `{t['id']}`: Timeout")

    if is_blocked:
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": "🛑 Bloqué (429). Pause 10min."})
        time.sleep(600)
        return

    total_scans_done += 1
    # Mise à jour du taux toutes les 100 scans pour ne pas spammer l'API de change
    if total_scans_done % 100 == 0:
        update_exchange_rate()

    # Nettoyage des vendus
    sold_ids = [sid for sid in seen_items if sid not in current_scan_ids]
    for sid in sold_ids: del seen_items[sid]

    update_report(status_lines)

def update_report(lines):
    global last_report_id
    text = (f"🛡️ **SNIPER v1.14** | `{datetime.now().strftime('%H:%M:%S')}`\n"
            f"📈 Scans: `{total_scans_done}` | Taux: `1$={current_rate:.3f}€`\n"
            f"--- \n" + "\n".join(lines))
    
    if last_report_id is None:
        res = send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"})
        if res and res.get("ok"): last_report_id = res['result']['message_id']
    else:
        send_telegram_request("editMessageText", {"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown"})

def send_urgent_alert(name, p_usd, wear, item_id):
    p_eur = p_usd * current_rate
    msg = (f"🚀 **CIBLE DÉTECTÉE !** 🚀\n\n"
           f"🔪 {name}\n"
           f"💰 **{p_eur:.2f}€**\n"
           f"📉 Float: `{wear:.5f}`\n\n"
           f"🔗 https://csfloat.com/item/{item_id}")
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg})
        time.sleep(0.5)

if __name__ == "__main__":
    update_exchange_rate() # Premier taux au démarrage
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
