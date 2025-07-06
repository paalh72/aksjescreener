import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go

# ----- Indikatorfunksjoner -----

def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# ----- Screener-funksjon -----

def screen_ticker(ticker, min_vol, min_swings, min_return_pct):
    df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True)
    if df.empty or 'Volume' not in df.columns:
        return None
    try:
        avg_vol = float(df['Volume'].dropna().mean())
    except:
        return None
    if avg_vol < min_vol:
        return None

    df['RSI'] = compute_rsi(df['Close'])
    swings = []
    last_rsi20_date = None

    for i in range(1, len(df)):
        prev, curr = df['RSI'].iat[i-1], df['RSI'].iat[i]
        if prev < 20 <= curr:
            last_rsi20_date = df.index[i]
        if prev < 70 <= curr and last_rsi20_date is not None:
            close_20 = df.at[last_rsi20_date, 'Close']
            close_70 = df['Close'].iat[i]
            pct = (close_70 / close_20 - 1) * 100
            swings.append(pct)
            last_rsi20_date = None

    if len(swings) < min_swings:
        return None

    success_rate = sum(p >= min_return_pct for p in swings) / len(swings) * 100

    return {"ticker": ticker, "swings": len(swings), "success_rate": success_rate, "df": df}

# ----- Streamlit UI -----

st.set_page_config(page_title="Aksjescreener", layout="wide")
st.title("📊 RSI‑basert Aksjescreener – 5 år data")

# Input: ticker-liste
tickers = st.text_area(
    "Tickere/securities (komma-separated)",
    value="AAPL,MSFT,TSLA,EQNR.OL,DNB.OL,ERIC-B.ST"
).upper().split(",")

# Kriterier
st.sidebar.header("Screener‑innstillinger")
min_vol = st.sidebar.number_input("Min. snittvolum", value=100000, step=50000)
min_swings = st.sidebar.number_input("Min. antall RSI‑20→70 sving", value=10, step=1)
min_return_pct = st.sidebar.number_input("Min. %økning fra RSI20→70", value=10)
min_success = st.sidebar.slider("Min. andel ± kriterie (%)", 0, 100, 50)

# Kjør screener
results = []
with st.spinner("📈 Kjører screener…"):
    for t in [t.strip() for t in tickers if t.strip()]:
        res = screen_ticker(t, min_vol, min_swings, min_return_pct)
        if res and res["success_rate"] >= min_success:
            results.append(res)

# Vis funn
if results:
    st.subheader(f"✅ Resultater ({len(results)} aksje(r) funnet)")
    df_res = pd.DataFrame([{"Ticker": r["ticker"],
                            "Swings": r["swings"],
                            "Success %": round(r["success_rate"],1)}
                           for r in results])
    selected = st.selectbox("Velg aksje for graf:", df_res["Ticker"])
    st.table(df_res)

    # Vis graf for valgt ticker
    sel = next(r for r in results if r["ticker"] == selected)
    df = sel["df"]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Close"))
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume",
                         opacity=0.3, yaxis="y2"))
    fig.update_layout(
        title=f"{selected} – 5 år med volum",
        yaxis2=dict(overlaying="y", side="right", title="Volum"),
        height=600
    )
    st.plotly_chart(fig, use_container_width=True)

else:
    st.info("ℹ️ Ingen aksjer matchet kriteriene.")

