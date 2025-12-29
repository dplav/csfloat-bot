import os
import requests
import smtplib
import time
from email.mime.text import MIMEText

# --- CONFIGURATION ---
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

SEEN_FILE = "seen.txt"
HEADERS = {"Authorization": CSFLOAT_API_KEY}

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        # On essaie le port 465 (SSL) si le 587 ne marche pas
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=15) as server:
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
            print("✅ E-mail envoyé avec succès !")
    except Exception as e:
        print(f"❌ Erreur critique Email : {e}")
        print("💡 Conseil : Si tu es sur un hébergeur gratuit, ils bloquent souvent les mails.")

def is_good_deal(item):
    item_info = item.get("item", {})
    name = item_info.get("market_hash_name", "")
    price = item.get("price", 0) / 100
    
    # Vérification StatTrak (Optionnel selon tes goûts)
    is_stattrak = "StatTrak™" in name

    # Critère 1 : Butterfly Ultraviolet FT
    if "Butterfly Knife | Ultraviolet" in name and item_info.get("wear_name") == "Field-Tested":
        ref_price = item.get("reference", {}).get("base_price", 0) / 100
        if ref_price > 0:
            discount = ((ref_price - price) / ref_price) * 100
            # On accepte StatTrak ou non, tant que le prix est bon
            if 1.0 <= discount <= 10.0: 
                return True

    # Critère 2 : Butterfly Freehand (FN ou MW)
    if "Butterfly Knife | Freehand" in name:
        float_val = item_info.get("float_value", 1.0)
        # On accepte les bonnes affaires même en StatTrak ici
        if float_val <= 0.08 and price <= 1100:
            return True

    return False

def fetch_listings(query):
    url = "https://csfloat.com/api/v1/listings"
    params = {"limit": 5, "sort_by": "most_recent", "market_hash_name": query}
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=10)
        return r.json() if isinstance(r.json(), list) else r.json().get("data", [])
    except:
        return []

def main():
    print("🕵️ Surveillance active (Incluant StatTrak)...")
    if not all([EMAIL_FROM, EMAIL_PASSWORD, CSFLOAT_API_KEY]):
        print("⚠️ Attention : Variables d'environnement manquantes !")
    
    seen = set() # On peut charger le fichier ici si besoin

    targets = [
        "★ Butterfly Knife | Ultraviolet (Field-Tested)",
        "★ StatTrak™ Butterfly Knife | Ultraviolet (Field-Tested)",
        "★ Butterfly Knife | Freehand (Factory New)",
        "★ Butterfly Knife | Freehand (Minimal Wear)",
        "★ StatTrak™ Butterfly Knife | Freehand (Factory New)"
    ]

    while True:
        for target in targets:
            items = fetch_listings(target)
            for item in items:
                listing_id = str(item["id"])
                if listing_id not in seen and is_good_deal(item):
                    name = item["item"]["market_hash_name"]
                    price = item["price"] / 100
                    print(f"🎯 Trouvé : {name} à {price}€")
                    send_email(f"🔥 DEAL: {name}", f"Prix: {price}€\nLien: https://csfloat.com/item/{listing_id}")
                    seen.add(listing_id)
        
        time.sleep(60)

if __name__ == "__main__":
    main()
