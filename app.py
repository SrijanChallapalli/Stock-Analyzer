from flask import Flask, render_template, request
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objs as go

app = Flask(__name__)

# Helper function to get stock data
def get_stock_data(ticker):
    stock = yf.Ticker(ticker)
    data = stock.history(period="1y")  # You can adjust the period as needed
    return data

# Calculate technical indicators
def calculate_indicators(data):
    # MACD
    exp12 = data['Close'].ewm(span=12, adjust=False).mean()
    exp26 = data['Close'].ewm(span=26, adjust=False).mean()
    data['MACD'] = exp12 - exp26
    data['Signal_Line'] = data['MACD'].ewm(span=9, adjust=False).mean()

    # RSI
    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    data['RSI'] = 100 - (100 / (1 + rs))

    # Bollinger Bands
    data['BB_Middle'] = data['Close'].rolling(window=20).mean()
    data['BB_Upper'] = data['BB_Middle'] + 2 * data['Close'].rolling(window=20).std()
    data['BB_Lower'] = data['BB_Middle'] - 2 * data['Close'].rolling(window=20).std()

    # SMA and EMA
    data['SMA'] = data['Close'].rolling(window=20).mean()
    data['EMA'] = data['Close'].ewm(span=20, adjust=False).mean()

    return data

# Get fundamental data (Example: P/E ratio, etc.)
def get_fundamentals(ticker):
    stock = yf.Ticker(ticker)
    info = stock.info
    fundamentals = {
        'PE_Ratio': info.get('trailingPE'),
        'PB_Ratio': info.get('priceToBook'),
        'ROE': info.get('returnOnEquity'),
        'ROA': info.get('returnOnAssets'),
        'Debt_to_Equity': info.get('debtToEquity'),
        'Dividend_Yield': info.get('dividendYield'),
        'Free_Cash_Flow': info.get('freeCashflow'),
    }
    return fundamentals

# Home route
@app.route('/')
def index():
    return render_template('index.html')

# Stock Analysis route
@app.route('/analyze', methods=['POST'])
def analyze():
    ticker = request.form['ticker']
    data = get_stock_data(ticker)
    data_with_indicators = calculate_indicators(data)
    fundamentals = get_fundamentals(ticker)

    # Create chart for visualization (e.g., candlestick chart with indicators)
    trace = go.Candlestick(
        x=data.index,
        open=data['Open'],
        high=data['High'],
        low=data['Low'],
        close=data['Close'],
        name='Candlesticks'
    )
    trace_macd = go.Scatter(x=data.index, y=data['MACD'], mode='lines', name='MACD')
    trace_signal = go.Scatter(x=data.index, y=data['Signal_Line'], mode='lines', name='Signal Line')

    layout = go.Layout(
        title=f"{ticker} Stock Analysis",
        xaxis={'rangeslider': {'visible': False}},
        yaxis={'title': 'Price'},
    )

    fig = go.Figure(data=[trace, trace_macd, trace_signal], layout=layout)

    # Render the result page with the chart and fundamental data
    return render_template('analyze.html', 
                           ticker=ticker, 
                           chart=fig.to_html(full_html=False),
                           fundamentals=fundamentals, 
                           data_with_indicators=data_with_indicators.tail(10))

if __name__ == '__main__':
    app.run(debug=True)
