import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
from datetime import datetime, timedelta
import requests
from io import StringIO

st.set_page_config(layout="wide")

@st.cache_data(show_spinner=False)
def hent_nyse_tickers():
    url = "https://datahub.io/core/nyse-other-listings/r/nyse-other-listings.csv"
    df = pd.read_csv(url)
    tickers = df['ACT Symbol'].tolist()
    return tickers

@st.cache_data(show_spinner=False)
def hent_oslo_bors_tickers():
    url = "https://raw.githubusercontent.com/marketplace/actions/norwegian-stock-listings/main/norwegian_stock_listings.csv"
    df = pd.read_csv(url)
    tickers = [t + ".OL" for t in df['Ticker']]
    return tickers

@st.cache_data(show_spinner=False)
def hent_stockholm_tickers():
    url = "https://raw.githubusercontent.com/nyhetsspeilet/stock-list/master/stock-list-Stockholm.csv"
    df = pd.read_csv(url)
    tickers = [t + ".ST" for t in df['Ticker']]
    return tickers

def beregn_rsi(prices, period=14):
    delta = prices.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def finn_rsi_svingninger(rsi_series, low=20, high=70):
    """
    Finn tidspunkt der RSI krysser under low og over high,
    returnerer en liste av (start_idx, end_idx) perioder hvor RSI
    har beveget seg mellom low og high.
    """
    periods = []
    in_period = False
    start_idx = None
    
    for i in range(1, len(rsi_series)):
        if not in_period:
            if rsi_series.iloc[i-1] < low and rsi_series.iloc[i] >= low:
                in_period = True
                start_idx = i
        else:
            if rsi_series.iloc[i-1] <= high and rsi_series.iloc[i] > high:
                in_period = False
                end_idx = i
                periods.append((start_idx, end_idx))
                start_idx = None
    return periods

@st.cache_data(show_spinner=True)
def hent_data(ticker, periode_aar=5):
    slutt = datetime.today()
    start = slutt - timedelta(days=periode_aar*365)
    df = yf.download(ticker, start=start, end=slutt, progress=False)
    return df

def volum_filter(df, volum_min):
    if df.empty:
        return False
    avg_volum = df['Volume'].mean()
    return avg_volum >= volum_min

def screener(ticker, volum_min, rsi_low, rsi_high, min_svingninger, min_prosent_vekst, min_prosent_andel):
    df = hent_data(ticker)
    if df.empty or len(df) < 50:
        return None

    if not volum_filter(df, volum_min):
        return None

    df['RSI'] = beregn_rsi(df['Close'])
    df = df.dropna(subset=['RSI'])

    svingninger = finn_rsi_svingninger(df['RSI'], low=rsi_low, high=rsi_high)
    if len(svingninger) < min_svingninger:
        return None

    # Sjekk prisvekst mellom RSI 20 og RSI 70 i forrige periode
    antall_ok = 0
    for (start_idx, end_idx) in svingninger:
        pris_rsi_low = df['Close'].iloc[start_idx-1] if start_idx-1 >= 0 else None
        pris_rsi_high = df['Close'].iloc[end_idx] if end_idx < len(df) else None
        if pris_rsi_low is None or pris_rsi_high is None:
            continue
        prosent_vekst = (pris_rsi_high - pris_rsi_low) / pris_rsi_low * 100
        if prosent_vekst >= min_prosent_vekst:
            antall_ok += 1

    andel_ok = antall_ok / len(svingninger)
    if andel_ok < min_prosent_andel:
        return None

    return {
        'ticker': ticker,
        'antall_svingninger': len(svingninger),
        'andel_ok': andel_ok,
        'data': df
    }

# --- UI ---

st.title("Aksjescreener for NYSE, Oslo Børs og Nasdaq Stockholm")

with st.expander("Innstillinger screener"):
    volum_min = st.number_input("Min. gjennomsnittlig volum per dag", min_value=1000, value=100000, step=1000)
    rsi_low = st.slider("RSI lav grense", 0, 100, 20)
    rsi_high = st.slider("RSI høy grense", 0, 100, 70)
    min_svingninger = st.number_input("Min antall RSI svingninger (20-70)", min_value=1, value=10, step=1)
    min_prosent_vekst = st.number_input("Min % vekst mellom RSI 20 og 70", min_value=0, value=10)
    min_prosent_andel = st.slider("Min % av svingninger som må ha denne veksten", 0.0, 1.0, 0.5, 0.05)

if st.button("Kjør screening, dette kan ta noen minutter!"):
    med_feil = []
    gode_aksjer = []

    st.info("Henter tickere...")

    tickers_nyse = hent_nyse_tickers()
    tickers_oslo = hent_oslo_bors_tickers()
    tickers_sto = hent_stockholm_tickers()

    alle_tickers = tickers_nyse + tickers_oslo + tickers_sto
    st.write(f"Totalt {len(alle_tickers)} tickere å screene")

    bar = st.progress(0)
    for i, ticker in enumerate(alle_tickers):
        try:
            resultat = screener(ticker, volum_min, rsi_low, rsi_high, min_svingninger, min_prosent_vekst, min_prosent_andel)
            if resultat is not None:
                gode_aksjer.append(resultat)
        except Exception as e:
            med_feil.append((ticker, str(e)))

        if i % 10 == 0:
            bar.progress(i / len(alle_tickers))

    bar.progress(1)

    st.success(f"Ferdig screening. Fant {len(gode_aksjer)} aksjer som matcher kriteriene.")

    if med_feil:
        st.warning(f"Feil oppstod på {len(med_feil)} tickere, vises ikke her.")

    if gode_aksjer:
        df_resultater = pd.DataFrame([{
            'Ticker': a['ticker'],
            'Antall svingninger': a['antall_svingninger'],
            'Andel OK': f"{a['andel_ok']*100:.1f} %"
        } for a in gode_aksjer])
        st.dataframe(df_resultater)

        valgt = st.selectbox("Velg aksje for detaljert visning", df_resultater['Ticker'])

        valgt_aksje = next(x for x in gode_aksjer if x['ticker'] == valgt)
        df_vis = valgt_aksje['data'][['Close', 'Volume']].copy()
        df_vis['RSI'] = beregn_rsi(df_vis['Close'])
        df_vis = df_vis.dropna()

        st.line_chart(df_vis[['Close', 'RSI']])
        st.bar_chart(df_vis['Volume'])

else:
    st.info("Trykk på knappen for å starte screening.")



