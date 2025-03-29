import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from datetime import datetime, timedelta
import pandas as pd
import time
import random
import os
import folium
from streamlit_folium import st_folium

st.title("Ebay Scraper (Selenium)")

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

# Eingabe für den benutzerdefinierten Dateinamen oder Auswahl aus Dropdown
file_naming_option = st.text_input(
    "Benutzerdefinierter Dateiname für die Excel-Datei (optional, oder wähle aus Dropdown)",
    placeholder="Gib einen Namen ein oder wähle aus dem Dropdown"
)
dropdown_options = ["Audi", "BMW", "Land-Rover", "Fiat", "Mercedes", "Porsche"]
selected_option = st.selectbox("Oder wähle eine Fahrzeugmarke", [""] + dropdown_options)
if selected_option:
    file_naming_option = selected_option

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
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(service=Service(), options=options)
    
    try:
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.CLASS_NAME, "aditem")))
        
        listings = []
        seen_ads = {}  # Track duplicates by (price, city)
        ad_items = driver.find_elements(By.CLASS_NAME, "aditem")
        
        for ad in ad_items:
            if len(listings) >= 150:  # Safety net: Stop after 150 results
                st.warning("Mehr als 150 Ergebnisse gefunden. Bitte die Suchkriterien eingrenzen.")
                break
            try:
                ad_id = ad.get_attribute("data-adid")  # Extract Inserat ID
                date = ad.find_element(By.CLASS_NAME, "aditem-main--top--right").text.strip()
                # Replace "Heute" with today's date
                if date.lower() == "heute":
                    date = datetime.now().strftime("%d.%m.%Y")
                title = ad.find_element(By.CLASS_NAME, "text-module-begin").text.strip()
                location = ad.find_element(By.CLASS_NAME, "aditem-main--top--left").text.strip()
                city, postal_code = location.split(" ", 1) if " " in location else (location, "Keine Postleitzahl")
                price_text = ad.find_element(By.CLASS_NAME, "aditem-main--middle--price-shipping--price").text.strip()
                price = int(''.join(filter(str.isdigit, price_text))) if any(char.isdigit() for char in price_text) else None
                vb = "VB" in price_text
                link = ad.get_attribute("data-href")
                link = f"https://www.kleinanzeigen.de{link}" if link else "Kein Link"
                
                # Check for duplicates
                key = (price, city)
                if key in seen_ads:
                    existing_date = seen_ads[key]["Datum"]
                    if date > existing_date:  # Keep the newer ad
                        listings.remove(seen_ads[key])
                        seen_ads[key] = {
                            "Inserat ID": ad_id,
                            "Datum": date,
                            "Titel": title,
                            "Postleitzahl": postal_code,
                            "Stadt": city,
                            "Preis": price,
                            "VB": vb,
                            "Link": link
                        }
                        listings.append(seen_ads[key])
                else:
                    ad_data = {
                        "Inserat ID": ad_id,
                        "Datum": date,
                        "Titel": title,
                        "Postleitzahl": postal_code,
                        "Stadt": city,
                        "Preis": price,
                        "VB": vb,
                        "Link": link
                    }
                    seen_ads[key] = ad_data
                    listings.append(ad_data)
            except Exception as e:
                st.warning(f"Fehler beim Verarbeiten einer Anzeige: {e}")
        
        return listings
    finally:
        driver.quit()

def save_to_excel(data, query, year_min, year_max, price_min, price_max):
    # Ensure output directory exists
    output_dir = os.path.join(os.getcwd(), "Output der Fahrzeugsuchen")
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate filename based on user input or dropdown selection
    year_range = f"{year_min}-{year_max}" if year_min and year_max else "alle"
    price_range = f"{price_min}-{price_max}" if price_min and price_max else "alle"
    filename = f"{file_naming_option}_{year_range}_{price_range}.xlsx".replace(" ", "_")
    filepath = os.path.join(output_dir, filename)
    
    # Save to Excel (overwrite if exists)
    df = pd.DataFrame(data)
    # Ensure city and Inserat ID are stored as text
    df["Postleitzahl"] = df["Postleitzahl"].astype(float)
    df["Inserat ID"] = df["Inserat ID"].astype(float)
    df.to_excel(filepath, index=False)
    st.success(f"Daten gespeichert unter {filepath}")
    
    # Update Tracker_Outputs.xlsx
    tracker_filepath = os.path.join(output_dir, "Tracker_Outputs.xlsx")
    if os.path.exists(tracker_filepath):
        tracker_df = pd.read_excel(tracker_filepath, dtype={"Postleitzahl": float, "Inserat ID": float})
    else:
        tracker_df = pd.DataFrame(columns=["Inserat ID", "Datum", "Titel", "Postleitzahl", "Stadt", "Preis", "VB", "Link"])
    
    # Append new data and remove duplicates
    new_data_df = pd.DataFrame(data)
    combined_df = pd.concat([tracker_df, new_data_df]).drop_duplicates(subset=["Inserat ID"], keep="last")
    combined_df.to_excel(tracker_filepath, index=False)
    st.success(f"Tracker aktualisiert unter {tracker_filepath}")

    # Display the data in Streamlit
    st.write("Tabellarische Darstellung der Ergebnisse:")
    st.dataframe(df)

    # Display price statistics
    prices = [row["Preis"] for row in data if row["Preis"] is not None]
    if prices:
        st.write(f"Durchschnittspreis: {sum(prices) / len(prices):.2f} €")
        st.write(f"Minimaler Preis: {min(prices)} €")
        st.write(f"Maximaler Preis: {max(prices)} €")

    # Display a map with pins for the listings
    st.write("Karte der Inserate:")
    map_center = [51.1657, 10.4515]  # Center of Germany
    m = folium.Map(location=map_center, zoom_start=6)
    for _, row in df.iterrows():
        if row["Postleitzahl"] != "Keine Postleitzahl":
            try:
                # Use the postal code to approximate the location
                folium.Marker(
                    location=[float(row["Postleitzahl"][:2]) + 0.5, float(row["Postleitzahl"][:2]) + 0.5],  # Approximation
                    popup=f"{row['Titel']}<br>Preis: {row['Preis']} €<br><a href='{row['Link']}' target='_blank'>Inserat ansehen</a>",
                    tooltip=row["Titel"]
                ).add_to(m)
            except Exception as e:
                st.warning(f"Fehler beim Hinzufügen eines Pins: {e}")
    st_folium(m, width=700, height=500)

if st.button("Scraper starten"):
    start_datetime = datetime.combine(start_date, start_time)
    wait_time = (start_datetime - datetime.now()).total_seconds()
    
    if wait_time > 0:
        st.write(f"Der Scraper startet in {wait_time} Sekunden...")
        time.sleep(wait_time)
    
    if custom_url:
        url = custom_url
        st.write(f"Es wird nach den Ergebnissen des Custom-Links gesucht: {custom_url}")
    else:
        url = generate_url(query, category, state, provider, price_min, price_max, year_min, year_max, km_min, km_max, power_min, power_max, car_type)
        st.write(f"Es wird nach {query} gesucht...")
    
    listings = scrape_kleinanzeigen(url)
    if listings:
        save_to_excel(listings, query, year_min, year_max, price_min, price_max)
    else:
        st.write("Keine Ergebnisse gefunden.")
    
    time.sleep(random.uniform(3, 7))

if st.button("Generierten Link anzeigen"):
    if custom_url:
        url = custom_url
    else:
        url = generate_url(query, category, state, provider, price_min, price_max, year_min, year_max, km_min, km_max, power_min, power_max, car_type)
    st.write(f"Generierter Link: {url}")
