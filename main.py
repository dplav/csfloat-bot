import os
import requests
import time
from datetime import datetime

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
API_KEY = os.getenv("CSFLOAT_API_KEY", "").replace('"', '').replace("'", "").strip()

# Paramètres
SCAN_LIMIT = 50
CHECK_INTERVAL = 30
last_report_id = None
last_update_id = 0  # Pour ne pas lire deux fois le même message Telegram

# Mémoire des items (ID: {price, name})
seen_items = {}

def get_updates():
    """Récupère les commandes /test envoyées au bot"""
    global last_update_id
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getUpdates?offset={last_update_id + 1}"
    try:
        r = requests.get(url, timeout=5).json()
        for update in r.get("result", []):
            last_update_id = update["update_id"]
            msg = update.get("message", {}).get("text", "")
            if msg == "/test1":
                trigger_test(1)
            elif msg == "/test3":
                trigger_test(3)
    except:
        pass

def trigger_test(count):
    """Force une alerte sur les X premiers items du marché pour tester le son"""
    headers = {"Authorization": API_KEY}
    url = f"https://csfloat.com/api/v1/listings?market_hash_name=★ Butterfly Knife | Stained (Field-Tested)&limit={count}&sort_by=lowest_price"
    try:
        data = requests.get(url, headers=headers).json().get("data", [])
        for i in data:
            send_urgent_alert(i['item']['market_hash_name'], i['price']/100, i['item']['float_value'], i['id'], is_test=True)
    except:
        send_telegram_msg("❌ Erreur lors du test.")

def get_market_data():
    global last_report_id
    headers = {"Authorization": API_KEY, "User-Agent": "Mozilla/5.0"}
    
    targets = [
        {"name": "★ Butterfly Knife | Ultraviolet (Field-Tested)", "max_p": 565.99, "max_f": 0.2409, "id": "UV_FT"},
        {"name": "★ Butterfly Knife | Stained (Field-Tested)", "max_p": 520.00, "max_f": 1.0, "id": "ST_FT"},
        {"name": "★ Butterfly Knife | Stained (Well-Worn)", "max_p": 480.00, "max_f": 1.0, "id": "ST_WW"}
    ]
    
    status_data = []
    current_scan_ids = set()

    for t in targets:
        url = f"https://csfloat.com/api/v1/listings?market_hash_name={t['name']}&limit={SCAN_LIMIT}&sort_by=lowest_price&type=buy_now"
        try:
            r = requests.get(url, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json().get("data", [])
                low_p = data[0]['price'] / 100 if data else 0
                status_data.append(f"📍 {t['id']}: {len(data)} vus | Min: ${low_p}")

                for i in data:
                    item_id = i['id']
                    current_scan_ids.add(item_id)
                    price = i['price'] / 100
                    wear = i.get('item', {}).get('float_value', 0)

                    if price <= t['max_p'] and wear <= t['max_f']:
                        if item_id not in seen_items:
                            send_urgent_alert(t['name'], price, wear, item_id)
                            seen_items[item_id] = {"price": price, "name": t['name']}
            else:
                status_data.append(f"❌ {t['id']}: Erreur {r.status_code}")
        except:
            status_data.append(f"⚠️ {t['id']}: Timeout")

    check_sold_items(current_scan_ids)
    update_report(status_data)

def check_sold_items(current_ids):
    sold_ids = []
    for sid in list(seen_items.keys()):
        if sid not in current_ids:
            item = seen_items[sid]
            send_telegram_msg(f"✅ **VENDU / RETIRÉ**\n{item['name']} à ${item['price']}")
            sold_ids.append(sid)
    for sid in sold_ids:
        del seen_items[sid]

def update_report(lines):
    global last_report_id
    text = f"📊 **STATUT SNIPER** ({datetime.now().strftime('%H:%M:%S')})\n" + "\n".join(lines)
    text += f"\n\n⚙️ `/test1` | `/test3` pour tester le son."
    
    if last_report_id is None:
        res = send_telegram_msg(text, silent=True)
        if res: last_report_id = res.get('result', {}).get('message_id')
    else:
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/editMessageText", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "message_id": last_report_id, "text": text, "parse_mode": "Markdown"})

def send_urgent_alert(name, price, wear, item_id, is_test=False):
    prefix = "🧪 [TEST] " if is_test else "🚀 "
    url = f"https://csfloat.com/item/{item_id}"
    msg = f"{prefix}**CIBLE DÉTECTÉE !**\n\n🔪 {name}\n💰 **${price:.2f}**\n📉 Float: `{wear:.5f}`\n\n🔗 [ACHETER]({url})"
    for _ in range(3):
        send_telegram_msg(msg)

def send_telegram_msg(text, silent=False):
    try:
        r = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage", 
                      json={"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown", "disable_notification": silent})
        return r.json()
    except: return None

if __name__ == "__main__":
    print("Sniper Pro v1.1 démarré...")
    while True:
        get_updates() # Vérifie si tu as envoyé /test1 ou /test3
        get_market_data() # Analyse le marché
        time.sleep(5) # Pause courte pour plus de réactivité sur les commandes
