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

# Parametre for screening
rsi_low = st.sidebar.slider("RSI lav terskel", 0, 100, 20)
rsi_high = st.sidebar.slider("RSI høy terskel", 0, 100, 70)
start_date = (datetime.now() - timedelta(days=365*2)).strftime("%Y-%m-%d")

# Hent tickers - fallback liste hvis nett er nede
default_tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "TSLA"]

try:
    tickers = pd.read_csv(
        "https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents_symbols.txt",
        header=None,
    )[0].tolist()
except Exception:
    st.warning("Kunne ikke hente tickers fra nettet, bruker default-liste.")
    tickers = default_tickers

st.write(f"Henter data for {len(tickers)} tickere...")

progress = st.progress(0)
results = []

for i, ticker in enumerate(tickers):
    try:
        data = yf.download(ticker, start=start_date, progress=False)
        if data.empty or len(data) < 20:
            continue

        data['RSI'] = compute_rsi(data['Close'])

        # Sjekk at RSI finnes og ikke er NaN på siste rad
        latest = data.iloc[-1]
        rsi = latest['RSI']

        # Forsikre at rsi er et enkelt tall, ikke Serie
        if isinstance(rsi, pd.Series):
            rsi = rsi.iloc[0]

        # 3-dagers endring i sluttkurs
        recent_change = data['Close'].iloc[-1] - data['Close'].iloc[-4]

        # Screening: RSI lav eller høy, eller positiv 3-dagers endring
        passed = (rsi < rsi_low) or (rsi > rsi_high) or (recent_change > 0)

        if pd.notna(rsi) and passed:
            results.append({
                "Ticker": ticker,
                "Kurs": round(latest['Close'], 2),
                "RSI": round(rsi, 2),
                "Endring (3d)": round(recent_change, 2),
            })

    except Exception as e:
        st.warning(f"Feil i {ticker}: {e}")

    progress.progress((i + 1) / len(tickers))

# Vis resultater
if results:
    df_results = pd.DataFrame(results)
    st.subheader("Screenede aksjer")
    st.dataframe(df_results)

    # Velg ticker for graf
    selected_ticker = st.selectbox("Velg ticker for graf", df_results["Ticker"].tolist())

    if selected_ticker:
        df = yf.download(selected_ticker, start=start_date, progress=False)
        df['RSI'] = compute_rsi(df['Close'])

        # Graf med pris og RSI
        st.subheader(f"Graf for {selected_ticker}")

        # Plot pris og RSI på to y-akser
        import altair as alt

        base = alt.Chart(df.reset_index()).encode(x='Date:T')

        price_line = base.mark_line(color='blue').encode(
            y=alt.Y('Close:Q', axis=alt.Axis(title='Pris (Close)'))
        )

        rsi_line = base.mark_line(color='orange').encode(
            y=alt.Y('RSI:Q', axis=alt.Axis(title='RSI'))
        )

        # Lag dobbel y-akse med layered chart
        chart = alt.layer(price_line, rsi_line).resolve_scale(
            y='independent'
        ).properties(
            width=800,
            height=400
        )

        st.altair_chart(chart, use_container_width=True)
else:
    st.write("Ingen aksjer passerte screening-kriteriene.")

