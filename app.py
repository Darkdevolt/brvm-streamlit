import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Cours BRVM", page_icon="📈", layout="wide")
st.title("📊 Cours des Actions BRVM")
st.caption("Données extraites en direct du site officiel de la BRVM")

# URL cible
url = "https://www.brvm.org/fr/cours-actions/0"

@st.cache_data(ttl=3600)  # Cache les données pendant 1 heure
def scrape_brvm_data():
    """Fonction pour scraper les données de la BRVM"""
    try:
        # Requête HTTP
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parser le contenu HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extraire la date de la séance
        date_element = soup.find('div', class_='seance-info')
        date_seance = "Date non disponible"
        if date_element:
            date_text = date_element.get_text(strip=True)
            date_seance = date_text.split('-')[0].strip() if '-' in date_text else date_text
        
        # Trouver le tableau (chercher la table avec les bonnes en-têtes)
        table = None
        tables = soup.find_all('table')
        
        for tbl in tables:
            headers = [th.get_text(strip=True) for th in tbl.find_all('th')]
            if 'Symbole' in headers and 'Variation (%)' in headers:
                table = tbl
                break
        
        if not table:
            st.error("Tableau non trouvé dans la page")
            return None, date_seance
        
        # Extraire les données du tableau
        data = []
        rows = table.find_all('tr')[1:]  # Skip l'en-tête
        
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 7:  # Vérifier qu'on a toutes les colonnes
                row_data = {
                    'Symbole': cols[0].get_text(strip=True),
                    'Nom': cols[1].get_text(strip=True),
                    'Volume': cols[2].get_text(strip=True).replace(' ', ''),
                    'Cours veille (FCFA)': cols[3].get_text(strip=True).replace(' ', ''),
                    'Cours Ouverture (FCFA)': cols[4].get_text(strip=True).replace(' ', ''),
                    'Cours Clôture (FCFA)': cols[5].get_text(strip=True).replace(' ', ''),
                    'Variation (%)': cols[6].get_text(strip=True).replace(',', '.')
                }
                data.append(row_data)
        
        # Créer le DataFrame
        df = pd.DataFrame(data)
        
        # Convertir les colonnes numériques
        numeric_cols = ['Volume', 'Cours veille (FCFA)', 'Cours Ouverture (FCFA)', 
                       'Cours Clôture (FCFA)', 'Variation (%)']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df, date_seance
        
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur de connexion: {e}")
        return None, "Erreur"
    except Exception as e:
        st.error(f"Erreur lors du scraping: {e}")
        return None, "Erreur"

# Interface Streamlit
st.sidebar.header("Paramètres")

# Bouton pour rafraîchir manuellement
if st.sidebar.button("🔄 Rafraîchir les données"):
    st.cache_data.clear()

# Afficher la date de la séance
st.sidebar.subheader("Dernière mise à jour")
st.sidebar.text(datetime.now().strftime("%d/%m/%Y %H:%M:%S"))

# Charger les données
with st.spinner("Chargement des données BRVM..."):
    df, date_seance = scrape_brvm_data()

