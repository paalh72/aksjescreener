import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Aksjescreener", layout="wide")

st.title("Aksjescreener med teknisk analyse")

# Funksjon for å beregne RSI
def compute_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    data['RSI'] = rsi
    return data

# Last inn tickere - her bruker vi en statisk liste pga. problemer med nett-kall
tickers = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA",
    "NFLX", "FB", "NVDA", "INTC", "IBM"
]

selected_tickers = st.multiselect("Velg tickere for screening", tickers, default=["AAPL", "MSFT"])

# Sett start- og sluttdato (minst 1 år tilbake)
end_date = datetime.now()
start_date = end_date - timedelta(days=365*2)  # 2 år for trygg margin
st.write(f"Data lastet for perioden: {start_date.date()} til {end_date.date()}")

all_data = {}
errors = {}

# Hent data og beregn RSI
for ticker in selected_tickers:
    try:
        df = yf.download(ticker, start=start_date, end=end_date)
        if df.empty:
            errors[ticker] = "Ingen data funnet"
            continue
        df = compute_rsi(df)
        df.reset_index(inplace=True)
        all_data[ticker] = df
    except Exception as e:
        errors[ticker] = str(e)

# Vis eventuelle feil
if errors:
    st.subheader("Feil i datahenting")
    for ticker, error_msg in errors.items():
        st.error(f"Feil i {ticker}: {error_msg}")

# Vis tabeller og grafer for hver ticker
for ticker in selected_tickers:
    if ticker in all_data:
        df = all_data[ticker]
        st.subheader(f"Data for {ticker}")
        st.dataframe(df.tail(10))

        needed_cols = {"Date", "Close", "RSI"}
        if not needed_cols.issubset(df.columns):
            st.error(f"Data for {ticker} mangler nødvendige kolonner: {needed_cols - set(df.columns)}")
            continue

        chart_df_melted = df.melt(id_vars="Date", value_vars=["Close", "RSI"], var_name="Type", value_name="Value")
        st.line_chart(data=chart_df_melted, x="Date", y="Value", color="Type")

# Enkel screening basert på RSI
st.header("Screening basert på RSI")

rsi_threshold_low = st.slider("RSI lavere enn:", 0, 100, 30)
rsi_threshold_high = st.slider("RSI høyere enn:", 0, 100, 70)

screened_stocks = []

for ticker in selected_tickers:
    if ticker in all_data:
        df = all_data[ticker]
        if "RSI" in df.columns:
            latest_rsi = df["RSI"].dropna().iloc[-1] if not df["RSI"].dropna().empty else None
            if latest_rsi is not None and (latest_rsi < rsi_threshold_low or latest_rsi > rsi_threshold_high):
                screened_stocks.append((ticker, latest_rsi))

if screened_stocks:
    st.subheader("Stocks matching RSI criteria")
    screened_df = pd.DataFrame(screened_stocks, columns=["Ticker", "Latest RSI"])
    st.dataframe(screened_df)
else:
    st.info("Ingen aksjer matcher RSI-kriteriene nå.")

