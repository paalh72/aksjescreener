import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go
import datetime

# RSI-funksjon
def compute_rsi(series, window=14):
    delta = series.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(window).mean()
    avg_loss = loss.rolling(window).mean()
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

# Screener-funksjon
def screen_ticker(ticker, min_vol, min_swings, min_return_pct):
    df = yf.download(ticker, period="5y", interval="1d", auto_adjust=True)
    if df.empty or df['Volume'].mean() < min_vol:
        return None
    df['RSI'] = compute_rsi(df['Close'])
    swings = []
    last_rsi20_date = None
    for i in range(1, len(df)):
        prev, curr = df['RSI'].iloc[i-1], df['RSI'].iloc[i]
        if prev < 20 and curr >= 20:
            last_rsi20_date = df.index[i]
        if prev < 70 and curr >= 70 and last_rsi20_date is not None:
            close_20 = df['Close'].loc[last_rsi20_date]
            close_70 = df['Close'].iloc[i]
            pct = (close_70 / close_20 - 1) * 100
            swings.append(pct)
            last_rsi20_date = None
    if len(swings) < min_swings:
        return None
    success_rate = sum(p >= min_return_pct for p in swings) / len(swings) * 100
    return {"ticker": ticker, "swings": len(swings), "success_rate": success_rate, "df": df}

# UI
st.title("📊 Aksjescreener – RSI 20/70-basert")
stocks = st.text_area("Oppgi tickere separert med komma", 
                      value="AAPL,MSFT,TSLA,EQNR.OL,DNB.OL,ERIC-B.ST").split(",")
min_vol = st.number_input("Min. gj.snittlig volum", value=100000, step=10000)
min_swings = st.number_input("Min. antall RSI-sving", value=10, step=1)
min_return_pct = st.number_input("Min. kursøkning (%) fra RSI20 til RSI70", value=10)
min_success_rate = st.slider("Min. andel ganger over min %", 0, 100, 50)

results = []
for t in [s.strip().upper() for s in stocks if s.strip()]:
    res = screen_ticker(t, min_vol, min_swings, min_return_pct)
    if res and res["success_rate"] >= min_success_rate:
        results.append(res)

if results:
    st.subheader("📈 Screener-resultater")
    for r in results:
        st.write(f"**{r['ticker']}** – Svingninger: {r['swings']}, Andel ≥{min_return_pct}%: {r['success_rate']:.1f}%")
    selected = st.selectbox("Vis kursgraf for:", [r['ticker'] for r in results])
    sel = next(r for r in results if r['ticker']==selected)
    df = sel['df']
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['Close'], name="Close"))
    fig.add_trace(go.Bar(x=df.index, y=df['Volume'], name="Volume", opacity=0.3, yaxis="y2"))
    fig.update_layout(title=f"{selected} – 5 år", yaxis2=dict(overlaying="y", side="right", title="Volum"))
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("Ingen aksjer matchet kriteriene.")

