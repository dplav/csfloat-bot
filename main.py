import os
import requests
import time
import sys
import nacl.signing
from datetime import datetime

# Force l'affichage des logs sur Railway
sys.stdout.reconfigure(line_buffering=True)

# --- CONFIGURATION ---
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = "6116293616"
CSFLOAT_API_KEY = os.getenv("CSFLOAT_API_KEY")

# Identifiants DMarket via Variables Railway
DMARKET_PUB = os.getenv("DMARKET_PUBLIC_KEY") 
DMARKET_SEC = os.getenv("DMARKET_SECRET_KEY")

# Recherches spécifiques CSFloat (Syntaxe Smart Filter)
RECHERCHES_CS = [
    "Butterfly Knife Ultraviolet <585€ newest",
    "Butterfly Knife Stained <550€ newest"
]

def update_status(text):
    """Envoie un message de statut silencieux sur Telegram"""
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID, 
        "text": text, 
        "parse_mode": "Markdown", 
        "disable_notification": True
    }
    try:
        r = requests.post(url, json=payload).json()
        return r.get("result", {}).get("message_id")
    except:
        return None

def delete_message(msg_id):
    """Supprime le message de statut précédent"""
    if msg_id:
        url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/deleteMessage"
        requests.post(url, json={"chat_id": TELEGRAM_CHAT_ID, "message_id": msg_id})

def is_good_deal(name, price, wear):
    """Critères de sélection Ultraviolet et Stained"""
    # Butterfly Ultraviolet (Field-Tested)
    if "Ultraviolet" in name and "Field-Tested" in name:
        if price <= 520: return True
        if wear <= 0.16 and price <= 580: return True
    
    # Butterfly Stained (Field-Tested)
    if "Stained" in name and "Field-Tested" in name:
        if price <= 545 and wear <= 0.30: return True
        
    return False

def scan_csfloat():
    """Scan des annonces sur CSFloat"""
    headers = {"Authorization": CSFLOAT_API_KEY}
    for query in RECHERCHES_CS:
        params = {"limit": 30, "full_text": query, "sort_by": "most_recent"}
        try:
            r = requests.
