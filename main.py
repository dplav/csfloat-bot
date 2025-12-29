import os
import requests
import smtplib
import time
from email.mime.text import MIMEText

# Configuration (Assure-toi que ces variables d'environnement sont bien définies)
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD") # Utilise un "Mot de passe d'application" Gmail

SEEN_FILE = "seen.txt"
HEADERS = {"Authorization": CSFLOAT_API_KEY} # CSFloat utilise souvent la clé brute ou Bearer

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(f.read().splitlines())

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        f.write("\n".join(list(seen)[-1000:])) # Garde les 1000 derniers pour éviter un fichier trop gros

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(EMAIL_FROM, EMAIL_PASSWORD)
            server.send_message(msg)
            print("✅ E-mail de notification envoyé !")
    except Exception as e:
        print(f"❌ Erreur lors de l'envoi de l'e-mail : {e}")

def fetch_listings(query):
    url = "https://csfloat.com/api/v1/listings"
    params = {
        "limit": 10,
        "sort_by": "most_recent",
        "market_hash_name": query
    }
    try:
        r = requests.get(url, headers=HEADERS, params=params, timeout=15)
        r.raise_for_status()
        return r.json() # CSFloat renvoie directement une liste ou un objet selon l'endpoint
    except Exception as e:
        print(f"❌ Erreur API ({query}) : {e}")
        return []

def is_good_deal(item):
    item_info = item.get("item", {})
    name = item_info.get("market_hash_name", "")
    price = item.get("price", 0) / 100
    
    # Cas 1 : Butterfly Ultraviolet FT avec réduction
    if "Butterfly Knife | Ultraviolet" in name and item_info.get("wear_name") == "Field-Tested":
        market_ref = item.get("reference", {}).get("base_price", 0) / 100
        if market_ref > 0:
            discount = ((market_ref - price) / market_ref) * 100
            if 1.0 <= discount <= 5.0: # J'ai élargi à 5% pour tes tests
                return True

    # Cas 2 : Butterfly Freehand avec Float bas
    if "Butterfly Knife | Freehand" in name:
        float_val = item_info.get("float_value", 1.0)
        if float_val <= 0.08 and price <= 1000:
            return True

    return False

def main():
    print("🚀 Bot démarré... Surveillance en cours.")
    seen = load_seen()
    
    # Liste des skins à surveiller spécifiquement
    targets = [
        "★ Butterfly Knife | Ultraviolet (Field-Tested)",
        "★ Butterfly Knife | Freehand (Factory New)",
        "★ Butterfly Knife | Freehand (Minimal Wear)"
    ]

    while True:
        for target in targets:
            listings = fetch_listings(target)
            
            # Note: selon l'API, c'est soit une liste directe, soit dans .get("data")
            items = listings if isinstance(listings, list) else listings.get("data", [])

            for item in items:
                listing_id = str(item["id"])
                if listing_id in seen:
                    continue

                if is_good_deal(item):
                    name = item["item"]["market_hash_name"]
                    price = item["price"] / 100
                    url = f"https://csfloat.com/item/{listing_id}"
                    
                    print(f"🎯 Affaire trouvée : {name} à {price}€")
                    body = f"Nouvelle offre détectée !\n\nNom: {name}\nPrix: {price}€\nLien: {url}"
                    send_email(f"🔥 PROMO CSFLOAT: {name}", body)

                seen.add(listing_id)
        
        save_seen(seen)
        time.sleep(60) # Attend 1 minute avant de recommencer

if __name__ == "__main__":
    main()
