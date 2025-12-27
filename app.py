import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

st.set_page_config(page_title="Cours BRVM", layout="wide")
st.title("📈 Cours des Actions - BRVM")

@st.cache_data(ttl=600)
def scrape_brvm():
    url = "https://www.brvm.org/fr/cours-actions/0"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
    except requests.RequestException as e:
        st.error(f"Erreur: {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    data = []
    
    table = soup.find('table')
    if not table:
        st.error("Tableau non trouvé")
        return None

    rows = table.find_all('tr')[1:]
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 7:
            row_data = [col.get_text(strip=True) for col in cols]
            data.append(row_data)

    columns = ["Symbole", "Nom", "Volume", "Cours veille", 
               "Cours Ouverture", "Cours Clôture", "Variation (%)"]
    
    df = pd.DataFrame(data, columns=columns)
    
    # Nettoyage des données
    numeric_cols = ["Volume", "Cours veille", "Cours Ouverture", "Cours Clôture"]
    for col in numeric_cols:
        df[col] = df[col].str.replace(' ', '').astype(float)
    
    df["Variation (%)"] = df["Variation (%)"].str.replace(',', '.').str.rstrip('%').astype(float)
    
    return df

def main():
    with st.spinner('Mise à jour des données...'):
        df = scrape_brvm()

    if df is not None and not df.empty:
        st.success(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Filtre
        symbol_search = st.text_input("🔍 Filtrer par symbole :")
        if symbol_search:
            df_filtered = df[df['Symbole'].str.contains(symbol_search.upper(), na=False)]
        else:
            df_filtered = df
        
        # Affichage
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)
        
        # Téléchargement
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(
            label="💾 Télécharger CSV",
            data=csv,
            file_name=f"brvm_cours_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning("Aucune donnée disponible")

if __name__ == "__main__":
    main()
