import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import pandas as pd
import time
import random
import re

st.title("Ebay Scraper")
st.write("Dieser Scraper durchsucht Ebay-Kleinanzeigen nach deiner Query und speichert die Ergebnisse in einer Excel-Datei.")

# Nimmt sich das momentane Datum & formatiert es zu '[Stunde:Minute:Sekunde] - '.
now = datetime.now()
prefix = "[" + now.strftime("%H:%M:%S") + "] - "

def clean_price(price_text):
    return int(re.sub(r'[^0-9]', '', price_text)) if re.search(r'\d', price_text) else None

def get_soup(url, headers):
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return BeautifulSoup(response.content, "html.parser")
    except requests.exceptions.RequestException as e:
        print(prefix + "Fehler bei der Anfrage: ", e)
        return None

def scrape_kleinanzeigen(query):
    URL = f"https://www.kleinanzeigen.de/s-{query}/k0"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36'
    }
    
    soup = get_soup(URL, headers)
    if not soup:
        return []
    
    listings = []
    srchRslts = soup.find_all("li")
    
    for srchRslt in srchRslts:
        price_tag = srchRslt.find("strong")
        if price_tag:
            price_text = price_tag.text.strip()
            price = clean_price(price_text)
            listings.append({"Preis": price, "Verhandelbar": "VB" in price_text})
    
    return listings

def save_to_excel(data, filename="kleinanzeigen.xlsx"):
    df = pd.DataFrame(data)
    df.to_excel(filename, index=False)
    print(prefix + f"Daten gespeichert unter {filename}")

if __name__ == "__main__":
    query = input(prefix + "Bitte gebe deine Query an << ")
    print(prefix + f"Es wird nach {query} gesucht...")
    
    listings = scrape_kleinanzeigen(query)
    if listings:
        save_to_excel(listings)
        print(prefix + f"Durchschnittspreis: {sum([l['Preis'] for l in listings if l['Preis']])/len(listings):.2f} €")
    else:
        print(prefix + "Keine Ergebnisse gefunden.")
    
    time.sleep(random.uniform(3, 7))
