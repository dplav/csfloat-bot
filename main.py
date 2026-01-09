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
    Logique de décision personnalisée pour chaque item.
    """
    # --- LOGIQUE SPORT GLOVES | SLINGSHOT FT ---
    # En FT, le Slingshot varie de 0.15 à 0.38. 
    # Le "look" change radicalement sous 0.20.
    if "Slingshot" in name:
        if wear <= 0.18: # Top Float (proche MW)
            if price_eur <= 450: return "💎 GOD TIER FLOAT/PRIX", "✨", True
            return "✅ TOP FLOAT (MW LOOK)", "✔️", True
        
        if price_eur < 360: # Prix plancher (Liquid)
            return "🚀 PRIX LIQUIDE (FLIP RAPIDE)", "✨", True
        elif 360 <= price_eur <= 390:
            return "✅ BON PRIX", "✔️", True
        else:
            return "❌ TROP CHER (STANDART)", "🗑️", False

    # --- LOGIQUE IMPERIAL PLAID MW ---
    elif "Imperial Plaid" in name:
        if wear <= 0.099:
            if price_eur <= 750: return "💎 TOP FLOAT (ULTRA RARE)", "✨", True
            return "✅ TOP FLOAT", "✔️", False
        if wear < 0.125:
            if price_eur <= 590: return "🚀 EXCELLENT PRIX/FLOAT", "✨", True
            return "⚖️ PRIX CORRECT", "✔️", False
        if price_eur < 555: return "🔥 PRIX LIQUIDE", "✨", True
        return "❌ MAUVAIS (TROP USÉ/CHÈRE)", "🗑️", False
            
    return "ANALYSE...", "", False

def get_market_data():
    global last_report_id, total_scans_done
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    # Liste de tes cibles avec leurs limites de scan respectives
    targets = [
        {"name": "★ Sport Gloves | Slingshot (Field-Tested)", "max_f": 0.38, "id": "SLING_FT"},
        {"name": "★ Driver Gloves | Imperial Plaid (Minimal Wear)", "max_f": 0.15, "id": "PLAID_MW"}
    ]
    
    status_lines = []

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=10&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                if data:
                    # On prend le moins cher qui respecte le float max
                    valid = [i for i in data if i['item']['float_value'] <= t['max_f']]
                    if valid:
                        best = valid[0]
                        p_eur = (best['price'] / 100) * current_rate
                        f_raw = best['item']['float_value']
                        i_id = best['id']
                        
                        status_text, emoji, is_alert = analyze_deal(t['name'], p_eur, f_raw)
                        
                        if is_alert and i_id not in seen_items:
                            send_urgent_alert(t['name'], p_eur, f_raw, i_id, status_text)
                            seen_items[i_id] = {"p": p_eur}

                        status_lines.append(
                            f"🎯 `{t['id']}`: [**{p_eur:.2f}€**](https://csfloat.com/item/{i_id}) | f: `{f_raw:.4f}`\n"
                            f"└ {emoji} {status_text}"
                        )
                    else: status_lines.append(f"❌ `{t['id']}`: Aucun float valide")
                else: status_lines.append(f"❌ `{t['id']}`: Vide")
        except:
            status_lines.append(f"📡 `{t['id']}`: Erreur Connexion")

    total_scans_done += 1
    update_report(status_lines)

def update_report(lines):
    global last_report_id
    text = (f"🧤 **MULTI-SNIPER v2.0**\n"
            f"🕒 `{datetime.now().strftime('%H:%M:%S')}` | Scans : `{total_scans_done}`\n"
            f"--- \n" + "\n".join(lines))
    
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    if last_report_id:
        send_telegram_request("editMessageText", {**payload, "message_id": last_report_id})
    else:
        res = send_telegram_request("sendMessage", payload)
        if res: last_report_id = res.get('result', {}).get('message_id')

def send_urgent_alert(name, p_eur, wear, item_id, label):
    msg = (f"🚨 {label} 🚨\n\n"
           f"🧤 {name}\n"
           f"💰 **{p_eur:.2f}€** | Float: `{wear:.10f}`\n"
           f"🔗 [ACHETER](https://csfloat.com/item/{item_id})")
    
    for _ in range(3): # Les 3 notifications pour être sûr de ne pas rater le deal
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        time.sleep(0.4)

if __name__ == "__main__":
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