if df is not None:
    # Afficher la date de la séance
    st.info(f"**Séance:** {date_seance}")
    
    # Métriques globales
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Nombre d'actions", len(df))
    with col2:
        if 'Variation (%)' in df.columns:
            hausses = (df['Variation (%)'] > 0).sum()
            st.metric("Hausses", hausses)
    with col3:
        if 'Variation (%)' in df.columns:
            baisses = (df['Variation (%)'] < 0).sum()
            st.metric("Baisses", baisses)
    with col4:
        if 'Variation (%)' in df.columns:
            stables = (df['Variation (%)'] == 0).sum()
            st.metric("Stables", stables)
    
    # Filtres
    st.subheader("Filtres")
    col1, col2 = st.columns(2)
    
    with col1:
        # Filtre par symbole
        symboles = ['Tous'] + sorted(df['Symbole'].unique().tolist())
        selected_symbole = st.selectbox("Filtrer par symbole:", symboles)
        
        # Filtre par variation
        variation_filter = st.selectbox("Filtrer par variation:", 
                                       ['Toutes', 'Hausses uniquement', 'Baisses uniquement', 'Stables uniquement'])
    
    with col2:
        # Filtre par volume
        if 'Volume' in df.columns:
            min_vol, max_vol = int(df['Volume'].min()), int(df['Volume'].max())
            vol_range = st.slider("Filtrer par volume:", min_vol, max_vol, (min_vol, max_vol))
        
        # Recherche par nom
        search_term = st.text_input("Rechercher par nom:", "")
    
    # Appliquer les filtres
    filtered_df = df.copy()
    
    if selected_symbole != 'Tous':
        filtered_df = filtered_df[filtered_df['Symbole'] == selected_symbole]
    
    if variation_filter == 'Hausses uniquement':
        filtered_df = filtered_df[filtered_df['Variation (%)'] > 0]
    elif variation_filter == 'Baisses uniquement':
        filtered_df = filtered_df[filtered_df['Variation (%)'] < 0]
    elif variation_filter == 'Stables uniquement':
        filtered_df = filtered_df[filtered_df['Variation (%)'] == 0]
    
    if 'Volume' in df.columns:
        filtered_df = filtered_df[
            (filtered_df['Volume'] >= vol_range[0]) & 
            (filtered_df['Volume'] <= vol_range[1])
        ]
    
    if search_term:
        filtered_df = filtered_df[
            filtered_df['Nom'].str.contains(search_term, case=False, na=False)
        ]
    
    # Afficher le tableau
    st.subheader(f"Cours des Actions ({len(filtered_df)} résultats)")
    
    # Formater l'affichage des nombres
    display_df = filtered_df.copy()
    if 'Cours Clôture (FCFA)' in display_df.columns:
        display_df['Cours Clôture (FCFA)'] = display_df['Cours Clôture (FCFA)'].apply(
            lambda x: f"{x:,.0f}" if pd.notnull(x) else ""
        )
    
    if 'Variation (%)' in display_df.columns:
        def color_variation(val):
            if pd.isnull(val):
                return ''
            elif val > 0:
                return 'color: green'
            elif val < 0:
                return 'color: red'
            else:
                return 'color: gray'
        
        # Afficher le tableau avec style
        st.dataframe(
            display_df.style.applymap(color_variation, subset=['Variation (%)']),
            use_container_width=True,
            height=600
        )
    else:
        st.dataframe(display_df, use_container_width=True, height=600)
    
    # Options d'export
    st.subheader("Exporter les données")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if st.button("📥 Télécharger CSV"):
            csv = filtered_df.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="Cliquer pour télécharger",
                data=csv,
                file_name=f"brvm_cours_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
    
    with col2:
        if st.button("📊 Afficher les Top 10"):
            top10 = filtered_df.nlargest(10, 'Variation (%)') if 'Variation (%)' in filtered_df.columns else filtered_df.head(10)
            st.dataframe(top10, use_container_width=True)
    
    with col3:
        if st.button("📉 Afficher statistiques"):
            if not filtered_df.empty and 'Variation (%)' in filtered_df.columns:
                st.write("**Statistiques des variations:**")
                st.write(filtered_df['Variation (%)'].describe())
    
    # Avertissement sur la source des données
    st.caption("""
    ⚠️ **Note:** Ces données sont extraites du site officiel de la BRVM. 
    Elles sont fournies à titre informatif uniquement. 
    Dernière extraction: {}
    """.format(datetime.now().strftime("%d/%m/%Y %H:%M:%S")))
    
else:
    st.warning("Impossible de charger les données. Veuillez réessayer plus tard.")
    st.info("""
    **Dépannage:**
    1. Vérifiez votre connexion internet
    2. Le site de la BRVM pourrait être temporairement inaccessible
    3. Essayez de rafraîchir la page dans quelques minutes
    """)

# Pied de page
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Instructions de déploiement sur Streamlit Cloud:**
1. Créez un fichier `requirements.txt` avec:
