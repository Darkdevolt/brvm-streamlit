import streamlit as st
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# Charger clés depuis secrets Streamlit Cloud
SUPABASE_URL = st.secrets["https://chaoxloeeqgwaxrqmwdn.supabase.co"]
SUPABASE_KEY = st.secrets["eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNoYW94bG9lZXFnd2F4cnFtd2RuIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NTYyMDAzNTcsImV4cCI6MjA3MTc3NjM1N30.3Zlp9oXeTiZCetzU8VgjWooaEwEqEj1_cj8oglXt-Zs"]

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Scraping
url = "https://www.sikafinance.com/marches/cotation_NSBC.ci"
headers = {"User-Agent": "Mozilla/5.0"}
response = requests.get(url, headers=headers)
soup = BeautifulSoup(response.text, "html.parser")

price = soup.find("div", {"class": "val-cotation"}).text.strip()
variation = soup.find("div", {"class": "var-cotation"}).text.strip()

# Insérer dans Supabase
supabase.table("actions").insert({
    "name": "NSIA Banque",
    "price": float(price.replace("XOF","").replace(" ","")),
    "variation": variation
}).execute()

# Affichage
st.title("📊 Suivi NSIA Banque (BRVM)")
st.write(f"Prix actuel : {price}")
st.write(f"Variation : {variation}")

# Historique
st.subheader("Dernières données")
rows = supabase.table("actions").select("*").order("created_at", desc=True).limit(10).execute().data
for row in rows:
    st.write(f"{row['created_at']} | {row['name']} | {row['price']} XOF ({row['variation']})")
