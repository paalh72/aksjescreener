import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime

# RSI-beregning
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Screener-funksjon
def screen_ticker(ticker, min_vol, min_swings, min_return_pct):
    try:
        df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or 'Volume' not in df.columns or df['Volume'].dropna().mean() < min_vol:
            return None
        df['RSI'] = compute_rsi(df['Close'])
        df = df.dropna(subset=["RSI"])

        swings = []
        last_rsi20_date = None

        for i in range(1, len(df)):
            prev, curr = df['RSI'].iat[i-1], df['RSI'].iat[i]
            if prev < 20 <= curr:
                last_rsi20_date = df.index[i]
            if prev < 70 <= curr and last_rsi20_date is not None:
                if last_rsi20_date in df.index:
                    close_20 = df.at[last_rsi20_date, 'Close']
                    close_70 = df['Close'].iat[i]
                    pct = (close_70 / close_20 - 1) * 100
                    swings.append(pct)
                last_rsi20_date = None

        if len(swings) >= min_swings:
            success_rate = 100 * sum(1 for pct in swings if pct >= min_return_pct) / len(swings)
            return {
                "ticker": ticker,
                "swings": len(swings),
                "success_rate": round(success_rate, 2),
                "avg_return": round(np.mean(swings), 2),
                "data": df,
            }
    except Exception as e:
        return None

# ---------- Streamlit UI ----------
st.set_page_config(page_title="Aksjescreener", layout="wide")
st.title("📈 Automatisk RSI Aksjescreener (5 år historikk)")

# Justerbare kriterier
min_vol = st.slider("Minimum gjennomsnittlig volum", 10000, 1000000, 100000, step=10000)
min_swings = st.slider("Minimum antall RSI 20–70 svingninger", 1, 20, 10)
min_return_pct = st.slider("Minimum avkastning fra RSI 20 til 70 (%)", 5, 50, 10)
min_success_rate = st.slider("Minimum suksessrate (%)", 0, 100, 50)

# Liste over tickere å sjekke (NB: begrens for testing)
st.subheader("📊 Selskaper å screene")
exchange = st.selectbox("Velg børs", ["NYSE (demo)", "Nasdaq Stockholm", "Oslo Børs"])
tickers = []

if exchange == "NYSE (demo)":
    tickers = ["AAPL", "MSFT", "TSLA", "NVDA", "GOOGL", "KO", "PEP"]
elif exchange ==

