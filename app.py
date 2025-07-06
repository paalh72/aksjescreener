import streamlit as st
import pandas as pd
import yfinance as yf
import datetime
from stqdm import stqdm 

st.set_page_config(page_title="Aksjescreener", layout="wide")
st.title("🔍 Aksjescreener – NYSE og Oslo Børs")

# URLs til dine CSV-filer (råformat)
url_oslo = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/oslo_bors_tickers.csv"
url_nyse = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/nyse_tickers.csv"

@st.cache_data(ttl=86400)
def hent_tickers_oslo():
    df = pd.read_csv(url_oslo, sep=';')
    return df['Symbol'].dropna().unique().tolist()

@st.cache_data(ttl=86400)
def hent_tickers_nyse():
    df = pd.read_csv(url_nyse)
    return df['Symbol'].dropna().unique().tolist()

tickers_oslo = hent_tickers_oslo()
tickers_nyse = hent_tickers_nyse()

alle_tickers = tickers_oslo + tickers_nyse

st.sidebar.markdown("### 🎯 Screening-kriterier")
min_volum = st.sidebar.number_input("Min. snittvolum (over 5 år)", value=100_000)
min_avkastning = st.sidebar.number_input("Min. avkastning mellom RSI 20→70", value=10)
min_antall_svingninger = st.sidebar.number_input("Min. antall RSI-svingninger (20→70)", value=10)
min_suksessrate = st.sidebar.slider("Min. % ganger 10%+ kursøkning etter RSI 20→70", 0, 100, 50)

@st.cache_data(ttl=86400)
def beregn_rsi(df, periode=14):
    delta = df['Close'].diff()
    gevinst = delta.where(delta > 0, 0)
    tap = -delta.where(delta < 0, 0)
    snitt_gevinst = gevinst.rolling(window=periode).mean()
    snitt_tap = tap.rolling(window=periode).mean()
    rs = snitt_gevinst / snitt_tap
    return 100 - (100 / (1 + rs))

@st.cache_data(ttl=86400)
def hent_data(ticker):
    slutt_dato = datetime.date.today()
    start_dato = slutt_dato - datetime.timedelta(days=5*365)
    try:
        df = yf.download(ticker, start=start_dato, end=slutt_dato)
        if df.empty or len(df) < 100:
            return None
        df['RSI'] = beregn_rsi(df)
        df['Ticker'] = ticker
        return df
    except Exception as e:
        return None

st.write("🔄 Kjører screening på aksjer. Dette kan ta noen minutter...")

resultater = []

for ticker in stqdm(alle_tickers, desc="Behandler tickere"):
    df = hent_data(ticker)
    if df is None or df['Volume'].mean() < min_volum:
        continue

    signaler = []
    i = 0
    while i < len(df) - 1:
        if df['RSI'].iloc[i] < 20:
            start_index = i
            i += 1
            while i < len(df) and df['RSI'].iloc[i] < 70:
                i += 1
            if i < len(df):
                slutt_index = i
                pris_vekst = (df['Close'].iloc[slutt_index] - df['Close'].iloc[start_index]) / df['Close'].iloc[start_index] * 100
                signaler.append(pris_vekst)
        i += 1

    if len(signaler) >= min_antall_svingninger:
        antall_treff = sum(1 for s in signaler if s >= min_avkastning)
        prosent_treff = antall_treff / len(signaler) * 100
        if prosent_treff >= min_suksessrate:
            resultater.append({
                "Ticker": ticker,
                "Volum snitt": int(df['Volume'].mean()),
                "Antall RSI-sving": len(signaler),
                "10%+ økning": f"{prosent_treff:.1f}%",
                "Siste kurs": round(df['Close'].iloc[-1], 2)
            })

if resultater:
    df_resultat = pd.DataFrame(resultater).sort_values("10%+ økning", ascending=False)
    st.success(f"Fant {len(df_resultat)} aksjer som matcher kriteriene.")
    valgt = st.dataframe(df_resultat, use_container_width=True)

    valgt_ticker = st.selectbox("📈 Velg aksje for å vise 5-års historikk", df_resultat["Ticker"].tolist())
    df_plot = hent_data(valgt_ticker)

    if df_plot is not None:
        import matplotlib.pyplot as plt
        fig, ax1 = plt.subplots(figsize=(12, 5))
        ax1.plot(df_plot.index, df_plot['Close'], label='Pris', color='blue')
        ax2 = ax1.twinx()
        ax2.plot(df_plot.index, df_plot['RSI'], label='RSI', color='orange')
        ax1.set_title(f"{valgt_ticker} – Kurs og RSI")
        ax1.set_ylabel("Pris")
        ax2.set_ylabel("RSI")
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        st.pyplot(fig)
else:
    st.warning("Ingen aksjer fant som matcher kriteriene.")
