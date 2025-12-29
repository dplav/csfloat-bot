import os
import requests
import time

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

HEADERS = {"Authorization": CSFLOAT_API_KEY}
BUDGET_MAX = 600

def send_telegram(text, image_url=None):
    """Envoie un message avec photo si disponible, sinon texte seul"""
    base_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}"
    
    try:
        if image_url:
            url = f"{base_url}/sendPhoto"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "photo": image_url, "caption": text, "parse_mode": "Markdown"}
        else:
            url = f"{base_url}/sendMessage"
            payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
        
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"❌ Erreur Telegram : {e}")

def is_good_deal(item):
    """Logique de tri selon tes critères précis"""
    name = item.get("item", {}).get("market_hash_name", "")
    price = item.get("price", 0) / 100
    wear = item.get("item", {}).get("float_value", 1.0)
    
    # Filtre de budget global
    if price > BUDGET_MAX:
        return False

    # 1. Butterfly Ultraviolet (Field-Tested)
    if "Butterfly Knife | Ultraviolet" in name and "Field-Tested" in name:
        if price <= 515: return True # Snipe pur
        if wear <= 0.16 and price <= 585: return True # Top Float

    # 2. Butterfly Freehand
    if "Butterfly Knife | Freehand" in name:
        if "(Factory New)" in name and price <= 600: return True
        if "(Minimal Wear)" in name and price <= 575: return True

    # 3. Butterfly Case Hardened (Recherche de Bleu)
    if "Case Hardened" in name:
        # On accepte tout CH sous 540€ (Snipe)
        if price <= 540: return True
        # Si CSFloat détecte un pattern rare (Blue Gem / Tier 1-2)
        if item.get("item", {}).get("is_blue_gem", False): return True
        # Si le pourcentage de bleu est mentionné dans les tags (si dispo)
        for tag in item.get("item", {}).get("tags", []):
            if "Blue" in tag.get("name", "") and "40%" in tag.get("name", ""):
                return True
                
    return False

def main():
    if not TELEGRAM_TOKEN or not CSFLOAT_API_KEY:
        print("❌ Erreur : Variables d'environnement manquantes !")
        return

    print(f"🚀 Sniper Bot en ligne (Budget: {BUDGET_MAX}€)")
    send_telegram(f"✅ *Sniper Bot Activé*\nSurveillance : UV FT (<515€), Freehand, et Case Hardened Bleu.\nBudget Max : {BUDGET_MAX}€")

    seen_ids = set()
    # On utilise des mots-clés plus larges pour ne rien rater
    queries = [
        "Butterfly Knife | Ultraviolet",
        "Butterfly Knife | Freehand",
        "Butterfly Knife | Case Hardened"
    ]

    while True:
        for q in queries:
            try:
                params = {"limit": 15, "market_hash_name": q, "sort_by": "most_recent"}
                r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
                
                if r.status_code != 200: continue
                
                items = r.json()
                if not isinstance(items, list): items = items.get("data", [])

                for item in items:
                    listing_id = item["id"]
                    if listing_id not in seen_ids:
                        if is_good_deal(item):
                            # Construction de l'alerte
                            name = item['item']['market_hash_name']
                            price = item['price']/100
                            wear = item['item']['float_value']
                            img = item['item'].get('screenshot', item['item'].get('image'))
                            
                            msg = (f"🔥 *OFFRE DÉTECTÉE*\n\n"
                                   f"🔪 *{name}*\n"
                                   f"💰 *Prix : {price}€*\n"
                                   f"🔍 *Float :* `{wear:.5f}`\n\n"
                                   f"🔗 [Ouvrir sur CSFloat](https://csfloat.com/item/{listing_id})")
                            
                            send_telegram(msg, image_url=img)
                            print(f"🎯 Alerte envoyée pour : {name}")
                        
                        seen_ids.add(listing_id)
            except Exception as e:
                print(f"Erreur scan : {e}")
        
        # On attend 45 secondes pour ne pas être banni par l'API
        time.sleep(45)

if __name__ == "__main__":
    main()
