import streamlit as st
import yfinance as yf
import pandas as pd
import datetime

# --- Funksjoner ---
def fetch_data(ticker, start_date):
    df = yf.download(ticker, start=start_date)
    df['RSI'] = compute_rsi(df['Close'])
    return df

def compute_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def screen_ticker(ticker, min_return_pct):
    df = fetch_data(ticker, '2018-01-01')
    swings = []
    last_rsi20_date = None

    for i in range(1, len(df)):
        prev_rsi = df['RSI'].iloc[i - 1]
        curr_rsi = df['RSI'].iloc[i]

        if prev_rsi < 20 and curr_rsi >= 20:
            last_rsi20_date = df.index[i]

        if prev_rsi < 70 and curr_rsi >= 70 and last_rsi20_date:
            start_price = df.loc[last_rsi20_date, 'Close'] if last_rsi20_date in df.index else None
            end_price = df['Close'].iloc[i]
            if start_price:
                return_pct = (end_price - start_price) / start_price * 100
                if return_pct >= min_return_pct:
                    swings.append((last_rsi20_date, df.index[i], return_pct))
            last_rsi20_date = None

    df['Swings'] = swings
    return df, swings

# --- Streamlit UI ---
st.title("Aksje Screener")

tickers = st.text_input("Skriv inn tickere separert med komma (f.eks. AAPL, MSFT, EQNR.OL)", "AAPL, MSFT")
min_return = st.number_input("Minimum avkastning mellom RSI 20 til RSI 70 (%)", value=10)

if st.button("Kjør screening"):
    ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
    for ticker in ticker_list:
        try:
            st.subheader(f"Resultater for {ticker}")
            df, swings = screen_ticker(ticker, min_return)

            if swings:
                st.success(f"Fant {len(swings)} gyldige svingninger")
                st.write("Eksempel-data:", df[['Close', 'RSI']].dropna().tail(10))

                chart_df = df[['Close', 'RSI']].dropna()
                chart_df.index.name = 'Date'
                chart_df.reset_index(inplace=True)
                st.line_chart(chart_df.set_index('Date'))
            else:
                st.warning("Ingen treff som matchet kriteriene.")

        except Exception as e:
            st.error(f"Feil i {ticker}: {str(e)}")
