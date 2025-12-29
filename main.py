import os
import requests
import time

# --- CONFIGURATION VIA VARIABLES D'ENVIRONNEMENT ---
# Le script va chercher ces valeurs dans ton système
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

HEADERS = {"Authorization": CSFLOAT_API_KEY}

def send_telegram_notif(text):
    """Envoie une notification formatée à ton Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown",
        "disable_web_page_preview": False
    }
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.json()
    except Exception as e:
        print(f"❌ Erreur Telegram : {e}")

def analyze_item(item):
    """Analyse les détails du skin (float, prix)"""
    reasons = []
    item_info = item.get("item", {})
    price = item.get("price", 0) / 100
    wear = item_info.get("float_value", 0)
    
    # Calcul de la réduction si disponible
    ref_price = item.get("reference", {}).get("base_price", 0) / 100
    if ref_price > 0:
        discount = ((ref_price - price) / ref_price) * 100
        if discount > 5: # Si plus de 5% de réduction
            reasons.append(f"📉 *Prix :* -{discount:.1f}% sous le marché")
    
    reasons.append(f"🔍 *Float :* `{wear:.5f}`")
    if wear < 0.21: reasons.append("✨ *Look :* Très propre pour du FT")
    
    return "\n".join(reasons)

def is_good_deal(item):
    """Filtre les couteaux selon tes critères"""
    name = item.get("item", {}).get("market_hash_name", "")
    wear = item.get("item", {}).get("float_value", 1.0)
    
    # Critère 1 : Butterfly Ultraviolet FT (Toutes)
    if "Butterfly Knife | Ultraviolet" in name and "Field-Tested" in name:
        return True

    # Critère 2 : Butterfly Freehand (Seulement bon float)
    if "Butterfly Knife | Freehand" in name and wear <= 0.09:
        return True
            
    return False

def main():
    # Vérification des variables
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
        print("❌ Erreur : Variables d'environnement manquantes !")
        return

    print(f"🚀 Bot activé ! Surveillance lancée pour l'ID : {TELEGRAM_CHAT_ID}")
    send_telegram_notif("✅ *Le bot CSFloat est en ligne !*\nJe surveille les Butterfly Ultraviolet et Freehand pour toi.")

    seen_ids = set()
    targets = [
        "★ Butterfly Knife | Ultraviolet (Field-Tested)",
        "★ Butterfly Knife | Freehand (Factory New)",
        "★ Butterfly Knife | Freehand (Minimal Wear)"
    ]

    while True:
        for query in targets:
            try:
                params = {"limit": 10, "market_hash_name": query, "sort_by": "most_recent"}
                r = requests.get("https://csfloat.com/api/v1/listings", headers=HEADERS, params=params, timeout=10)
                
                if r.status_code != 200:
                    print(f"⚠️ Erreur API CSFloat ({r.status_code})")
                    continue

                data = r.json()
                items = data if isinstance(data, list) else data.get("data", [])

                for item in items:
                    listing_id = item["id"]
                    if listing_id not in seen_ids:
                        if is_good_deal(item):
                            analysis = analyze_item(item)
                            msg = (f"🔥 *NOUVELLE OFFRE*\n\n"
                                   f"🔪 *{item['item']['market_hash_name']}*\n"
                                   f"💰 *Prix : {item['price']/100}€*\n\n"
                                   f"📊 *Analyse :*\n{analysis}\n\n"
                                   f"🔗 [VOIR SUR CSFLOAT](https://csfloat.com/item/{listing_id})")
                            send_telegram_notif(msg)
                            print(f"🎯 Match envoyé sur Telegram : {item['item']['market_hash_name']}")
                        seen_ids.add(listing_id)
            except Exception as e:
                print(f"Erreur pendant le scan : {e}")
        
        time.sleep(60) # Attente d'une minute entre chaque tour

if __name__ == "__main__":
    main()
