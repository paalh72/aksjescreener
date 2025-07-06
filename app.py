import streamlit as st
import pandas as pd
import yfinance as yf
import datetime

# Konfigurasjon
st.set_page_config(page_title="Aksjescreener", layout="wide")
st.title("📈 Aksjescreener med RSI og prisendring")

# Parametere
rsi_low = 30
rsi_high = 70
start_date = datetime.date.today() - datetime.timedelta(days=365 * 5)

# Hent tickere fra lokal CSV
try:
    tickers = pd.read_csv("tickers.csv", header=None)[0].str.strip().tolist()
except FileNotFoundError:
    st.error("Fant ikke 'tickers.csv'. Legg den i samme mappe som app.py.")
    st.stop()

# Funksjon: RSI
def compute_rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# Screeningresultater
results = []

progress = st.progress(0)
for i, ticker in enumerate(tickers):
    try:
        data = yf.download(ticker, start=start_date, progress=False)
        if data.empty or len(data) < 20:
            continue

        data['RSI'] = compute_rsi(data['Close'])
        latest = data.iloc[-1]
        close = latest['Close']
        rsi = latest['RSI']

        # Enkel screening: RSI og positiv 3-dagers endring
        recent_change = data['Close'].iloc[-1] - data['Close'].iloc[-4]
        passed = rsi < rsi_low or rsi > rsi_high or recent_change > 0

        if pd.notna(rsi) and passed:
            results.append({
                "Ticker": ticker,
                "Kurs": round(close, 2),
                "RSI": round(rsi, 2),
                "Endring (3d)": round(recent_change, 2),
            })

    except Exception as e:
        st.warning(f"Feil i {ticker}: {e}")
    progress.progress((i + 1) / len(tickers))

# Vis resultater
if results:
    st.subheader("🎯 Aksjer som matcher kriterier")
    df = pd.DataFrame(results)
    st.dataframe(df.sort_values(by="RSI"), use_container_width=True)

    # Velg en aksje for å vise graf
    selected = st.selectbox("Velg en aksje for å vise RSI og kursgraf", df["Ticker"])
    chart_data = yf.download(selected, start=start_date, progress=False)
    chart_data['RSI'] = compute_rsi(chart_data['Close'])

    chart_df = chart_data[['Close', 'RSI']].dropna()
    chart_df.reset_index(inplace=True)
    st.line_chart(chart_df.set_index('Date'))
else:
    st.info("Ingen aksjer matchet screeningkriteriene.")
