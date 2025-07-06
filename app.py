import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# RSI-funksjon
def compute_rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

st.title("📈 Aksjescreener med RSI og Volum")

# Brukerinput
exchange = st.selectbox("Velg børs:", ["NYSE", "Nasdaq Stockholm", "Oslo Børs"])
ticker_input = st.text_input("🎯 Test ticker manuelt", "AAPL")

if st.button("Test ticker"):
    try:
        df = yf.download(ticker_input, period="5y", interval="1d", auto_adjust=True)

        if df.empty:
            st.error("Ingen data funnet for denne tickeren.")
        else:
            df['RSI'] = compute_rsi(df['Close'])
            chart_df = df[['Close', 'RSI']].dropna().copy()

            # Flatten MultiIndex hvis nødvendig
            if isinstance(chart_df.columns, pd.MultiIndex):
                chart_df.columns = ['_'.join(col).strip() for col in chart_df.columns.values]

            # Reset index og plott
            chart_df_reset = chart_df.reset_index()
            st.line_chart(chart_df_reset.set_index('Date'))

            # Vis data
            st.dataframe(chart_df_reset.tail(30))

    except Exception as e:
        st.error(f"Feil ved henting eller behandling av data: {e}")

st.markdown("---")
st.info("Flere screening-funksjoner og tekniske indikatorer kommer snart.")
