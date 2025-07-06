import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Aksjescreener", layout="wide")

st.title("Aksjescreener med RSI og volum")

# Funksjon for å regne RSI
def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Sett startdato til 1 år tilbake
start_date = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d")
end_date = datetime.now().strftime("%Y-%m-%d")

# Last inn tickers (her kan du erstatte med din liste)
default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

tickers_input = st.text_input("Skriv inn tickers separert med komma (f.eks. AAPL, MSFT, TSLA):", ",".join(default_tickers))
tickers = [ticker.strip().upper() for ticker in tickers_input.split(",") if ticker.strip()]

period_input = st.selectbox("Velg periode for data", options=["1y", "6mo", "3mo", "1mo"], index=0)

# Oppdater startdato basert på valgt periode
period_map = {
    "1y": 365,
    "6mo": 183,
    "3mo": 90,
    "1mo": 30
}
start_date = (datetime.now() - timedelta(days=period_map[period_input])).strftime("%Y-%m-%d")

st.write(f"Henter data fra {start_date} til {end_date}")

# Funksjon for å hente og bearbeide data per ticker
def fetch_data(ticker):
    try:
        df = yf.download(ticker, start=start_date, end=end_date)
        if df.empty:
            st.warning(f"Ingen data funnet for {ticker}")
            return None
        df["RSI"] = compute_rsi(df["Close"])
        df["Volume_MA20"] = df["Volume"].rolling(window=20).mean()
        df.dropna(inplace=True)
        return df
    except Exception as e:
        st.error(f"Feil i {ticker}: {e}")
        return None

# Hent data for alle tickere
all_data = {}
for ticker in tickers:
    df = fetch_data(ticker)
    if df is not None:
        all_data[ticker] = df

if not all_data:
    st.error("Ingen data tilgjengelig for tickere.")
    st.stop()

# Screener kriterier fra bruker
rsi_lower = st.slider("RSI lavere enn:", 0, 100, 30)
rsi_upper = st.slider("RSI høyere enn:", 0, 100, 70)
volume_multiple = st.number_input("Volum er X ganger 20-dagers snitt (min 1):", min_value=1.0, max_value=10.0, value=1.5, step=0.1)

# Finn aksjer som møter kriterier på siste dag i data
results = []
for ticker, df in all_data.items():
    last_rsi = df["RSI"].iloc[-1]
    last_volume = df["Volume"].iloc[-1]
    volume_ma20 = df["Volume_MA20"].iloc[-1]

    if (last_rsi >= rsi_lower and last_rsi <= rsi_upper) and (last_volume >= volume_multiple * volume_ma20):
        results.append({
            "Ticker": ticker,
            "Close": df["Close"].iloc[-1],
            "RSI": last_rsi,
            "Volume": last_volume,
            "Volume_MA20": volume_ma20,
        })

# Vis resultater
if results:
    results_df = pd.DataFrame(results)
    st.subheader("Aksjer som møter kriteriene:")
    st.dataframe(results_df)
else:
    st.write("Ingen aksjer møter kriteriene akkurat nå.")

# Velg ticker for graf
selected_ticker = st.selectbox("Velg aksje for graf", tickers)

if selected_ticker in all_data:
    chart_df = all_data[selected_ticker].reset_index()

    # Velg hvilke kolonner å vise i graf
    st.subheader(f"Pris og RSI for {selected_ticker}")
    chart_df_melted = chart_df.melt(id_vars="Date", value_vars=["Close", "RSI"], var_name="Type", value_name="Value")

    # Lag linjegraf med Streamlit
    st.line_chart(data=chart_df_melted, x="Date", y="Value", color="Type")


