import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime

# Configuration de la page
st.set_page_config(page_title="Cours BRVM", page_icon="📈", layout="wide")
st.title("📊 Cours des Actions BRVM")
st.caption("Scraping direct du site officiel de la BRVM")

# URL cible
url = "https://www.brvm.org/fr/cours-actions/0"

@st.cache_data(ttl=3600)  # Cache les données pendant 1 heure
def scrape_brvm_data():
    """Fonction pour scraper les données de la BRVM - Version scraping uniquement"""
    try:
        # Requête HTTP avec headers
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'fr,fr-FR;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        }
        
        # Debug: afficher l'URL
        st.sidebar.write(f"Tentative de connexion à: {url}")
        
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()  # Lève une exception pour les codes 4xx/5xx
        
        # Vérifier le contenu
        if len(response.content) < 1000:
            raise Exception("Réponse trop courte, site peut-être bloqué")
        
        # Parser le contenu HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Debug: afficher la taille du HTML
        st.sidebar.write(f"HTML reçu: {len(response.content)} caractères")
        
        # Trouver le tableau - approche robuste
        table = None
        
        # Essayer plusieurs méthodes pour trouver le tableau
        # 1. Chercher par les en-têtes
        tables = soup.find_all('table')
        for tbl in tables:
            th_texts = [th.get_text(strip=True) for th in tbl.find_all('th')]
            if any('Symbole' in text for text in th_texts):
                table = tbl
                break
        
        # 2. Si pas trouvé, prendre la première table avec des données
        if not table and tables:
            table = tables[0]
        
        if not table:
            raise Exception("Aucun tableau trouvé dans la page HTML")
        
        # Extraire les lignes
        rows = table.find_all('tr')
        if len(rows) < 2:
            raise Exception("Tableau vide ou insuffisamment de lignes")
        
        # Extraire les en-têtes
        headers = []
        if rows[0].find('th'):
            headers = [th.get_text(strip=True) for th in rows[0].find_all('th')]
        else:
            # Deviner les en-têtes basés sur le contenu fourni
            headers = ['Symbole', 'Nom', 'Volume', 'Cours veille (FCFA)', 
                      'Cours Ouverture (FCFA)', 'Cours Clôture (FCFA)', 'Variation (%)']
        
        # Extraire les données
        data = []
        for row in rows[1:]:  # Skip la première ligne (en-têtes)
            cols = row.find_all('td')
            if len(cols) >= 7:  # On attend au moins 7 colonnes
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
        
        if not data:
            raise Exception("Aucune donnée extraite du tableau")
        
        # Créer le DataFrame
        df = pd.DataFrame(data)
        
        # Convertir les colonnes numériques
        numeric_cols = ['Volume', 'Cours veille (FCFA)', 'Cours Ouverture (FCFA)', 
                       'Cours Clôture (FCFA)', 'Variation (%)']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        # Debug: afficher les premières lignes
        st.sidebar.write(f"Données extraites: {len(df)} lignes")
        
        return df, "Données BRVM réelles"
        
    except requests.exceptions.Timeout:
        raise Exception("Timeout: Le site BRVM ne répond pas (délai dépassé)")
    except requests.exceptions.ConnectionError:
        raise Exception("Erreur de connexion: Impossible d'atteindre le site BRVM")
    except requests.exceptions.HTTPError as e:
        raise Exception(f"Erreur HTTP {e.response.status_code}: Accès refusé")
    except Exception as e:
        raise Exception(f"Erreur de scraping: {str(e)}")

# Interface principale
st.sidebar.header("Configuration")

# Bouton pour rafraîchir
if st.sidebar.button("🔄 Forcer le rafraîchissement"):
    st.cache_data.clear()
    st.rerun()

# Afficher le statut
st.sidebar.subheader("Statut")
status_placeholder = st.sidebar.empty()

