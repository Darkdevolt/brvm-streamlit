import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
import json
import time

st.set_page_config(page_title="Scraping BRVM Dynamique", page_icon="📈", layout="wide")
st.title("🔄 Scraping BRVM (Site Dynamique)")
st.caption("Site avec chargement JavaScript - Approche avancée")

# URL cible
url = "https://www.brvm.org/fr/cours-actions/0"

def fetch_brvm_with_js_simulation():
    """Tente de récupérer les données avec simulation de navigateur"""
    try:
        # Headers pour sembler être un navigateur réel
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'none',
            'Sec-Fetch-User': '?1',
            'Cache-Control': 'max-age=0'
        }
        
        # 1. D'abord récupérer la page de base
        st.sidebar.info("Étape 1: Chargement de la page principale...")
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code != 200:
            return None, f"HTTP {response.status_code}"
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # 2. Chercher des endpoints API dans les scripts
        st.sidebar.info("Étape 2: Analyse des scripts...")
        
        # Chercher tous les scripts
        scripts = soup.find_all('script')
        
        # Chercher des URLs d'API potentielles
        api_patterns = ['cours', 'actions', 'data', 'json', 'api']
        potential_urls = []
        
        for script in scripts:
            if script.string:
                content = script.string
                # Chercher des URLs dans le JavaScript
                import re
                urls = re.findall(r'["\'](https?://[^"\']+\.(json|js)[^"\']*)["\']', content)
                for url_match in urls:
                    if any(pattern in url_match[0].lower() for pattern in api_patterns):
                        potential_urls.append(url_match[0])
        
        # 3. Essayer de trouver le tableau dans le HTML chargé
        st.sidebar.info("Étape 3: Recherche des données...")
        
        # Méthode 1: Vérifier si les données sont dans une balise script JSON
        json_data = None
        for script in scripts:
            if script.string and 'var' in script.string and 'data' in script.string.lower():
                # Essayer d'extraire du JSON
                try:
                    # Chercher des objets JSON
                    json_text = re.search(r'(\{.*\})', script.string.replace('\n', ''))
                    if json_text:
                        data = json.loads(json_text.group(1))
                        if isinstance(data, dict) and len(data) > 0:
                            json_data = data
                            break
                except:
                    continue
        
        # Méthode 2: Essayer de parser le tableau HTML s'il existe
        tables = soup.find_all('table')
        data = []
        
        if tables:
            for table in tables:
                rows = table.find_all('tr')
                if len(rows) > 5:  # Tableau avec assez de données
                    for row in rows[1:]:  # Skip header
                        cols = row.find_all(['td', 'th'])
                        if len(cols) >= 6:
                            try:
                                row_data = {
                                    'Symbole': cols[0].get_text(strip=True),
                                    'Nom': cols[1].get_text(strip=True),
                                    'Volume': cols[2].get_text(strip=True).replace(' ', ''),
                                    'Cours veille': cols[3].get_text(strip=True).replace(' ', ''),
                                    'Cours Ouverture': cols[4].get_text(strip=True).replace(' ', ''),
                                    'Cours Clôture': cols[5].get_text(strip=True).replace(' ', ''),
                                    'Variation': cols[6].get_text(strip=True).replace(',', '.') if len(cols) > 6 else ''
                                }
                                data.append(row_data)
                            except:
                                continue
        
        # Si on a des données, créer DataFrame
        if data:
            df = pd.DataFrame(data)
            return df, "Données extraites du HTML"
        
        # Si pas de données, chercher des endpoints alternatifs
        st.sidebar.info("Étape 4: Tentative avec endpoints alternatifs...")
        
        # Essayer des endpoints communs
        endpoints = [
            "https://www.brvm.org/api/cours",
            "https://www.brvm.org/api/actions",
            "https://www.brvm.org/data/cours.json",
            "https://www.brvm.org/fr/cours-actions/data",
        ]
        
        for endpoint in endpoints:
            try:
                resp = requests.get(endpoint, headers=headers, timeout=5)
                if resp.status_code == 200:
                    # Essayer de parser comme JSON
                    try:
                        json_data = resp.json()
                        if isinstance(json_data, list) and len(json_data) > 0:
                            df = pd.DataFrame(json_data)
                            return df, f"Données API: {endpoint}"
                    except:
                        # Si pas JSON, essayer HTML
                        soup2 = BeautifulSoup(resp.content, 'html.parser')
                        tables2 = soup2.find_all('table')
                        if tables2:
                            # Essayer de parser
                            dfs = pd.read_html(str(tables2[0]))
                            if dfs:
                                return dfs[0], f"Tableau trouvé: {endpoint}"
            except:
                continue
        
        return None, "Aucune donnée trouvée - Site utilise probablement JavaScript lourd"
        
    except Exception as e:
        return None, f"Erreur: {str(e)}"

