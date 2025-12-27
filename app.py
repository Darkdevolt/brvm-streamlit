import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Titre de l'application
st.set_page_config(page_title="Cours BRVM", layout="wide")
st.title("📈 Cours des Actions - BRVM")
st.markdown("Données mises à jour depuis [BRVM.org](https://www.brvm.org/fr/cours-actions/0)")

@st.cache_data(ttl=600)  # Met en cache les données pendant 10 minutes
def scrape_brvm():
    """
    Scrape les données des actions depuis le site de la BRVM.
    Retourne un DataFrame pandas.
    """
    url = "https://www.brvm.org/fr/cours-actions/0"
    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()  # Vérifie les erreurs HTTP
    except requests.RequestException as e:
        st.error(f"Erreur lors de la récupération de la page : {e}")
        return None

    soup = BeautifulSoup(response.content, 'html.parser')
    data = []

    # Chercher le tableau principal. Cette sélection peut nécessiter un ajustement.
    # D'après le HTML fourni, on cherche la table après l'en-tête "Toutes"
    table = soup.find('table')
    if not table:
        st.error("Tableau non trouvé. La structure du site a peut-être changé.")
        return None

    # Parcourir les lignes du tableau (en ignorant l'en-tête)
    rows = table.find_all('tr')[1:]  # Supprime la première ligne d'en-tête
    for row in rows:
        cols = row.find_all('td')
        if len(cols) >= 7:  # Vérifie qu'il y a assez de colonnes
            # Nettoyer les données (supprimer les espaces superflus)
            row_data = [col.get_text(strip=True) for col in cols]
            data.append(row_data)

    # Définir les noms de colonnes basés sur le site
    columns = ["Symbole", "Nom", "Volume", "Cours veille (FCFA)", 
               "Cours Ouverture (FCFA)", "Cours Clôture (FCFA)", "Variation (%)"]
    
    df = pd.DataFrame(data, columns=columns)
    
    # Convertir les colonnes numériques (gérer les séparateurs d'espace pour les milliers)
    numeric_cols = ["Volume", "Cours veille (FCFA)", "Cours Ouverture (FCFA)", "Cours Clôture (FCFA)"]
    for col in numeric_cols:
        df[col] = df[col].str.replace(' ', '').astype(float)
    
    # Nettoyer la colonne 'Variation (%)' : retirer le % et convertir
    df["Variation (%)"] = df["Variation (%)"].str.replace(',', '.').str.rstrip('%').astype(float)
    
    return df

def main():
    # Scraper les données
    with st.spinner('Mise à jour des données depuis la BRVM...'):
        df = scrape_brvm()

    if df is not None and not df.empty:
        # Afficher la date de la dernière mise à jour
        st.success(f"Dernière mise à jour : {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
        
        # Afficher quelques métriques clés en haut
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Nombre d'actions", len(df))
        with col2:
            st.metric("Plus forte hausse", f"{df['Variation (%)'].max():.2f}%")
        with col3:
            st.metric("Plus forte baisse", f"{df['Variation (%)'].min():.2f}%")

        # Zone de recherche et filtres
        st.subheader("📊 Tableau des Cours")
        
        # Filtre par symbole
        symbol_search = st.text_input("🔍 Filtrer par symbole (ex: BICB, BOAB) :")
        if symbol_search:
            df_filtered = df[df['Symbole'].str.contains(symbol_search.upper(), na=False)]
        else:
            df_filtered = df

        # Filtre par variation
        min_var, max_var = st.slider(
            "Filtrer par plage de variation (%) :",
            min_value=float(df['Variation (%)'].min()),
            max_value=float(df['Variation (%)'].max()),
            value=(float(df['Variation (%)'].min()), float(df['Variation (%)'].max()))
        )
        df_filtered = df_filtered[(df_filtered['Variation (%)'] >= min_var) & 
                                  (df_filtered['Variation (%)'] <= max_var)]

        # Afficher le tableau interactif
        st.dataframe(df_filtered, use_container_width=True, hide_index=True)

        # Télécharger les données
        csv = df.to_csv(index=False, sep=';').encode('utf-8-sig')
        st.download_button(
            label="💾 Télécharger les données en CSV",
            data=csv,
            file_name=f"brvm_cours_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

        # Visualisation simple
        st.subheader("📈 Top 5 des Variations")
        top_gainers = df.nlargest(5, 'Variation (%)')[['Symbole', 'Nom', 'Variation (%)']]
        top_losers = df.nsmallest(5, 'Variation (%)')[['Symbole', 'Nom', 'Variation (%)']]
        
        col_chart1, col_chart2 = st.columns(2)
        with col_chart1:
            st.write("**Top 5 des hausses**")
            st.bar_chart(top_gainers.set_index('Symbole')['Variation (%)'])
        with col_chart2:
            st.write("**Top 5 des baisses**")
            st.bar_chart(top_losers.set_index('Symbole')['Variation (%)'])
    else:
        st.warning("Aucune donnée n'a pu être récupérée. Le site a peut-être changé sa structure.")

if __name__ == "__main__":
    main()
