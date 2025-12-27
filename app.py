import streamlit as st
import pandas as pd
from playwright.sync_api import sync_playwright
import time
from datetime import datetime

# --- Page Configuration ---
st.set_page_config(page_title="BRVM Scraper", layout="wide")
st.title("📊 Scraping des Cours BRVM")
st.caption("Extraction en direct depuis le site web public de la BRVM")

# --- Main Scraping Function with Playwright ---
@st.cache_data(ttl=600)  # Cache data for 10 minutes
def scrape_brvm_with_playwright():
    """
    Uses a headless browser to load the JavaScript and scrape the stock table.
    """
    url = "https://www.brvm.org/fr/cours-actions/0"
    data = []

    with sync_playwright() as p:
        # Launch browser (headless=True for production)
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        try:
            # Navigate to the page
            page.goto(url, timeout=60000)
            st.sidebar.info("Chargement de la page en cours...")

            # **CRITICAL: Wait for the table to be present in the DOM**
            # The main table often has a class or structure. You might need to adjust the selector.
            # Example: wait for a <table> or a specific row to appear.
            page.wait_for_selector("table", timeout=30000)  # Basic wait for any table
            # Give extra time for data to populate
            time.sleep(3)

            # Extract the entire page's HTML after JS has run
            html_content = page.content()

            # Use pandas to read all HTML tables
            tables = pd.read_html(html_content)
            st.sidebar.success(f"Trouvé: {len(tables)} tableau(x) dans la page.")

            # Find the main stocks table (usually the largest one)
            main_df = None
            for df in tables:
                # Identify the correct table by its columns or size
                # Looking for columns like 'Symbole', 'Nom', 'Volume', etc.
                if df.shape[1] >= 6:  # Has enough columns
                    if main_df is None or df.shape[0] > main_df.shape[0]:
                        main_df = df

            if main_df is not None:
                st.sidebar.success(f"Tableau principal extrait ({main_df.shape[0]} lignes).")
                return main_df
            else:
                st.sidebar.error("Impossible d'identifier le tableau des actions.")
                return None

        except Exception as e:
            st.sidebar.error(f"Erreur lors du scraping: {e}")
            # Print the page content for debugging if table not found
            # st.text(html_content[:2000]) # Uncomment for debugging
            return None
        finally:
            browser.close()

# --- Streamlit UI ---
if st.sidebar.button("🔄 Extraire les données"):
    # Clear cache for this function to force a fresh scrape
    st.cache_data.clear()

with st.spinner("Lancement du navigateur et extraction des données..."):
    df = scrape_brvm_with_playwright()

if df is not None:
    st.success(f"✅ Données mises à jour. {len(df)} actions trouvées.")
    
    # Display the DataFrame
    st.dataframe(df, use_container_width=True, height=600)
    
    # Download button
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Télécharger en CSV",
        data=csv,
        file_name=f"brvm_cours_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
else:
    st.error("""
    **Échec de l'extraction.** 
    Causes possibles :
    1. La structure du site a changé (le sélecteur 'table' n'est plus valide).
    2. Le site a bloqué l'accès du robot (techniques anti-scraping)[citation:9].
    3. Temps de chargement trop long.

    **Solution :** Ouvrez l'URL dans votre navigateur, inspectez l'élément (F12) contenant le tableau et notez son sélecteur CSS (ex: `.table-cours` ou `#data-table`). Remplacez `"table"` dans la fonction `page.wait_for_selector()` par ce nouveau sélecteur.
    """)
