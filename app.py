import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import datetime
from ta.momentum import RSIIndicator

try:
    from stqdm import stqdm
except ImportError:
    stqdm = lambda x, **kwargs: x  # fallback hvis stqdm ikke er installert

# --- HENT TICKERS ---
@st.cache_data
def hent_tickers(url):
    df = pd.read_csv(url, sep=None, engine="python")
    kolonner = df.columns.str.lower()
    if "symbol" in kolonner:
        symbol_col = df.columns[kolonner.get_loc("symbol")]
        return df[symbol_col].dropna().unique().tolist()
    else:
        return []

url_oslo = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/oslo_bors_tickers.csv"
url_nyse = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/nyse_tickers.csv"

tickers_oslo = hent_tickers(url_oslo)
tickers_nyse = hent_tickers(url_nyse)
alle_tickers = tickers_oslo + tickers_nyse

# --- PARAMETERE FRA BRUKER ---
st.title("📈 Aksjescreener basert på RSI og kursutvikling")

min_volum = st.number_input("Minimum snittvolum (aksjer per dag)", value=100000)
rsi_grense = st.slider("RSI-grenser (lav/høy)", 10, 90, (20, 70))
prisendring_prosent = st.number_input("Minimum kursendring mellom RSI 20 og 70 (%)", value=10)
min_treff = st.number_input("Minimum andel tilfeller med positiv utvikling (%)", value=50)

# --- HENT DATA ---
def hent_data(ticker):
    try:
        df = yf.download(ticker, period="5y", interval="1d", progress=False)
        if df.empty:
            return None
        df = df.dropna(subset=["Close", "Volume"])
        df["RSI"] = RSIIndicator(close=df["Close"], window=14).rsi()
        df = df.dropna(subset=["RSI"])
        return df
    except Exception:
        return None

# --- ANALYSER AKSJE ---
def analyser_aksje(df, rsi_bounds, min_change, min_pct_ok):
    low, high = rsi_bounds
    df = df.copy()
    df["Signal"] = None

    # Finn RSI lav og høy punkter
    signaler = []
    i = 0
    while i < len(df) - 1:
        if df["RSI"].iloc[i] <= low:
            for j in range(i+1, len(df)):
                if df["RSI"].iloc[j] >= high:
                    pris_start = df["Close"].iloc[i]
                    pris_slutt = df["Close"].iloc[j]
                    endring = (pris_slutt - pris_start) / pris_start * 100
                    signaler.append(endring)
                    i = j
                    break
            else:
                break
        i += 1

    if len(signaler) == 0:
        return None

    antall = len(signaler)
    antall_ok = sum(1 for x in signaler if x >= min_change)
    prosent_ok = round(antall_ok / antall * 100, 2)

    if prosent_ok >= min_pct_ok:
        return {
            "Ticker": df.name if hasattr(df, "name") else "",
            "Antall tilfeller": antall,
            "Positiv andel (%)": prosent_ok
        }
    return None

# --- KJØR SCREENER ---
resultater = []

for ticker in stqdm(alle_tickers, desc="Behandler tickere"):
    try:
        df = hent_data(ticker)
        if (
            df is None
            or "Volume" not in df.columns
            or df["Volume"].dropna().empty
            or df["Volume"].dropna().mean() < min_volum
        ):
            continue

        df.name = ticker  # for visning i resultat
        resultat = analyser_aksje(df, rsi_grense, prisendring_prosent, min_treff)
        if resultat:
            resultater.append(resultat)

    except Exception as e:
        st.warning(f"Feil i {ticker}: {e}")

# --- VIS RESULTAT ---
if resultater:
    df_resultat = pd.DataFrame(resultater).sort_values("Positiv andel (%)", ascending=False)
    valgt = st.selectbox("Velg aksje for å se graf", df_resultat["Ticker"])
    st.dataframe(df_resultat, use_container_width=True)

    if valgt:
        df_valgt = hent_data(valgt)
        st.line_chart(df_valgt[["Close", "RSI"]])
else:
    st.info("Ingen aksjer matchet kriteriene.")
