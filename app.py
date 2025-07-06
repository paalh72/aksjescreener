import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime, timedelta

st.set_page_config(page_title="Aksjescreener", layout="wide")

@st.cache_data(ttl=86400)
def hent_tickers(url):
    df = pd.read_csv(url)
    return df['Symbol'].tolist()

def calculate_rsi(data, window=14):
    delta = data['Close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=window, min_periods=window).mean()
    avg_loss = loss.rolling(window=window, min_periods=window).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def analyze_ticker(ticker, start_date, end_date, min_volume, rsi_low=20, rsi_high=70, min_rsi_cycles=10, min_price_increase_pct=10, min_hit_ratio=0.5):
    try:
        data = yf.download(ticker, start=start_date, end=end_date, progress=False)
        if data.empty:
            return None
        
        # Sjekk volum
        avg_volume = data['Volume'].mean()
        if avg_volume < min_volume:
            return None
        
        data['RSI'] = calculate_rsi(data)
        data = data.dropna(subset=['RSI'])
        if data.empty:
            return None
        
        # Finn RSI sykluser mellom rsi_low og rsi_high
        cycles = []
        state = None  # None, "below_low", "above_high"
        last_low_index = None
        last_high_index = None
        
        for i, rsi in enumerate(data['RSI']):
            if state is None:
                if rsi <= rsi_low:
                    state = "below_low"
                    last_low_index = i
            elif state == "below_low":
                if rsi >= rsi_high:
                    state = "above_high"
                    last_high_index = i
            elif state == "above_high":
                if rsi <= rsi_low:
                    # Full cycle complete: RSI went low->high->low
                    cycles.append((last_low_index, last_high_index))
                    state = "below_low"
                    last_low_index = i
        
        # Vi kan ha en siste halvsyklus, ignorer den
        
        if len(cycles) < min_rsi_cycles:
            return None
        
        # Evaluer prisøkning mellom RSI 20 (low) og RSI 70 (high)
        hits = 0
        for low_i, high_i in cycles:
            price_low = data['Close'].iloc[low_i]
            price_high = data['Close'].iloc[high_i]
            if price_high >= price_low * (1 + min_price_increase_pct / 100):
                hits += 1
        
        hit_ratio = hits / len(cycles)
        if hit_ratio < min_hit_ratio:
            return None
        
        return {
            "Ticker": ticker,
            "AvgVolume": avg_volume,
            "RSICycles": len(cycles),
            "Hits": hits,
            "HitRatio": hit_ratio,
            "CloseLatest": data['Close'].iloc[-1],
            "Data": data
        }
    except Exception as e:
        st.error(f"Feil i {ticker}: {e}")
        return None

# URLer til dine CSV filer på GitHub (raw)
url_oslo = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/oslo_bors_tickers.csv"
url_nyse = "https://raw.githubusercontent.com/paalh72/aksjescreener/main/nyse_tickers.csv"

st.title("Aksjescreener for Oslo Børs og NYSE")

min_volume = st.number_input("Minimum gjennomsnittlig volum per dag", min_value=1000, value=100000, step=1000)
min_price_increase = st.slider("Minimum % prisøkning mellom RSI 20 og RSI 70", min_value=1, max_value=50, value=10)
min_rsi_cycles = st.number_input("Minimum antall RSI 20-70 sykluser (minimum)", min_value=1, value=10)
min_hit_ratio = st.slider("Minimum andel av sykluser hvor prisøkning må oppfylles (f.eks 50%)", min_value=0.0, max_value=1.0, value=0.5, step=0.05)

with st.spinner("Henter tickers..."):
    tickers_oslo = hent_tickers(url_oslo)
    tickers_nyse = hent_tickers(url_nyse)

tickers = tickers_oslo + tickers_nyse

st.write(f"Totalt {len(tickers)} tickers hentet fra Oslo Børs og NYSE.")

start_date = datetime.now() - timedelta(days=365*5)
end_date = datetime.now()

results = []
progress_bar = st.progress(0)

for i, ticker in enumerate(tickers):
    result = analyze_ticker(ticker, start_date, end_date, min_volume, min_rsi_cycles=min_rsi_cycles, min_price_increase_pct=min_price_increase, min_hit_ratio=min_hit_ratio)
    if result:
        results.append(result)
    progress_bar.progress((i+1)/len(tickers))

if results:
    df_results = pd.DataFrame(results)
    df_results = df_results.sort_values(by="HitRatio", ascending=False)
    st.write(f"Aksjer som matcher kriteriene ({len(df_results)}):")
    st.dataframe(df_results[['Ticker', 'AvgVolume', 'RSICycles', 'Hits', 'HitRatio', 'CloseLatest']])
    
    selected_ticker = st.selectbox("Velg aksje for detaljert visning:", df_results['Ticker'])
    selected_data = next(r['Data'] for r in results if r['Ticker'] == selected_ticker)
    
    st.line_chart(selected_data[['Close', 'Volume']])
else:
    st.write("Ingen aksjer matchet kriteriene med dagens innstillinger.")