def fallback_scraping():
    """Méthode de fallback - utilisation de services externes ou techniques alternatives"""
    try:
        # Essayer Google Cache
        cached_url = f"https://webcache.googleusercontent.com/search?q=cache:{url}&strip=1"
        headers = {'User-Agent': 'Mozilla/5.0'}
        
        response = requests.get(cached_url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            tables = soup.find_all('table')
            
            if tables:
                # Essayer de parser tous les tableaux
                all_data = []
                for table in tables:
                    try:
                        df_list = pd.read_html(str(table))
                        for df in df_list:
                            if len(df) > 5 and len(df.columns) >= 5:
                                # Vérifier si c'est probablement le tableau des cours
                                if any(col in str(df.columns).lower() for col in ['symbole', 'nom', 'cours', 'variation']):
                                    return df, "Données depuis Google Cache"
                    except:
                        continue
        
        return None, "Échec fallback"
        
    except Exception as e:
        return None, f"Erreur fallback: {str(e)}"

# Interface
st.sidebar.header("Options de scraping")

method = st.sidebar.selectbox(
    "Méthode:",
    ["Auto-détection", "HTML direct", "Fallback (Google Cache)"],
    index=0
)

show_debug = st.sidebar.checkbox("Afficher le debug", value=False)

if st.sidebar.button("🎯 Lancer le scraping"):
    st.cache_data.clear()

# Statut
status_placeholder = st.sidebar.empty()

# Exécution
if method in ["Auto-détection", "HTML direct"]:
    status_placeholder.info("🔄 Scraping en cours...")
    
    with st.spinner("Analyse du site BRVM..."):
        df, message = fetch_brvm_with_js_simulation()
    
    if df is not None:
        status_placeholder.success(f"✅ {message}")
        st.success(f"Données récupérées ({len(df)} lignes)")
        
        # Afficher le dataframe
        st.dataframe(df, use_container_width=True, height=500)
        
        # Téléchargement
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Télécharger CSV",
            data=csv,
            file_name="brvm_data.csv",
            mime="text/csv"
        )
        
        # Statistiques
        with st.expander("📊 Statistiques"):
            if 'Variation' in df.columns:
                try:
                    df['Variation'] = pd.to_numeric(df['Variation'].str.replace('%', ''), errors='coerce')
                    st.write(f"Moyenne variation: {df['Variation'].mean():.2f}%")
                    st.write(f"Max hausse: {df['Variation'].max():.2f}%")
                    st.write(f"Max baisse: {df['Variation'].min():.2f}%")
                except:
                    st.write("Variation non numérique")
    
    else:
        status_placeholder.warning(f"⚠️ {message}")
        
        if method == "Auto-détection":
            st.warning("""
            ## ⚠️ Site BRVM détecté comme dynamique
            
            **Problème:** Le site charge les données via JavaScript après le chargement initial.
            
            **Solutions possibles:**
            
            ### 1. Utiliser Selenium (recommandé pour ce site)
            ```python
            from selenium import webdriver
            from selenium.webdriver.common.by import By
            import pandas as pd
            
            driver = webdriver.Chrome()
            driver.get("https://www.brvm.org/fr/cours-actions/0")
            time.sleep(5)  # Attendre le chargement JS
            
            # Extraire le tableau
            table = driver.find_element(By.TAG_NAME, "table")
            df = pd.read_html(table.get_attribute('outerHTML'))[0]
            ```
            
            ### 2. Chercher l'API réelle
            - Ouvrir DevTools (F12)
            - Onglet Network → Filtrer XHR/JS
            - Recharger la page
            - Chercher les requêtes qui retournent du JSON
            
            ### 3. Utiliser un service proxy
            - services comme ScrapingBee, ScraperAPI
            - Ils gèrent le JavaScript pour vous
            """)
            
            if st.button("🔄 Essayer la méthode Fallback"):
                with st.spinner("Tentative Fallback..."):
                    df_fallback, msg = fallback_scraping()
                    if df_fallback is not None:
                        st.dataframe(df_fallback)
                    else:
                        st.error(f"Fallback échoué: {msg}")

elif method == "Fallback (Google Cache)":
    status_placeholder.info("Tentative via Google Cache...")
    df, msg = fallback_scraping()
    
    if df is not None:
        st.dataframe(df)
    else:
        st.error(f"Échec: {msg}")

# Informations debug
if show_debug:
    with st.expander("🔍 Informations techniques"):
        st.write("**Analyse du site BRVM:**")
        st.write("""
        1. **Type:** Site Drupal avec chargement dynamique
        2. **JavaScript:** Requis pour afficher le tableau
        3. **Structure:** Données probablement chargées via AJAX/API interne
        4. **Défis:** 
           - Anti-scraping possible
           - Sessions ou tokens
           - Requêtes AJAX complexes
        """)
        
        st.write("**Pour trouver l'API manuellement:**")
        st.code("""
        1. Ouvrir https://www.brvm.org/fr/cours-actions/0
        2. F12 → Network
        3. Filtrer par XHR/JS
        4. Recharger la page
        5. Chercher les requêtes avec 'cours', 'data', 'json'
        6. Copier l'URL de la requête et l'utiliser directement
        """)

# Conclusion
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Recommandation:**
Pour le site BRVM, utilisez **Selenium** car il nécessite l'exécution de JavaScript.

**Alternative:** Cherchez l'API réelle via DevTools → Network.
""")
