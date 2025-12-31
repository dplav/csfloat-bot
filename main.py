import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres globaux
SCAN_INTERVAL = 30 
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

def analyze_deal(name, price_eur, wear):
    """
    Logique de décision : Filtre les mauvaises affaires et 
    déclenche les alertes pour les pépites.
    """
    if "Ultraviolet" in name:
        # EXCEPTION : Top Float (Look proche du Minimal Wear)
        if wear <= 0.19 and price_eur <= 565:
            return "💎 TOP FLOAT (LOOK MW)", "✨", True
        
        # LOGIQUE STANDARD UV FT (Limite 0.24)
        if price_eur < 510:
            return "🚀 EXCELLENTE AFFAIRE", "✨", True
        elif 510 <= price_eur <= 535:
            return "✅ BON PRIX (ACHAT)", "✔️", True
        elif 536 <= price_eur <= 560:
            return "⚖️ MOYEN", "⚠️", False
        else:
            return "❌ MAUVAIS (TROP CHER)", "🗑️", False

    elif "Stained" in name:
        # LOGIQUE STAINED FT (Prix max 520€)
        if wear < 0.20 and price_eur <= 520:
            return "💎 STAINED TOP LUMINOSITÉ", "✨", True
        elif price_eur < 510:
            return "✅ BON PRIX (FLIP)", "✔️", True
        elif 511 <= price_eur <= 525:
            return "⚖️ MOYEN", "⚠️", False
        else:
            return "❌ MAUVAIS", "🗑️", False
            
    return "ANALYSE...", "", False

def get_market_data():
    global last_report_id, total_scans_done
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # Cibles mises à jour
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.00, "max_f": 0.2400, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 525.00, "max_f": 0.3800, "id": "ST_FT"}
    ]
    
    status_lines = []

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=30&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # Filtrage selon tes critères de float
                valid_items = [i for i in data if i['item']['float_value'] <= t['max_f']]
                
                if valid_items:
                    # Tri pour trouver la meilleure offre (Prix puis Float)
                    valid_items.sort(key=lambda x: (x['price'], x['item']['float_value']))
                    best_item = valid_items[0]
                    
                    p_eur = (best_item['price'] / 100) * current_rate
                    f_raw = best_item['item']['float_value']
                    i_id = best_item['id']
                    
                    # Analyse du Deal
                    status_text, emoji, is_alert = analyze_deal(t['name'], p_eur, f_raw)
                    
                    # Envoi de l'alerte urgente (3x notification)
                    if is_alert and i_id not in seen_items:
                        send_urgent_alert(t['name'], p_eur, f_raw, i_id, status_text)
                        seen_items[i_id] = {"p": p_eur}

                    # Ligne pour le Dashboard
                    status_lines.append(
                        f"🎯 `{t['id']}`: {len(valid_items)} valides\n"
                        f"└ [**{p_eur:.2f}€**](https://csfloat.com/item/{i_id}) | f: `{f_raw:.4f}` | {emoji} {status_text}"
                    )
                else:
                    status_lines.append(f"❌ `{t['id']}`: Aucun (f < {t['max_f']})")
        except:
            status_lines.append(f"📡 `{t['id']}`: Erreur Connexion")

    total_scans_done += 1
    update_report(status_lines)

def update_report(lines):
    global last_report_id
    text = (f"🛡️ **SNIPER INTELLIGENT v1.30**\n"
            f"🕒 Scan : `{datetime.now().strftime('%H:%M:%S')}`\n"
            f"📈 Scans : `{total_scans_done}` | Taux : `{current_rate}`\n"
            f"--- \n" + "\n".join(lines))
    
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    
    if last_report_id:
        send_telegram_request("editMessageText", {**payload, "message_id": last_report_id})
    else:
        res = send_telegram_request("sendMessage", payload)
        if res: last_report_id = res.get('result', {}).get('message_id')

def send_urgent_alert(name, p_eur, wear, item_id, label):
    msg = (f"{label}\n\n"
           f"🔪 {name}\n"
           f"💰 **{p_eur:.2f}€**\n"
           f"📉 Float: `{wear:.10f}`\n"
           f"🔗 [SNIPER MAINTENANT](https://csfloat.com/item/{item_id})")
    
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        time.sleep(0.3)

if __name__ == "__main__":
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