try:
    # Tentative de scraping
    status_placeholder.info("⏳ Connexion au site BRVM...")
    
    with st.spinner("Scraping en cours... Cela peut prendre quelques secondes"):
        df, source = scrape_brvm_data()
    
    status_placeholder.success("✅ Données chargées avec succès")
    
    # Afficher les données
    st.success(f"✅ Scraping réussi - {len(df)} actions récupérées")
    st.write(f"**Source:** {source}")
    
    # Afficher le DataFrame brut
    st.subheader("📋 Données brutes BRVM")
    st.dataframe(df, use_container_width=True, height=500)
    
    # Options de téléchargement
    st.subheader("💾 Téléchargement")
    
    # Format CSV
    csv = df.to_csv(index=False, encoding='utf-8-sig')
    st.download_button(
        label="📥 Télécharger en CSV",
        data=csv,
        file_name=f"brvm_{datetime.now().strftime('%Y%m%d')}.csv",
        mime="text/csv",
        help="Téléchargez les données au format CSV"
    )
    
    # Format Excel
    excel_buffer = pd.ExcelWriter('brvm_data.xlsx', engine='openpyxl')
    df.to_excel(excel_buffer, index=False)
    excel_buffer.close()
    
    with open('brvm_data.xlsx', 'rb') as f:
        excel_data = f.read()
    
    st.download_button(
        label="📊 Télécharger en Excel",
        data=excel_data,
        file_name=f"brvm_{datetime.now().strftime('%Y%m%d')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        help="Téléchargez les données au format Excel"
    )
    
    # Statistiques rapides
    st.subheader("📈 Statistiques")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        if 'Variation (%)' in df.columns:
            avg_var = df['Variation (%)'].mean()
            st.metric("Variation moyenne", f"{avg_var:.2f}%")
    
    with col2:
        if 'Cours Clôture (FCFA)' in df.columns:
            max_price = df['Cours Clôture (FCFA)'].max()
            st.metric("Cours max", f"{max_price:,.0f} FCFA")
    
    with col3:
        if 'Volume' in df.columns:
            total_volume = df['Volume'].sum()
            st.metric("Volume total", f"{total_volume:,.0f}")
    
except Exception as e:
    # Affichage de l'erreur
    status_placeholder.error("❌ Échec du scraping")
    
    st.error("""
    ## ❌ Impossible d'accéder aux données BRVM
    
    **Problème détecté:** `{}`
    
    ### Causes possibles:
    1. 🔒 **Le site BRVM bloque l'accès** aux robots/scrapers
    2. 🌐 **Problème de connexion** internet
    3. 🚧 **Site BRVM en maintenance** ou inaccessible
    4. 🔄 **Structure du site modifiée**
    
    ### Solutions à essayer:
    - ⏱️ **Attendez quelques minutes** et réessayez
    - 🔄 **Cliquez sur 'Forcer le rafraîchissement'** dans la sidebar
    - 🌍 **Vérifiez manuellement** le site: [BRVM Cours Actions](https://www.brvm.org/fr/cours-actions/0)
    - 🛡️ **Le site peut nécessiter** un proxy ou un navigateur avec JavaScript
    
    ### Code d'erreur technique:
    ```python
    {}
    ```
    """.format(str(e), str(e)))
    
    # Afficher des informations de débogage
    with st.expander("🔧 Informations de débogage"):
        st.write("**Headers utilisés pour la requête:**")
        st.code("""
        User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124
        Accept: text/html,application/xhtml+xml,application/xml
        Accept-Language: fr,fr-FR
        """)
        
        st.write("**Pour tester manuellement:**")
        st.markdown("""
        1. Ouvrez [https://www.brvm.org/fr/cours-actions/0](https://www.brvm.org/fr/cours-actions/0)
        2. Vérifiez si la page s'affiche
        3. Inspectez la page (F12) pour voir le tableau
        """)

# Pied de page
st.sidebar.markdown("---")
st.sidebar.markdown("""
**ℹ️ À propos:**
- **Type:** Scraping réel uniquement
- **Source:** Site BRVM officiel
- **Pas de données simulées**
- **Dernière tentative:** {}
""".format(datetime.now().strftime("%H:%M:%S")))
