import streamlit as st
import pandas as pd
import requests
import json
from datetime import datetime

st.set_page_config(page_title="BRVM Scraper", layout="wide")
st.title("📊 Scraping Dynamique BRVM")

# --- REMPLACEZ CETTE URL PAR CELLE QUE VOUS TROUVEREZ ---
# Exemples d'URLs potentielles (À TROUVER VOUS-MÊME via F12 -> Réseau)
DATA_SOURCE_URLS = [
    "https://www.brvm.org/api/data/cours",  # Exemple 1
    "https://www.brvm.org/fr/cours-actions/data.json",  # Exemple 2
    # L'URL réelle sera différente. Trouvez-la.
]

@st.cache_data(ttl=300)
def fetch_data_from_api():
    """
    Tente de récupérer les données depuis une URL source potentielle.
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    for api_url in DATA_SOURCE_URLS:
        try:
            st.sidebar.info(f"Essai: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=10)
            
            if response.status_code == 200:
                # Essayer de parser la réponse en JSON
                try:
                    data = response.json()
                    # Ici, il faut ADAPTER la structure.
                    # Le JSON pourrait être une liste ou un dict.
                    # Exemple si c'est une liste d'objets :
                    df = pd.DataFrame(data)
                    st.sidebar.success(f"Succès via: {api_url}")
                    return df
                except json.JSONDecodeError:
                    # Ce n'est pas du JSON, peut-être du JSONP ou autre
                    st.sidebar.warning(f"{api_url} - Réponse non-JSON")
                    continue
        except requests.exceptions.RequestException as e:
            st.sidebar.warning(f"Échec {api_url}: {e}")
            continue
    
    # Si aucune URL directe ne fonctionne, on utilise Playwright pour intercepter
    return fetch_data_via_browser_interception()

def fetch_data_via_browser_interception():
    """
    Méthode de secours: Utilise un navigateur headless pour charger la page
    et intercepter les réponses réseau en temps réel.
    """
    st.sidebar.info("Aucune API directe trouvée. Lancement du navigateur...")
    
    try:
        from playwright.sync_api import sync_playwright
        
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # Liste pour stocker les réponses intéressantes
            captured_data = []
            
            # Écouteur d'événement pour intercepter les réponses
            def on_response(response):
                url = response.url
                # Filtrer les URLs qui pourraient contenir les données
                if any(keyword in url.lower() for keyword in ['cours', 'data', 'action', 'json', 'api']):
                    try:
                        # Essayer d'extraire le JSON de la réponse
                        json_data = response.json()
                        captured_data.append({
                            "url": url,
                            "data": json_data
                        })
                        st.sidebar.text(f"✅ Donnée interceptée: {url}")
                    except:
                        pass  # Ce n'était pas du JSON
            
            page.on("response", on_response)
            
            # Naviguer vers la page et attendre
            page.goto("https://www.brvm.org/fr/cours-actions/0", wait_until="networkidle", timeout=30000)
            
            # Attendre un peu plus pour que tout se charge
            page.wait_for_timeout(5000)
            
            browser.close()
            
            # Analyser les données capturées
            if captured_data:
                st.sidebar.success(f"Intercepté {len(captured_data)} flux de données.")
                # Ici, il faut analyser la structure des 'captured_data' pour en extraire un DataFrame.
                # C'est la partie la plus spécifique au site.
                # On prend le premier flux de données comme exemple :
                raw_json = captured_data[0]["data"]
                df = pd.json_normalize(raw_json)  # Adaptez cette ligne selon la structure
                return df
            else:
                st.sidebar.error("Aucune donnée interceptée.")
                return None
                
    except Exception as e:
        st.sidebar.error(f"Erreur Playwright: {e}")
        return None

# --- Interface Streamlit ---
if st.sidebar.button("🔄 Extraire les données"):
    st.cache_data.clear()

with st.spinner("Recherche et extraction des données en cours..."):
    df = fetch_data_from_api()

if df is not None and not df.empty:
    st.success(f"✅ Données extraites avec succès ! ({len(df)} lignes)")
    
    # Nettoyage basique des colonnes
    df.columns = [col.replace('.', '_').strip() for col in df.columns]
    
    st.dataframe(df, use_container_width=True, height=600)
    
    # Option de téléchargement
    csv = df.to_csv(index=False).encode('utf-8-sig')
    st.download_button(
        label="📥 Télécharger en CSV",
        data=csv,
        file_name=f"brvm_data_{datetime.now().strftime('%Y%m%d_%H%M')}.csv",
        mime="text/csv"
    )
    
    # Section DEBUG : Afficher la structure brute pour vous aider
    with st.expander("🔧 Debug : Afficher la structure des données brutes"):
        st.json(df.head(2).to_dict(orient='records'))
        st.write("**Types de données :**")
        st.write(df.dtypes)
        
else:
    st.error("""
    **Échec de l'extraction.**
    
    **Prochaines étapes MANUELLES indispensables :**
    
    1.  **Ouvrez le site dans Chrome/Firefox.**
    2.  **Ouvrez l'onglet `Réseau` (F12 > Network).**
    3.  **Rechargez la page.**
    4.  **Cherchez une requête qui retourne les données des actions** (filtrez par XHR/JS).
    5.  **Cliquez sur cette requête** > Onglet `Réponse` (Response) ou `Prévisualisation` (Preview). Vous verrez les données en JSON.
    6.  **Copiez l'URL complète de cette requête** (onglet `En-têtes` / Headers).
    7.  **Collez cette URL** dans la variable `DATA_SOURCE_URLS` dans le code ci-dessus (remplacez mes exemples).
    8.  **Adaptez le code** dans la fonction `fetch_data_from_api()` pour parser la structure spécifique du JSON que vous voyez.
    """)
