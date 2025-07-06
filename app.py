import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

# RSI-beregning
@st.cache_data
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Screener-funksjon
@st.cache_data(show_spinner=False)
def screen_ticker(ticker, min_vol, min_swings, min_return_pct):
    try:
        df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
        if df.empty:
            return None
        if 'Volume' not in df.columns:
            return None

        mean_volume = df['Volume'].dropna().mean()
        if pd.isna(mean_volume) or mean_volume < min_vol:
            return None

        df['RSI'] = compute_rsi(df['Close'])
        swings = []
        last_rsi20_date = None

        for i in range(1, len(df)):
            prev_rsi = df['RSI'].iloc[i-1]
            curr_rsi = df['RSI'].iloc[i]
            if prev_rsi < 20 <= curr_rsi:
                last_rsi20_date = df.index[i]
            if prev_rsi < 70 <= curr_rsi and last_rsi20_date is not None:
                start_price = df.loc[last_rsi20_date, 'Close'] if last_rsi20_date in df.index else None
                end_price = df['Close'].iloc[i]
                if start_price is not None:
                    return_pct = (end_price - start_price) / start_price * 100
                    if return_pct >= min_return_pct:
                        swings.append((last_rsi20_date, df.index[i], return_pct))
                last_rsi20_date = None

        if len(swings) >= min_swings:
            success_rate = len(swings) / (len(df) / 252)  # Estimert antall per år
            return {
                "ticker": ticker,
                "swings": swings,
                "success_rate": success_rate,
                "avg_return": np.mean([s[2] for s in swings])
            }
        return None
    except Exception as e:
        st.warning(f"Feil i {ticker}: {e}")
        return None

# Streamlit app oppsett
st.set_page_config(page_title="Aksjescreener RSI", layout="wide")
st.title("📈 RSI-baserte aksjesvingninger – Screener")

# Test av yfinance
test_ticker = "AAPL"
test_df = yf.download(test_ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
if test_df.empty:
    st.error(f"⚠️ Ingen data for test-ticker {test_ticker} – sjekk internett eller yfinance.")
else:
    st.success(f"✅ Lastet ned {len(test_df)} rader for {test_ticker}")
    st.dataframe(test_df.tail())

# Sidebar filtre
st.sidebar.header("🔧 Filterinnstillinger")
min_vol = st.sidebar.number_input("Minimum gj.snittlig volum", value=50000)
min_swings = st.sidebar.number_input("Min. antall svingmønstre", value=1, min_value=1)
min_return_pct = st.sidebar.number_input("Min. avkastning per swing (%)", value=5.0)
min_success_rate = st.sidebar.slider("Min. treffrate per år", 0.0, 10.0, 0.5, step=0.1)

stocks = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "ORCL", "ADBE", "NFLX",
    "NOK.OL", "DNB.OL", "TEL.OL", "YAR.OL", "EQNR.OL"
]

results = []
st.subheader("🔍 Screener kjører")
with st.spinner("Analyserer aksjer, vennligst vent..."):
    for i, t in enumerate([s.strip().upper() for s in stocks if s.strip()]):
        st.write(f"▶️ Sjekker {t} ({i+1}/{len(stocks)})")
        res = screen_ticker(t, min_vol, min_swings, min_return_pct)
        if res and res["success_rate"] >= min_success_rate:
            results.append(res)

# Vis resultater
st.subheader("📊 Resultater")
if results:
    results_df = pd.DataFrame([{k: v for k, v in r.items() if k != 'swings'} for r in results])
    results_df = results_df.sort_values("success_rate", ascending=False)
    st.dataframe(results_df)
else:
    st.info("Ingen aksjer matchet kriteriene dine.")

# Manuell ticker-test
st.subheader("🔬 Test enkeltaksje")
ticker_input = st.text_input("🎯 Test ticker manuelt", "AAPL")
if st.button("Test ticker"):
    df = yf.download(ticker_input, period="5y", interval="1d", auto_adjust=True)
    if df.empty:
        st.error("Ingen data funnet.")
    else:
        df['RSI'] = compute_rsi(df['Close'])
        if 'RSI' in df.columns and 'Close' in df.columns:
            chart_df = df[['Close', 'RSI']].dropna()
            if not chart_df.empty:
                # Resetter index slik at Date blir kolonne for plotting
                chart_df_reset = chart_df.reset_index()
                # Her gjør vi melting for bedre plot med f.eks. Altair (valgfritt)
                # Men Streamlit line_chart takler også wide format:
                st.line_chart(chart_df)
            else:
                st.warning("⚠️ Ingen data å vise i grafen (etter dropp av NA).")
        else:
            st.warning("⚠️ RSI eller Close mangler i datasettet.")

