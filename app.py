import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib3
import time

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="BRVM Secteurs", page_icon="🏢", layout="wide")

st.title("🏢 Secteurs d'Activité BRVM")
st.markdown("*Classification des entreprises par secteur d'activité*")

# Liste des secteurs disponibles sur BRVM
SECTEURS = {
    "AGRICULTURE": "BRVM - AGRICULTURE",
    "AUTRES SECTEURS": "BRVM - AUTRES SECTEURS",
    "DISTRIBUTION": "BRVM - DISTRIBUTION",
    "FINANCE": "BRVM - FINANCE",
    "INDUSTRIE": "BRVM - INDUSTRIE",
    "SERVICES PUBLICS": "BRVM - SERVICES PUBLICS",
    "TRANSPORT": "BRVM - TRANSPORT"
}

@st.cache_data(ttl=300)
def scrape_secteur(secteur_nom):
    """Scrape les données d'un secteur spécifique"""
    url = "https://www.sikafinance.com/marches/secteurs"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9',
        }
        
        # Paramètres pour sélectionner le secteur
        params = {
            'secteur': secteur_nom
        }
        
        response = requests.get(url, headers=headers, params=params, verify=False, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Trouver le tableau
        table = soup.find('table')
        
        if not table:
            return None
        
        # Extraire les en-têtes
        headers_list = []
        thead = table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                headers_list.append(th.get_text(strip=True))
        
        # Extraire les données
        data = []
        tbody = table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                cols = row.find_all('td')
                if cols:
                    row_data = [col.get_text(strip=True) for col in cols]
                    data.append(row_data)
        
        if not headers_list or not data:
            return None
        
        df = pd.DataFrame(data, columns=headers_list)
        return df
    
    except Exception as e:
        st.error(f"Erreur lors du scraping du secteur {secteur_nom}: {str(e)}")
        return None

@st.cache_data(ttl=300)
def scrape_tous_secteurs():
    """Scrape tous les secteurs et compile les données"""
    tous_les_secteurs = {}
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i, (secteur_key, secteur_nom) in enumerate(SECTEURS.items()):
        status_text.text(f"Chargement du secteur: {secteur_key}...")
        
        df = scrape_secteur(secteur_nom)
        if df is not None and not df.empty:
            # Ajouter une colonne secteur
            df.insert(0, 'Secteur', secteur_key)
            tous_les_secteurs[secteur_key] = df
        
        progress_bar.progress((i + 1) / len(SECTEURS))
        time.sleep(0.5)  # Petit délai pour ne pas surcharger le serveur
    
    progress_bar.empty()
    status_text.empty()
    
    return tous_les_secteurs

# Interface principale
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.info(f"⏰ {datetime.now().strftime('%H:%M:%S')}")

st.markdown("---")

# Menu de sélection
mode = st.radio(
    "Mode d'affichage",
    ["📊 Vue par secteur", "📈 Vue consolidée"],
    horizontal=True
)

st.markdown("---")

if mode == "📊 Vue par secteur":
    # Vue par secteur individuel
    secteur_selectionne = st.selectbox(
        "Sélectionner un secteur",
        options=list(SECTEURS.keys()),
        index=0
    )
    
    with st.spinner(f"Chargement du secteur {secteur_selectionne}..."):
        df = scrape_secteur(SECTEURS[secteur_selectionne])
    
    if df is not None and not df.empty:
        st.success(f"✅ {len(df)} entreprise(s) dans le secteur {secteur_selectionne}")
        
        # Statistiques
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Entreprises", len(df))
        with col2:
            st.metric("Secteur", secteur_selectionne)
        with col3:
            st.metric("Source", "Sikafinance")
        
        st.markdown("---")
        
        # Afficher le tableau
        st.dataframe(
            df,
            use_container_width=True,
            height=400,
            hide_index=True
        )
        
        # Téléchargement
        csv = df.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label=f"📥 Télécharger {secteur_selectionne} en CSV",
            data=csv,
            file_name=f"brvm_{secteur_selectionne.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"⚠️ Aucune donnée disponible pour le secteur {secteur_selectionne}")

else:
    # Vue consolidée de tous les secteurs
    with st.spinner("Chargement de tous les secteurs..."):
        tous_secteurs = scrape_tous_secteurs()
    
    if tous_secteurs:
        # Statistiques globales
        total_entreprises = sum(len(df) for df in tous_secteurs.values())
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Entreprises", total_entreprises)
        with col2:
            st.metric("Nombre de Secteurs", len(tous_secteurs))
        with col3:
            st.metric("Date", datetime.now().strftime('%d/%m/%Y'))
        with col4:
            st.metric("Source", "Sikafinance")
        
        st.markdown("---")
        
        # Répartition par secteur
        st.subheader("📊 Répartition des entreprises par secteur")
        
        repartition = pd.DataFrame([
            {"Secteur": secteur, "Nombre d'entreprises": len(df)}
            for secteur, df in tous_secteurs.items()
        ])
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            st.bar_chart(repartition.set_index('Secteur'))
        
        with col2:
            st.dataframe(
                repartition,
                use_container_width=True,
                hide_index=True
            )
        
        st.markdown("---")
        
        # Afficher chaque secteur dans un expander
        st.subheader("📋 Détails par secteur")
        
        for secteur, df in tous_secteurs.items():
            with st.expander(f"🏢 {secteur} ({len(df)} entreprises)", expanded=False):
                st.dataframe(
                    df.drop('Secteur', axis=1) if 'Secteur' in df.columns else df,
                    use_container_width=True,
                    hide_index=True
                )
        
        # Téléchargement consolidé
        st.markdown("---")
        st.subheader("📥 Téléchargements")
        
        # Créer un DataFrame consolidé
        df_consolide = pd.concat(tous_secteurs.values(), ignore_index=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            csv_consolide = df_consolide.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📥 Télécharger TOUTES les données (CSV)",
                data=csv_consolide,
                file_name=f"brvm_tous_secteurs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
        
        with col2:
            csv_repartition = repartition.to_csv(index=False, encoding='utf-8-sig')
            st.download_button(
                label="📊 Télécharger la répartition (CSV)",
                data=csv_repartition,
                file_name=f"brvm_repartition_secteurs_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                use_container_width=True
            )
    else:
        st.error("❌ Impossible de charger les données des secteurs")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>Données provenant de <a href='https://www.sikafinance.com/marches/secteurs' target='_blank'>Sikafinance.com</a> | 
    Mise à jour automatique toutes les 5 minutes</small>
</div>
""", unsafe_allow_html=True)
