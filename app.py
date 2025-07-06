import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta
import matplotlib.pyplot as plt

st.set_page_config(page_title="Aksjescreener", layout="wide")

@st.cache_data
def hent_tickers(url, sep):
    df = pd.read_csv(url, sep=sep)
    if 'Symbol' not in df.columns:
        st.error(f"Symbol-kolonne ikke funnet i filen: {url}")
        return []
    return df['Symbol'].dropna().unique().tolist()

@st.cache_data
def hent_data(ticker, periode_aar=5):
    slutt = datetime.today()
    start = slutt - timedelta(days=periode_aar * 365)
    try:
        df = yf.download(ticker, start=start, end=slutt, progress=False)
        if df.empty:
            return None
        df['RSI'] = beregn_rsi(df['Close'])
        df.dropna(inplace=True)
        return df
    except Exception as e:
        print(f"Feil i {ticker}: {e}")
        return None

def beregn_rsi(priser, periode=14):
    delta = priser.diff()
    gevinst = delta.clip(lower=0)
    tap = -delta.clip(upper=0)
    gj_snitt_gevinst = gevinst.rolling(window=periode).mean()
    gj_snitt_tap = tap.rolling(window=periode).mean()
    rs = gj_snitt_gevinst / gj_snitt_tap
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyser_rsi(df, prosentgrense, min_økninger):
    lav_rsi = df[df['RSI'] < 20]
    hoy_rsi = df[df['RSI'] > 70]
    telling = 0
    suksesser = 0

    for i in range(len(lav_rsi)):
        start_dato = lav_rsi.index[i]
        neste_hoy = hoy_rsi[hoy_rsi.index > start_dato]
        if not neste_hoy.empty:
            slutt_dato = neste_hoy.index[0]
            pris_start = df.loc[start_dato]['Close']
            pris_slutt = df.loc[slutt_dato]['Close']
            endring = (pris_slutt - pris_start) / pris_start * 100
            telling += 1
            if endring >= prosentgrense:
                suksesser += 1

    if telling >= min_økninger:
        return suksesser, telling
    else:
        return None

st.title("📈 Aksjescreener med RSI-analyse")

url_oslo = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/oslo_bors_tickers.csv"
url_nyse = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/nyse_tickers.csv"

volumgrense = st.number_input("Minimum gjennomsnittlig volum", min_value=0, value=100_000)
prosentgrense = st.number_input("Minimum prosentøkning mellom RSI 20 og 70", min_value=1, value=10)
min_økninger = st.number_input("Minimum antall RSI-sykluser (20->70)", min_value=1, value=10)

st.markdown("---")

st.write("⏳ Laster tickere fra Oslo Børs og NYSE...")
tickers_oslo = hent_tickers(url_oslo, sep=';')
tickers_nyse = hent_tickers(url_nyse, sep=',')
alle_tickers = tickers_oslo + tickers_nyse

resultater = []

for ticker in alle_tickers:
    df = hent_data(ticker)
    if df is None or df.empty or 'Volume' not in df.columns:
        continue
    df['Volume'] = pd.to_numeric(df['Volume'], errors='coerce')
    df = df.dropna(subset=['Volume'])
    if df['Volume'].mean() < volumgrense:
        continue

    analyse = analyser_rsi(df, prosentgrense, min_økninger)
    if analyse:
        suksesser, totalt = analyse
        prosent = suksesser / totalt * 100
        resultater.append((ticker, suksesser, totalt, prosent))

if resultater:
    resultater.sort(key=lambda x: x[3], reverse=True)
    df_resultat = pd.DataFrame(resultater, columns=["Ticker", "Suksesser", "Totalt", "Treffsikkerhet (%)"])
    st.subheader("📋 Aksjer som matcher kriteriene:")
    valgt_rad = st.dataframe(df_resultat, use_container_width=True)

    valgt_ticker = st.selectbox("Velg en aksje for å vise graf:", df_resultat["Ticker"])
    if valgt_ticker:
        df_plot = hent_data(valgt_ticker)
        fig, ax1 = plt.subplots(figsize=(12, 6))
        ax1.plot(df_plot.index, df_plot['Close'], label='Close', color='blue')
        ax2 = ax1.twinx()
        ax2.plot(df_plot.index, df_plot['RSI'], label='RSI', color='orange')
        ax1.set_title(f"Kurs og RSI for {valgt_ticker}")
        ax1.set_ylabel("Kurs")
        ax2.set_ylabel("RSI")
        ax1.legend(loc='upper left')
        ax2.legend(loc='upper right')
        st.pyplot(fig)
else:
    st.warning("Ingen aksjer matchet kriteriene dine.")
