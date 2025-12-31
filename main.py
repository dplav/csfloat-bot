import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_INTERVAL = 30 # Réduit à 30s pour être plus rapide
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
    
    # Cibles avec tes limites strictes
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 615.00, "max_f": 0.2300, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 570.00, "max_f": 0.3800, "id": "ST_FT"}
    ]
    
    status_lines = []

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit=30&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            if r.status_code == 200:
                data = r.json().get("data", [])
                
                # Filtrage des items valides selon tes critères
                valid_items = [i for i in data if i['item']['float_value'] <= t['max_f']]
                
                if valid_items:
                    # AMÉLIORATION DASHBOARD : On trie pour trouver le "Best Value"
                    # On cherche le float le plus bas parmi les prix les plus bas
                    best_by_price = sorted(valid_items, key=lambda x: (x['price'], x['item']['float_value']))
                    best_item = best_by_price[0]
                    
                    p_eur = (best_item['price'] / 100) * current_rate
                    f_raw = best_item['item']['float_value']
                    i_id = best_item['id']
                    
                    # Alerte urgente si nouveau
                    if p_eur <= t['max_p'] and i_id not in seen_items:
                        send_urgent_alert(t['name'], (best_item['price']/100), f_raw, i_id)
                        seen_items[i_id] = {"p": p_eur}

                    # Texte du Dashboard amélioré
                    lum_status = "✨ TOP LUMINOSITÉ" if f_raw < 0.20 else "🔆 Moyen"
                    status_lines.append(
                        f"🎯 `{t['id']}`: {len(valid_items)} valides\n"
                        f"└ [**{p_eur:.2f}€**](https://csfloat.com/item/{i_id}) | f: `{f_raw:.4f}` | {lum_status}"
                    )
                else:
                    status_lines.append(f"❌ `{t['id']}`: Aucun (f < {t['max_f']})")
        except Exception as e:
            status_lines.append(f"📡 `{t['id']}`: Erreur Connexion")

    total_scans_done += 1
    update_report(status_lines)

def update_report(lines):
    global last_report_id
    text = (f"🛡️ **SNIPER INTELLIGENT v1.25**\n"
            f"🕒 Scan : `{datetime.now().strftime('%H:%M:%S')}`\n"
            f"📈 Scans : `{total_scans_done}` | Taux : `{current_rate}`\n"
            f"--- \n" + "\n".join(lines))
    
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_web_page_preview": True}
    
    if last_report_id:
        send_telegram_request("editMessageText", {**payload, "message_id": last_report_id})
    else:
        res = send_telegram_request("sendMessage", payload)
        if res: last_report_id = res.get('result', {}).get('message_id')

def send_urgent_alert(name, p_usd, wear, item_id):
    p_eur = p_usd * current_rate
    
    analysis = ""
    if "Ultraviolet" in name:
        if p_eur < 510:
            analysis = "🚀 **Excellente Affaire**\n_Rare, mais arrive (ex: le 0.18 à 515€ était déjà une pépite)._"
        elif 515 <= p_eur <= 535:
            analysis = "✅ **Bon Prix (Achat)**\n_Plusieurs ventes à 515€ et 533€ (0.15 et 0.18). C'est ton prix cible._"
        elif 540 <= p_eur <= 560:
            analysis = "⚖️ **Prix Normal**\n_Le gros du marché. À 553€ tu en trouves régulièrement._"
    
    elif "Stained" in name:
        # Analyse spéciale Stained (Priorité Luminosité)
        if wear < 0.20:
            analysis = "💎 **STAINED - TOP LUMINOSITÉ**\n_Float exceptionnel, sera très brillant en jeu !_"
        elif p_eur < 510:
            analysis = "💰 **PRIX PLANCHER STAINED**\n_Bon investissement pour flip rapide._"

    msg = (f"{analysis}\n\n"
           f"🔪 {name}\n"
           f"💰 **{p_eur:.2f}€**\n"
           f"📉 Float: `{wear:.10f}`\n"
           f"🔗 [SNAPER MAINTENANT](https://csfloat.com/item/{item_id})")
    
    for _ in range(3):
        send_telegram_request("sendMessage", {"chat_id": TELEGRAM_CHAT_ID, "text": msg, "parse_mode": "Markdown"})
        time.sleep(0.3)

if __name__ == "__main__":
    while True:
        get_market_data()
        time.sleep(SCAN_INTERVAL)
