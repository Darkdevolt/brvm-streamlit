import streamlit as st
import requests
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import urllib3

# Désactiver les warnings SSL
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="BRVM Secteurs", page_icon="🏢", layout="wide")

st.title("🏢 Secteurs d'Activité BRVM")
st.markdown("*Classification des entreprises par secteur d'activité*")

# Classification manuelle des entreprises par secteur (basée sur BRVM)
SECTEURS_MAPPING = {
    # AGRICULTURE
    "PALMCI": "Agriculture",
    "SAPH CI": "Agriculture",
    "SICOR": "Agriculture",
    "SOGB": "Agriculture",
    "SUCRIVOIRE": "Agriculture",
    
    # FINANCE
    "BANK OF AFRICA BENIN": "Finance",
    "BANK OF AFRICA BURKINA FASO": "Finance",
    "BANK OF AFRICA CI": "Finance",
    "BANK OF AFRICA MALI": "Finance",
    "BANK OF AFRICA NIGER": "Finance",
    "BANK OF AFRICA SENEGAL": "Finance",
    "BANQUE INTERNATIONALE POUR LE COMMERCE DU BENIN": "Finance",
    "BICICI": "Finance",
    "CORIS BANK INTERNATIONAL BF": "Finance",
    "ECOBANK CI": "Finance",
    "NSIA BANQUE": "Finance",
    "ORAGROUP TOGO": "Finance",
    "SGBCI": "Finance",
    "SOCIETE IVOIRIENNE DE BANQUE CI": "Finance",
    "SMB CI": "Finance",
    
    # DISTRIBUTION
    "BERNABE": "Distribution",
    "CFAO CI": "Distribution",
    "TRACTAFRIC MOTORS CI": "Distribution",
    "VIVO ENERGY CI": "Distribution",
    
    # INDUSTRIE
    "FILTISAC CI": "Industrie",
    "NEI CEDA CI": "Industrie",
    "NESTLE CI": "Industrie",
    "SAFCA CI": "Industrie",
    "SERVAIR ABIDJAN CI": "Industrie",
    "SETAO CI": "Industrie",
    "SICABLE CI": "Industrie",
    "SITAB": "Industrie",
    "SOLIBRA CI": "Industrie",
    "TOTAL CI": "Industrie",
    "TOTAL SENEGAL": "Industrie",
    "UNILEVER CI": "Industrie",
    "UNIWAX CI": "Industrie",
    
    # SERVICES PUBLICS
    "CIE CI": "Services Publics",
    "ONATEL BF": "Services Publics",
    "ORANGE CI": "Services Publics",
    "SODECI": "Services Publics",
    "SONATEL": "Services Publics",
    
    # TRANSPORT
    "AFRICA GLOBAL LOGISTICS": "Transport",
    
    # AUTRES SECTEURS
    "CROWN SIEM": "Autres Secteurs",
    "ERIUM": "Autres Secteurs",
    "ETI TG": "Autres Secteurs",
    "LOTERIE NATIONALE DU BENIN": "Autres Secteurs",
    "MOVIS CI": "Autres Secteurs",
}

