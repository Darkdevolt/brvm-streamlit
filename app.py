import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time

# Configuration de la page
st.set_page_config(page_title="Scraping BRVM", page_icon="📊", layout="wide")
st.title("🔍 Scraping du Site BRVM")
st.caption("Connexion directe au site officiel de la BRVM")

# URL cible
url = "https://www.brvm.org/fr/cours-actions/0"

@st.cache_data(ttl=300)  # Cache de 5 minutes
def scrape_brvm_direct():
    """Fonction de scraping direct du site BRVM"""
    try:
        # Headers EXACTEMENT comme vous les avez fournis
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/91.0.4472.124',
            'Accept': 'text/html,application/xhtml+xml,application/xml',
            'Accept-Language': 'fr,fr-FR'
        }
        
        st.sidebar.code(f"Headers utilisés:\n{headers}")
        
        # Faire la requête avec timeout court
        response = requests.get(url, headers=headers, timeout=10)
        st.sidebar.text(f"Status Code: {response.status_code}")
        
        # Vérifier le statut
        if response.status_code != 200:
            return None, f"Erreur HTTP: {response.status_code}"
        
        # Parser le HTML
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Vérifier si on a du contenu
        if len(response.content) < 100:
            return None, "Réponse vide du serveur"
        
        # Afficher un aperçu du HTML pour debug
        with st.expander("🔎 Aperçu du HTML reçu (premier 1000 caractères)"):
            st.text(response.text[:1000])
        
        # Essayer de trouver le tableau
        table = soup.find('table')
        
        if not table:
            # Chercher autrement
            tables = soup.find_all('table')
            if tables:
                table = tables[0]
            else:
                return None, "Aucun tableau trouvé dans le HTML"
        
        # Extraire les données du tableau
        data = []
        rows = table.find_all('tr')
        
        if len(rows) < 2:
            return None, "Tableau vide"
        
        # Extraire les en-têtes
        headers_row = rows[0]
        headers = [th.get_text(strip=True) for th in headers_row.find_all('th')]
        
        # Si pas d'en-têtes th, essayer avec td
        if not headers and len(rows) > 1:
            first_row = rows[1]
            headers = [td.get_text(strip=True) for td in first_row.find_all('td')]
        
        # Extraire les données
        for row in rows[1:]:
            cols = row.find_all('td')
            if len(cols) >= 7:  # Minimum 7 colonnes attendues
                try:
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
                except Exception as e:
                    st.sidebar.warning(f"Erreur ligne: {str(e)}")
                    continue
        
        if not data:
            return None, "Aucune donnée extraite"
        
        # Créer DataFrame
        df = pd.DataFrame(data)
        
        # Convertir types numériques
        numeric_cols = ['Volume', 'Cours veille (FCFA)', 'Cours Ouverture (FCFA)', 
                       'Cours Clôture (FCFA)', 'Variation (%)']
        
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors='coerce')
        
        return df, "Succès"
        
    except requests.exceptions.Timeout:
        return None, "Timeout: Le site ne répond pas"
    except requests.exceptions.ConnectionError:
        return None, "Erreur de connexion"
    except Exception as e:
        return None, f"Erreur: {str(e)}"

# Interface principale
st.sidebar.header("Configuration Scraping")

# Options
st.sidebar.checkbox("Afficher les logs de debug", value=True, key="debug")

# Bouton de rafraîchissement
if st.sidebar.button("🔄 Lancer le Scraping"):
    st.cache_data.clear()
    st.rerun()

# Affichage du statut
status_container = st.sidebar.container()

# Tentative de scraping
status_container.info("🔄 Tentative de connexion...")

try:
    with st.spinner("Scraping en cours..."):
        df, message = scrape_brvm_direct()
    
    if df is not None:
        status_container.success(f"✅ {message}")
        
        # Afficher les résultats
        st.success(f"✅ Scraping réussi - {len(df)} lignes récupérées")
        
        # Afficher le tableau
        st.dataframe(df, use_container_width=True, height=500)
        
        # Téléchargement
        st.download_button(
            label="📥 Télécharger CSV",
            data=df.to_csv(index=False, encoding='utf-8-sig'),
            file_name=f"brvm_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
        
    else:
        status_container.error(f"❌ {message}")
        
        st.error(f"""
        ## ❌ Échec du Scraping
        
        **Message d'erreur:** `{message}`
        
        ### Dépannage immédiat:
        
        1. **Testez manuellement le site:**
           - Ouvrez [BRVM Actions]({url}) dans votre navigateur
           - Vérifiez si la page s'affiche
        
        2. **Vérifiez l'accès:**
           ```bash
           # Test réseau simple
           ping www.brvm.org
           
           # Ou avec curl
           curl -I {url}
           ```
        
        3. **Problèmes possibles:**
           - 🔒 Le site bloque les robots
           - 🚧 Maintenance du site
           - 🌐 Restrictions géographiques
           - 🔄 Changement de structure HTML
        
        ### Pour Streamlit Cloud:
        - Vérifiez les logs Streamlit
        - Testez avec un timeout plus long
        - Essayez un user-agent différent
        """)
        
        # Test direct
        with st.expander("🧪 Test de connexion directe"):
            try:
                test_response = requests.get(url, timeout=5)
                st.text(f"Status: {test_response.status_code}")
                st.text(f"Taille: {len(test_response.content)} bytes")
                st.text(f"En-têtes: {dict(test_response.headers)}")
            except Exception as e:
                st.error(f"Erreur test: {str(e)}")
                
except Exception as e:
    st.error(f"Erreur inattendue: {str(e)}")

# Informations techniques
st.sidebar.markdown("---")
st.sidebar.markdown("""
**📊 Informations techniques:**
- URL: `https://www.brvm.org/fr/cours-actions/0`
- Méthode: GET direct
- Cache: 5 minutes
- Timeout: 10 secondes

**🛠️ Si ça ne marche pas:**
1. Vérifiez que le site est accessible
2. Vérifiez les logs Streamlit Cloud
3. Adaptez le parsing HTML si nécessaire
""")
