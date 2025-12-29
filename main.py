import os
import requests
import time

# --- CONFIGURATION ---
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
TELEGRAM_TOKEN = "TON_TOKEN_TELEGRAM"
TELEGRAM_CHAT_ID = "TON_CHAT_ID"

HEADERS = {"Authorization": CSFLOAT_API_KEY}

def send_telegram_notif(text):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Erreur Telegram : {e}")

def analyze_item(item):
    """Analyse pourquoi l'item est une bonne affaire et retourne les arguments."""
    reasons = []
    item_info = item.get("item", {})
    name = item_info.get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item_info.get("float_value", 0)
    
    # 1. Analyse du Prix vs Marché (Base Price)
    ref_price = item.get("reference", {}).get("base_price", 0) / 100
    if ref_price > 0:
        diff = ref_price - price
        discount_pct = (diff / ref_price) * 100
        if diff > 0:
            reasons.append(f"📉 *Prix :* -{discount_pct:.1f}% sous le marché ({diff:.2f}€ d'économie)")
    
    # 2. Analyse du Float (Usure)
    if wear > 0:
        reasons.append(f"🔍 *Float :* `{wear:.5f}`")
        if wear < 0.01: reasons.append("💎 *Rare :* Float exceptionnel (Top Condition)")
        elif wear < 0.08: reasons.append("✨ *Look :* Très propre (Proche FN)")

    # 3. Spécificités
    if "StatTrak™" in name:
        reasons.append("⚡ *StatTrak™ :* Comptabilise tes kills !")
    
    return "\n".join(reasons)

def is_good_deal(item):
    name = item["item"]["market_hash_name"]
    price = item["price"] / 100
    wear = item["item"].get("float_value", 1.0)
    ref_price = item.get("reference", {}).get("base_price", 0) / 100

    # Logique de filtrage stricte
    if "Butterfly Knife | Ultraviolet" in name and "Field-Tested" in name:
        if ref_price > 0 and (ref_price - price) / ref_price >= 0.02: # 2% de réduc
            return True

    if "Butterfly Knife | Freehand" in name:
        if wear <= 0.09 and price <= 1080: # Bon float ou prix barré
            return True
            
    return False

def main():
    print("🚀 Bot en ligne. Analyse détaillée activée.")
    seen_ids = set()

    targets = [
        "★ Butterfly Knife | Ultraviolet (Field-Tested)",
        "★ StatTrak™ Butterfly Knife | Ultraviolet (Field-Tested)",
        "★ Butterfly Knife | Freehand (Factory New)",
        "★ Butterfly Knife | Freehand (Minimal Wear)"
    ]

    while True:
        for query in targets:
            try:
                params = {"limit": 5, "market_hash_name": query, "sort_by": "most_recent"}
                r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
                items = r.json() if isinstance(r.json(), list) else r.json().get("data", [])

                for item in items:
                    listing_id = item["id"]
                    if listing_id not in seen_ids and is_good_deal(item):
                        # On génère l'argumentaire
                        arguments = analyze_item(item)
                        name = item['item']['market_hash_name']
                        price = item['price']/100
                        link = f"https://csfloat.com/item/{listing_id}"
                        
                        msg = (f"🔥 *NOUVELLE AFFAIRE DÉTECTÉE*\n\n"
                               f"🔪 *{name}*\n"
                               f"💰 *Prix : {price}€*\n\n"
                               f"📊 *Pourquoi c'est un bon deal ?*\n{arguments}\n\n"
                               f"🔗 [VOIR L'OFFRE ICI]({link})")
                        
                        send_telegram_notif(msg)
                        seen_ids.add(listing_id)
            except Exception as e:
                print(f"Erreur : {e}")
        
        time.sleep(60)

if __name__ == "__main__":
    main()
