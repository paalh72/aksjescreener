import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import datetime
import altair as alt

# --- RSI calculation ---
def compute_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

# --- Screening function ---
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
            if pd.isna(prev_rsi) or pd.isna(curr_rsi):
                continue

            if prev_rsi < 20 and curr_rsi >= 20:
                last_rsi20_date = df.index[i]

            elif prev_rsi < 70 and curr_rsi >= 70 and last_rsi20_date:
                if last_rsi20_date in df.index:
                    start_price = df.loc[last_rsi20_date, 'Close']
                    end_price = df['Close'].iloc[i]
                    return_pct = (end_price - start_price) / start_price * 100

                    if return_pct >= min_return_pct:
                        swings.append((last_rsi20_date, df.index[i], return_pct))
                last_rsi20_date = None

        if len(swings) >= min_swings:
            success_rate = len(swings) / (len(df) / 252)  # swings per year
            return {
                "ticker": ticker,
                "swings": swings,
                "success_rate": success_rate,
                "avg_return": np.mean([s[2] for s in swings]) if swings else 0
            }
        return None

    except Exception as e:
        st.warning(f"Feil i {ticker}: {e}")
        return None

# --- Layout ---
st.title("📈 Aksjescreener med RSI og volum")
st.markdown("Denne screeneren finner aksjer som har beveget seg fra RSI 20 til RSI 70 og målt avkastning på slike bevegelser.")

exchange = st.selectbox("Velg børs:", ["NYSE", "Nasdaq", "Oslo Børs"])
min_vol = st.number_input("Minimum gjennomsnittlig volum", value=500_000)
min_swings = st.number_input("Minimum antall RSI 20-70 bevegelser (5 år)", value=3)
min_return_pct = st.number_input("Minimum avkastning mellom RSI 20-70 (%)", value=10)

run = st.button("🔍 Kjør screening")

if run:
    with st.spinner("Henter og analyserer data..."):
        if exchange == "NYSE":
            tickers = pd.read_csv("https://raw.githubusercontent.com/datasets/s-and-p-500-companies/master/data/constituents_symbols.txt", header=None)[0].tolist()
        elif exchange == "Nasdaq":
            tickers = pd.read_csv("https://raw.githubusercontent.com/owid/owid-datasets/master/datasets/Nasdaq%20Symbols/Nasdaq%20Symbols.csv")['Symbol'].dropna().unique().tolist()
        else:  # Oslo Børs (hardkodet eksempler)
            tickers = ['EQNR.OL', 'YAR.OL', 'NHY.OL', 'DNB.OL', 'TEL.OL']

        results = []
        for ticker in tickers[:50]:  # Begrens for ytelse
            res = screen_ticker(ticker, min_vol, min_swings, min_return_pct)
            if res:
                results.append(res)

    if results:
        df_results = pd.DataFrame(results)
        df_results = df_results.sort_values(by='success_rate', ascending=False)

        st.subheader("🎯 Resultater")
        st.dataframe(df_results[['ticker', 'success_rate', 'avg_return']])

        selected_ticker = st.selectbox("Velg en aksje for detaljer", df_results['ticker'])

        selected_data = screen_ticker(selected_ticker, min_vol, min_swings, min_return_pct)
        if selected_data:
            df_chart = yf.download(selected_ticker, period="1y", interval="1d", auto_adjust=True, progress=False)
            df_chart['RSI'] = compute_rsi(df_chart['Close'])
            df_chart = df_chart.dropna()
            df_chart = df_chart.reset_index()

            chart_data = df_chart[['Date', 'Close', 'RSI']].melt(id_vars='Date', var_name='Type', value_name='Value')
            chart = alt.Chart(chart_data).mark_line().encode(
                x='Date:T',
                y='Value:Q',
                color='Type:N'
            ).properties(title=f"{selected_ticker} - RSI og pris siste 12 mnd", width=700)
            st.altair_chart(chart, use_container_width=True)

            st.write(f"**Antall swings:** {len(selected_data['swings'])}")
            st.write(f"**Gj.snittlig avkastning:** {selected_data['avg_return']:.2f}%")
            st.write(f"**Swings funnet:**")
            swing_df = pd.DataFrame(selected_data['swings'], columns=['Start', 'Slutt', 'Avkastning (%)'])
            st.dataframe(swing_df)
    else:
        st.info("Ingen aksjer oppfyller kriteriene.")

