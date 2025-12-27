import streamlit as st
import requests
import pandas as pd
from bs4 import BeautifulSoup

st.set_page_config(page_title="BRVM - Actions", layout="wide")

st.title("📈 Tableau des actions – BRVM")
st.caption("Données récupérées automatiquement depuis le site officiel de la BRVM")

@st.cache_data(ttl=3600)
def scrape_brvm_actions():
    url = "https://www.brvm.org/fr/cours-actions/0"

    headers = {
        "User-Agent": "Mozilla/5.0"
    }

    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "lxml")

    table = soup.find("table")
    if table is None:
        return None

    df = pd.read_html(str(table))[0]

    # Nettoyage léger
    df.columns = [col.strip() for col in df.columns]
    df = df.dropna(how="all")

    return df


with st.spinner("Récupération des données BRVM..."):
    try:
        df_actions = scrape_brvm_actions()

        if df_actions is not None:
            st.success("Données chargées avec succès")

            st.dataframe(
                df_actions,
                use_container_width=True,
                hide_index=True
            )

            # Téléchargement
            csv = df_actions.to_csv(index=False).encode("utf-8")
            st.download_button(
                "📥 Télécharger en CSV",
                csv,
                "brvm_actions.csv",
                "text/csv"
            )
        else:
            st.error("Impossible de trouver le tableau sur le site BRVM.")

    except Exception as e:
        st.error("Erreur lors du scraping")
        st.code(str(e))
