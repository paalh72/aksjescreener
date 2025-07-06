import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# Konfigurasjon
st.set_page_config(page_title="Aksjescreener", layout="wide")
st.title("📈 RSI-baserte aksjesvingninger – Screener")

# RSI-beregning
@st.cache_data
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Screening-funksjon
@st.cache_data(show_spinner=False)
def screen_ticker(ticker, min_vol, min_swings, min_return_pct):
    try:
        df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
        if df.empty or 'Volume' not in df.columns or df['Volume'].dropna().mean() < min_vol:
            return None

        df['RSI'] = compute_rsi(df['Close'])
        swings = []
        last_rsi20_date = None

        for i in range(1, len(df)):
            prev_rsi = df['RSI'].iloc[i - 1]
            curr_rsi = df['RSI'].iloc[i]
            if prev_rsi < 20 <= curr_rsi:
                last_rsi20_date = df.index[i]
            elif prev_rsi < 70 <= curr_rsi and last_rsi20_date:
                if last_rsi20_date in df.index:
                    start_price = df.loc[last_rsi20_date, 'Close']
                    end_price = df['Close'].iloc[i]
                    return_pct = (end_price - start_price) / start_price * 100
                    if return_pct >= min_return_pct:
                        swings.append((last_rsi20_date, df.index[i], return_pct))
                last_rsi20_date = None

        if len(swings) >= min_swings:
            success_rate = len(swings) / (len(df) / 252)
            return {
                "ticker": ticker,
                "swings": swings,
                "success_rate": round(success_rate, 2),
                "avg_return": round(np.mean([s[2] for s in swings]), 2)
            }
        return None
    except Exception as e:
        st.warning(f"Feil i {ticker}: {e}")
        return None

# Sidebar-filtere
st.sidebar.header("🔧 Filterinnstillinger")
min_vol = st.sidebar.number_input("Minimum gj.snittlig volum", value=50000)
min_swings = st.sidebar.number_input("Min. antall svingmønstre", value=1)
min_return_pct = st.sidebar.number_input("Min. avkastning per swing (%)", value=5.0)

# Liste over tickere (kan utvides)
stocks = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "ORCL", "ADBE", "NFLX",
    "NOK.OL", "DNB.OL", "TEL.OL", "YAR.OL", "EQNR.OL"
]

# Screening
st.subheader("🔍 Screener-resultater")
results = []
with st.spinner("Analyserer aksjer..."):
    for i, ticker in enumerate(stocks):
        st.write(f"🔎 Sjekker {ticker} ({i + 1}/{len(stocks)})")
        res = screen_ticker(ticker, min_vol, min_swings, min_return_pct)
        if res:
            results.append(res)

if results:
    df_results = pd.DataFrame([{k: v for k, v in r.items() if k != 'swings'} for r in results])
    st.dataframe(df_results.sort_values("success_rate", ascending=False), use_container_width=True)
else:
    st.info("Ingen aksjer matchet kriteriene dine.")

# Manuell testing
st.subheader("🔬 Test enkeltaksje manuelt")
ticker_input = st.text_input("🎯 Skriv inn ticker for manuell RSI-visning", value="AAPL")

if st.button("Vis RSI-graf"):
    df = yf.download(ticker_input, period="5y", interval="1d", auto_adjust=True)
    if df.empty:
        st.error("Ingen data funnet.")
    else:
        df['RSI'] = compute_rsi(df['Close'])
        df_plot = df[['Close', 'RSI']].dropna().copy()
        df_plot.index.name = "Date"
        st.line_chart(df_plot)

