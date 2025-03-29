import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import pandas as pd
import time
import random
import re

st.title("Ebay Scraper")

st.write("Dieser Scraper durchsucht Ebay-Kleinanzeigen nach deiner Query und speichert die Ergebnisse in einer Excel-Datei.")

# Eingabe für den vorgefertigten Link
custom_url = st.text_input("Füge einen vorgefertigten Link ein (optional)")

# Eingabe für die Query
query = st.text_input("Bitte gebe deine Query an")

# Dropdown-Menü für die Kategorie
category = st.selectbox("Kategorie", ["autos", "immobilien"])

# Dropdown-Menü für das Bundesland
states = ["", "Baden-Württemberg", "Bayern", "Berlin", "Brandenburg", "Bremen", "Hamburg", "Hessen", "Mecklenburg-Vorpommern", "Niedersachsen", "Nordrhein-Westfalen", "Rheinland-Pfalz", "Saarland", "Sachsen", "Sachsen-Anhalt", "Schleswig-Holstein", "Thüringen"]
state = st.selectbox("Bundesland (optional)", states)

# Eingabe für den Anbieter
provider = st.selectbox("Anbieter", ["", "privat", "gewerblich"])

# Eingabe für den Preisbereich
price_min = st.number_input("Mindestpreis (optional)", min_value=0, step=1000)
price_max = st.number_input("Höchstpreis (optional)", min_value=0, step=1000)

# Eingabe für das Baujahr
year_min = st.number_input("Mindestbaujahr (optional)", min_value=1900, step=1, format="%d", value=None)
year_max = st.number_input("Höchstbaujahr (optional)", min_value=1900, step=1, format="%d", value=None)

# Eingabe für den Kilometerstand
km_min = st.number_input("Mindestkilometerstand (optional)", min_value=0, step=1000)
km_max = st.number_input("Höchstkilometerstand (optional)", min_value=0, step=1000)

# Eingabe für die Leistung
power_min = st.number_input("Mindestleistung (optional)", min_value=0, step=10)
power_max = st.number_input("Höchstleistung (optional)", min_value=0, step=10)

# Dropdown-Menü für den Karosserietyp
car_type = st.selectbox("Karosserietyp (optional)", ["", "coupe", "cabrio", "kombi"])

# Eingabe für das Startdatum und die Startzeit
start_date = st.date_input("Startdatum")
start_time = st.time_input("Startzeit")

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

def generate_url(query, category, state, provider, price_min, price_max, year_min, year_max, km_min, km_max, power_min, power_max, car_type):
    base_url = f"https://www.kleinanzeigen.de/s-{category}"
    query = query.replace(" ", "-")
    url = f"{base_url}/anzeige:angebote/{query}"
    
    if state:
        url += f"/{state}"
    if provider:
        url += f"/anbieter:{provider}"
    if price_min or price_max:
        url += f"/preis:{price_min}:{price_max}"
    
    if year_min is not None or year_max is not None:
        url += f"+autos.ez_i:{year_min if year_min is not None else ''}%2C{year_max if year_max is not None else ''}"
    if km_min > 0 or km_max > 0:
        url += f"+autos.km_i:{km_min}%2C{km_max}"
    if power_min > 0 or power_max > 0:
        url += f"+autos.power_i:{power_min}%2C{power_max}"
    if car_type:
        url += f"+autos.typ_s:{car_type}"
    
    if category == "autos":
        url += "/k0c216"
    else:
        url += "/k0"
    
    return url

def scrape_kleinanzeigen(url):
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/84.0.4147.125 Safari/537.36'
    }
    
    soup = get_soup(url, headers)
    if not soup:
        return []
    
    # Debugging: HTML-Inhalt der Seite ausgeben
    st.text_area("HTML-Inhalt der Seite", soup.prettify(), height=300)

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

if st.button("Scraper starten"):
    start_datetime = datetime.combine(start_date, start_time)
    wait_time = (start_datetime - datetime.now()).total_seconds()
    
    if wait_time > 0:
        st.write(f"Der Scraper startet in {wait_time} Sekunden...")
        time.sleep(wait_time)
    
    if custom_url:
        url = custom_url
        st.write(prefix + f"Es wird nach den Ergebnissen des Custom-Links gesucht: {custom_url}")
    else:
        url = generate_url(query, category, state, provider, price_min, price_max, year_min, year_max, km_min, km_max, power_min, power_max, car_type)
        st.write(prefix + f"Es wird nach {query} gesucht...")
    
    listings = scrape_kleinanzeigen(url)
    if listings:
        save_to_excel(listings)
        st.write(prefix + f"Durchschnittspreis: {sum([l['Preis'] for l in listings if l['Preis']])/len(listings):.2f} €")
    else:
        st.write(prefix + "Keine Ergebnisse gefunden.")
    
    time.sleep(random.uniform(3, 7))

if st.button("Generierten Link anzeigen"):
    if custom_url:
        url = custom_url
    else:
        url = generate_url(query, category, state, provider, price_min, price_max, year_min, year_max, km_min, km_max, power_min, power_max, car_type)
    st.write(f"Generierter Link: {url}")
