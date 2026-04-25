import streamlit as st
import pandas as pd
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import io

# Page Config
st.set_page_config(page_title="Nigeria Mutual Fund Tracker", layout="wide", page_icon="🇳🇬")

st.title("🇳🇬 Mutual Fund ROI Tracker")
st.markdown("Developed by **Bamidele Adedeji** | Independent Researcher")

# Sidebar for investment input
st.sidebar.header("Investment Simulator")
monthly_budget = st.sidebar.slider("Your Monthly Investment (₦)", 5000, 50000, 10000, 5000)

@st.cache_data(ttl=86400)
def load_and_process_data():
    base_url = "https://sec.gov.ng/for-operators/keep-track-of-capital-market-data/net-asset-value-data/monthly-net-asset-value-for-collective-investment-schemes/2026-monthly-nav-for-cis/"
    root = "https://sec.gov.ng"
    
    # Scrape latest file link
    res = requests.get(base_url, headers={'User-Agent': 'Mozilla/5.0'})
    soup = BeautifulSoup(res.text, 'html.parser')
    links = [urljoin(root, a['href']) for a in soup.find_all('a', href=True) if a['href'].endswith('.xlsx')]
    
    if not links:
        return None

    # Load data
    file_res = requests.get(links[0])
    df = pd.read_excel(io.BytesIO(file_res.content), skiprows=3)
    
    # Process core columns by index for stability
    data = {
        'Fund Name': df.iloc[:, 1],
        'Manager': df.iloc[:, 2],
        'Net Asset Value': pd.to_numeric(df.iloc[:, 5], errors='coerce'),
        'Units Outstanding': pd.to_numeric(df.iloc[:, 6], errors='coerce'),
        'Yield YTD': pd.to_numeric(df.iloc[:, 12], errors='coerce')
    }
    
    clean_df = pd.DataFrame(data)
    clean_df['Unit Price (₦)'] = clean_df['Net Asset Value'] / clean_df['Units Outstanding']
    
    # Filter for Retail-friendly funds
    clean_df = clean_df[(clean_df['Unit Price (₦)'] > 0.1) & (clean_df['Unit Price (₦)'] < 10000)].copy()
    clean_df['Yield (%)'] = clean_df['Yield YTD'] * 100
    
    return clean_df

# Run App Logic
try:
    processed_data = load_and_process_data()
    
    if processed_data is not None:
        # Calculations based on user input
        processed_data['Units You Buy'] = monthly_budget / processed_data['Unit Price (₦)']
        
        # Display Metrics
        m1, m2, m3 = st.columns(3)
        m1.metric("Retail Funds Found", len(processed_data))
        m2.metric("Highest Yield", f"{processed_data['Yield (%)'].max():.2f}%")
        m3.metric("Your Budget", f"₦{monthly_budget:,}")

        # Interactive Table
        st.subheader("Monthly Investment Breakdown")
        st.dataframe(
            processed_data[['Fund Name', 'Yield (%)', 'Unit Price (₦)', 'Units You Buy', 'Manager']]
            .sort_values('Yield (%)', ascending=False),
            use_container_width=True
        )

        # Performance Chart
        st.subheader("Top 10 Performers")
        st.bar_chart(processed_data.sort_values('Yield (%)', ascending=False).head(10), x="Fund Name", y="Yield (%)")
    else:
        st.warning("No data found. Please check the SEC website source.")

except Exception as e:
    st.error(f"Data Processing Error: {e}")
