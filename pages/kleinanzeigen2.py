import streamlit as st
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
import pandas as pd
import time
from webdriver_manager.chrome import ChromeDriverManager

# Streamlit UI
st.title("Ebay Scraper mit Selenium")

st.write("Dieser Scraper verwendet Selenium, um dynamische Inhalte von Ebay-Kleinanzeigen zu scrapen.")

# Eingabe für den vorgefertigten Link
custom_url = st.text_input("Füge einen vorgefertigten Link ein (Pflichtfeld)")

# Button zum Starten des Scrapers
if st.button("Scraper starten"):
    if not custom_url:
        st.error("Bitte geben Sie einen gültigen Link ein.")
    else:
        # Selenium Setup
        st.write("Starte den Scraper...")
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Headless mode, falls kein Browserfenster angezeigt werden soll
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.binary_location = "/usr/bin/google-chrome"  # Pfad zur Google-Chrome-Binary

        # ChromeDriver mit webdriver_manager verwalten
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

        try:
            # Öffnen der URL
            driver.get(custom_url)
            st.write(f"Öffne die Seite: {custom_url}")

            # Warten, bis die Anzeigen geladen sind
            wait = WebDriverWait(driver, 20)  # Timeout auf 20 Sekunden erhöhen
            wait.until(EC.presence_of_all_elements_located((By.CLASS_NAME, "aditem")))

            # Debugging: HTML-Inhalt der Seite ausgeben
            page_source = driver.page_source
            st.text_area("HTML-Inhalt der Seite", page_source, height=300)

            # Anzeigen scrapen
            ads = driver.find_elements(By.CLASS_NAME, "aditem")
            listings = []

            for ad in ads:
                try:
                    # Titel der Anzeige
                    title = ad.find_element(By.CLASS_NAME, "ellipsis").text

                    # Preis der Anzeige
                    price_element = ad.find_element(By.CLASS_NAME, "aditem-main--price")
                    price = price_element.text if price_element else "Kein Preis"

                    # Link zur Anzeige
                    link_element = ad.find_element(By.TAG_NAME, "a")
                    link = link_element.get_attribute("href") if link_element else "Kein Link"

                    # Daten speichern
                    listings.append({"Titel": title, "Preis": price, "Link": link})
                except Exception as e:
                    st.warning(f"Fehler beim Scrapen einer Anzeige: {e}")

            # Ergebnisse anzeigen
            if listings:
                st.success(f"{len(listings)} Anzeigen gefunden!")
                df = pd.DataFrame(listings)
                st.dataframe(df)

                # Ergebnisse in Excel speichern
                filename = "kleinanzeigen_ergebnisse.xlsx"
                df.to_excel(filename, index=False)
                st.write(f"Daten wurden in {filename} gespeichert.")
            else:
                st.warning("Keine Anzeigen gefunden.")

        except TimeoutException:
            st.error("Timeout: Die Seite konnte nicht vollständig geladen werden.")
        except Exception as e:
            st.error(f"Ein Fehler ist aufgetreten: {e}")
        finally:
            driver.quit()