@st.cache_data(ttl=300)
def scrape_toutes_actions():
    """Scrape toutes les actions depuis la page A-Z"""
    url = "https://www.sikafinance.com/marches/aaz"
    
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'fr-FR,fr;q=0.9',
        }
        
        response = requests.get(url, headers=headers, verify=False, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Trouver toutes les tables
        tables = soup.find_all('table')
        
        if len(tables) < 2:
            return None
        
        # Deuxième table : Les actions
        actions_table = tables[1]
        actions_data = []
        actions_headers = []
        
        # Extraire les en-têtes
        thead = actions_table.find('thead')
        if thead:
            for th in thead.find_all('th'):
                actions_headers.append(th.get_text(strip=True))
        
        # Extraire les données
        tbody = actions_table.find('tbody')
        if tbody:
            for row in tbody.find_all('tr'):
                cols = row.find_all('td')
                if cols:
                    row_data = [col.get_text(strip=True) for col in cols]
                    actions_data.append(row_data)
        
        if not actions_headers or not actions_data:
            return None
        
        df = pd.DataFrame(actions_data, columns=actions_headers)
        
        # Ajouter la colonne secteur
        df['Secteur'] = df['Nom'].map(SECTEURS_MAPPING).fillna('Non classifié')
        
        # Réorganiser les colonnes pour mettre Secteur en second
        cols = df.columns.tolist()
        cols = [cols[0], cols[-1]] + cols[1:-1]
        df = df[cols]
        
        return df
    
    except Exception as e:
        st.error(f"Erreur lors du scraping: {str(e)}")
        return None

# Interface principale
col1, col2, col3 = st.columns([1, 1, 4])
with col1:
    if st.button("🔄 Rafraîchir", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

with col2:
    st.info(f"⏰ {datetime.now().strftime('%H:%M:%S')}")

st.markdown("---")

# Charger les données
with st.spinner("Chargement des données BRVM..."):
    df_complet = scrape_toutes_actions()

if df_complet is not None and not df_complet.empty:
    st.success(f"✅ {len(df_complet)} entreprises chargées avec succès")
    
    # Statistiques globales
    secteurs_uniques = df_complet['Secteur'].unique()
    nb_secteurs = len([s for s in secteurs_uniques if s != 'Non classifié'])
    
    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Entreprises", len(df_complet))
    with col2:
        st.metric("Secteurs", nb_secteurs)
    with col3:
        st.metric("Date", datetime.now().strftime('%d/%m/%Y'))
    with col4:
        st.metric("Source", "Sikafinance")
    
    st.markdown("---")
    
    # Onglets pour différentes vues
    tab1, tab2, tab3 = st.tabs(["📊 Vue par secteur", "📈 Vue globale", "📋 Statistiques"])
    
    with tab1:
        st.subheader("Filtrer par secteur")
        
        # Sélecteur de secteur
        secteur_selectionne = st.selectbox(
            "Choisir un secteur",
            options=['Tous'] + sorted([s for s in secteurs_uniques if s != 'Non classifié']),
            index=0
        )
        
        # Filtrer les données
        if secteur_selectionne == 'Tous':
            df_filtre = df_complet
        else:
            df_filtre = df_complet[df_complet['Secteur'] == secteur_selectionne]
        
        # Barre de recherche
        search = st.text_input("🔍 Rechercher une entreprise", placeholder="Nom de l'entreprise...")
        
        if search:
            mask = df_filtre['Nom'].str.contains(search, case=False, na=False)
            df_filtre = df_filtre[mask]
            st.info(f"🔎 {len(df_filtre)} résultat(s) trouvé(s)")
        
        # Affichage
        st.dataframe(
            df_filtre,
            use_container_width=True,
            height=500,
            hide_index=True
        )
        
        # Téléchargement
        csv = df_filtre.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label=f"📥 Télécharger ({secteur_selectionne}) en CSV",
            data=csv,
            file_name=f"brvm_{secteur_selectionne.lower().replace(' ', '_')}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with tab2:
        st.subheader("Toutes les entreprises")
        
        # Tableau complet
        st.dataframe(
            df_complet,
            use_container_width=True,
            height=500,
            hide_index=True
        )
        
        # Téléchargement
        csv_complet = df_complet.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📥 Télécharger toutes les données en CSV",
            data=csv_complet,
            file_name=f"brvm_toutes_entreprises_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    
    with tab3:
        st.subheader("📊 Répartition par secteur")
        
        # Calculer la répartition
        repartition = df_complet['Secteur'].value_counts().reset_index()
        repartition.columns = ['Secteur', 'Nombre d\'entreprises']
        repartition = repartition[repartition['Secteur'] != 'Non classifié']
        
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
        
        # Détails par secteur dans des expanders
        st.subheader("Détails par secteur")
        
        for secteur in sorted(repartition['Secteur'].unique()):
            df_secteur = df_complet[df_complet['Secteur'] == secteur]
            with st.expander(f"🏢 {secteur} ({len(df_secteur)} entreprises)", expanded=False):
                st.dataframe(
                    df_secteur.drop('Secteur', axis=1),
                    use_container_width=True,
                    hide_index=True
                )
        
        # Télécharger la répartition
        csv_repartition = repartition.to_csv(index=False, encoding='utf-8-sig')
        st.download_button(
            label="📊 Télécharger la répartition en CSV",
            data=csv_repartition,
            file_name=f"brvm_repartition_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )

else:
    st.error("❌ Impossible de charger les données. Veuillez réessayer plus tard.")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666;'>
    <small>Données provenant de <a href='https://www.sikafinance.com/marches/aaz' target='_blank'>Sikafinance.com</a> | 
    Classification sectorielle basée sur BRVM | Mise à jour automatique toutes les 5 minutes</small>
</div>
""", unsafe_allow_html=True)
