import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import altair as alt

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
        if df.empty or 'Volume' not in df.columns or df['Volume'].dropna().mean() < min_vol:
            return None

        df['RSI'] = compute_rsi(df['Close'])
        swings = []
        last_rsi20_date = None
        for i in range(1, len(df)):
            prev_rsi = df['RSI'].iloc[i-1]
            curr_rsi = df['RSI'].iloc[i]
            if prev_rsi < 20 <= curr_rsi:
                last_rsi20_date = df.index[i]
            if prev_rsi < 70 <= curr_rsi and last_rsi20_date:
                start_price = df.loc[last_rsi20_date, 'Close'] if last_rsi20_date in df.index else None
                end_price = df['Close'].iloc[i]
                if start_price:
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

# --- Streamlit UI setup ---
st.set_page_config(page_title="Aksjescreener", layout="wide")
st.title("📈 RSI-baserte aksjesvingninger – Screener")

# Test om yfinance fungerer
test_ticker = "AAPL"
test_df = yf.download(test_ticker, period="5y", interval="1d", auto_adjust=True, progress=False)
if test_df.empty:
    st.error(f"⚠️ Ingen data for test-ticker {test_ticker} – sjekk internett eller yfinance.")
else:
    st.success(f"✅ Lastet ned {len(test_df)} rader for {test_ticker}")
    st.dataframe(test_df.tail())

# Sidebar filter
st.sidebar.header("🔧 Filterinnstillinger")
min_vol = st.sidebar.number_input("Minimum gj.snittlig volum", value=50000)
min_swings = st.sidebar.number_input("Min. antall svingmønstre", value=1)
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
        if res:
            # Her kan du legge inn filter på success_rate hvis ønskelig
            if res['success_rate'] >= min_success_rate:
                results.append(res)

# Vis resultater
st.subheader("📊 Resultater")
if results:
    results_df = pd.DataFrame([{k: v for k, v in r.items() if k != 'swings'} for r in results])
    results_df = results_df.sort_values("success_rate", ascending=False)
    st.dataframe(results_df)
else:
    st.info("Ingen aksjer matchet kriteriene dine.")

# Manuell test og plotting av ticker
st.subheader("🔬 Test enkeltaksje")
ticker_input = st.text_input("🎯 Test ticker manuelt", "AAPL")
if st.button("Test ticker"):
    df = yf.download(ticker_input, period="5y", interval="1d", auto_adjust=True)
    if df.empty:
        st.error("Ingen data funnet.")
    else:
        # Flatten MultiIndex kolonner hvis nødvendig
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = ['_'.join(filter(None, map(str, col))).strip() for col in df.columns.values]
            st.write("Flattened kolonner:", df.columns.tolist())

        # Finn riktig Close-kolonne
        close_cols = [col for col in df.columns if col.lower().startswith('close')]
        if not close_cols:
            st.error("Fant ikke 'Close'-kolonne i data.")
        else:
            close_col = close_cols[0]
            df['RSI'] = compute_rsi(df[close_col])

            chart_df = df[[close_col, 'RSI']].dropna()
            chart_df = chart_df.rename(columns={close_col: 'Close'})

            if not chart_df.empty:
                chart_df_reset = chart_df.reset_index()

                # Sørg for at dato-kolonnen heter 'Date'
                if 'Date' not in chart_df_reset.columns:
                    date_col = chart_df_reset.columns[0]
                    chart_df_reset.rename(columns={date_col: 'Date'}, inplace=True)

                try:
                    chart_df_melted = chart_df_reset.melt(
                        id_vars='Date',
                        value_vars=['Close', 'RSI'],
                        var_name='Type',
                        value_name='Value'
                    )

                    chart = alt.Chart(chart_df_melted).mark_line().encode(
                        x='Date:T',
                        y='Value:Q',
                        color='Type:N'
                    ).properties(
                        width=800,
                        height=400,
                        title=f"{ticker_input.upper()} – Close & RSI"
                    ).interactive()

                    st.altair_chart(chart, use_container_width=True)
                except KeyError as e:
                    st.error(f"Feil i melt-funksjonen: {e}")
                    st.write(chart_df_reset.head())
            else:
                st.warning("⚠️ Ingen data å vise i grafen (etter dropp av NA).")


