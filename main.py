import os
import requests
import smtplib
from email.mime.text import MIMEText

CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

EMAIL_FROM = os.getenv("EMAIL_FROM")
EMAIL_TO = os.getenv("EMAIL_TO")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

SEEN_FILE = "seen.txt"

HEADERS = {
    "Authorization": f"Bearer {CSFLOAT_API_KEY}"
}

def load_seen():
    if not os.path.exists(SEEN_FILE):
        return set()
    with open(SEEN_FILE, "r") as f:
        return set(f.read().splitlines())

def save_seen(seen):
    with open(SEEN_FILE, "w") as f:
        f.write("\n".join(seen))

def send_email(subject, body):
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = EMAIL_FROM
    msg["To"] = EMAIL_TO

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
        server.login(EMAIL_FROM, EMAIL_PASSWORD)
        server.send_message(msg)

def fetch_listings():
    url = "https://csfloat.com/api/v1/listings"
    params = {
        "limit": 50,
        "sort_by": "created_at",
        "order": "desc"
    }
    r = requests.get(url, headers=HEADERS, params=params, timeout=10)
    return r.json().get("data", [])

def is_good_deal(item):
    name = item["item"]["market_hash_name"]
    price = item["price"] / 100
    market = item.get("reference", {}).get("price", 0) / 100

    if "Butterfly Knife | Ultraviolet" in name and item["item"]["wear"] == "Field-Tested":
        if market > 0:
            discount = (market - price) / market * 100
            return 1.0 <= discount <= 2.0

    if "Butterfly Knife | Freehand" in name:
        wear = item["item"]["float_value"]
        if wear <= 0.08 and price <= 1000:
            return True

    return False

def main():
    seen = load_seen()
    listings = fetch_listings()

    for item in listings:
        listing_id = str(item["id"])
        if listing_id in seen:
            continue

        if is_good_deal(item):
            name = item["item"]["market_hash_name"]
            price = item["price"] / 100
            url = f"https://csfloat.com/item/{listing_id}"

            body = f"{name}\nPrix: {price}€\nLien: {url}"
            send_email("CSFloat – Bonne affaire détectée", body)

        seen.add(listing_id)

    save_seen(seen)

if __name__ == "__main__":
    main()


