from flask import Flask, render_template, request, jsonify
import numpy as np
import pandas as pd
import yfinance as yf
import random
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
import atexit
import plotly.graph_objs as go

app = Flask(__name__, static_folder="static")

# Global variable to store CNBC articles
articles = []

def fetch_articles():
    global articles
    url = "https://www.cnbc.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []
    for item in soup.select('a.Card-title'):
        title = item.get_text(strip=True)
        link = item['href']
        if not link.startswith('http'):
            link = f"https://www.cnbc.com{link}"
        articles.append({"title": title, "link": link})
    print("Fetched new articles from CNBC")

# Schedule fetch_articles to run every hour
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_articles, trigger="interval", hours=1)
scheduler.start()
atexit.register(lambda: scheduler.shutdown())

def safe_value(value):
    """
    Convert numeric value to rounded value.
    If value is NaN or an error occurs, return "N/A".
    """
    try:
        if pd.isna(value):
            return "N/A"
        return round(value, 2)
    except Exception:
        return "N/A"

class StockAnalyzer:
    def __init__(self, ticker, period):
        self.ticker = ticker
        self.period = period
        self.data = None

    def fetch_data(self):
        stock = yf.Ticker(self.ticker)
        self.data = stock.history(period=self.period)
        if self.data.empty:
            return False  # No data found, invalid ticker
        self.data['Moving Average (10)'] = self.data['Close'].rolling(window=10).mean()
        self.data['Daily Return'] = self.data['Close'].pct_change()
        return True

    def calculate_rsi(self, period=14):
        delta = self.data['Close'].diff()
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).rolling(window=period, min_periods=1).mean()
        avg_loss = pd.Series(loss).rolling(window=period, min_periods=1).mean()
        # Avoid division by zero by replacing 0 with a very small number
        avg_loss = avg_loss.replace(0, 1e-10)
        rs = avg_gain / avg_loss
        self.data['RSI'] = 100 - (100 / (1 + rs))

    def calculate_bollinger_bands(self):
        ma = self.data['Close'].rolling(window=20).mean()
        std = self.data['Close'].rolling(window=20).std()
        self.data['Upper Band'] = ma + (2 * std)
        self.data['Lower Band'] = ma - (2 * std)

    def get_fundamentals(self):
        stock = yf.Ticker(self.ticker)
        info = stock.info
        fundamentals = {
            'PE_Ratio': info.get('trailingPE'),
            'PB_Ratio': info.get('priceToBook'),
            'ROE': info.get('returnOnEquity'),
            'ROA': info.get('returnOnAssets'),
            'Debt_to_Equity': info.get('debtToEquity'),
            'Dividend_Yield': info.get('dividendYield'),
            'Free_Cash_Flow': info.get('freeCashflow'),
            'Revenue_Growth': info.get('revenueGrowth'),
            'Profit_Margin': info.get('profitMargins')
        }
        return fundamentals

    def generate_recommendation(self):
        latest_rsi = self.data['RSI'].iloc[-1]
        latest_close = self.data['Close'].iloc[-1]
        upper_band = self.data['Upper Band'].iloc[-1]
        lower_band = self.data['Lower Band'].iloc[-1]
        if latest_rsi < 30 and latest_close < lower_band:
            return "Buy"
        elif latest_rsi > 70 and latest_close > upper_band:
            return "Sell"
        else:
            return "Hold"

    def generate_analysis(self):
        analysis_templates = [
            f"{self.ticker} has been experiencing volatility. Its moving averages suggest a potential shift in momentum. Consider market conditions and sector trends before making decisions.",
            f"Technical indicators for {self.ticker} show mixed signals. The RSI suggests possible overbought conditions while Bollinger Bands indicate volatility. Caution is advised.",
            f"{self.ticker} shows signs of consolidation. A breakout could be imminent, but further analysis is recommended before taking action.",
            f"Observations for {self.ticker} indicate a balanced market sentiment with potential for both upward and downward movements. Monitor earnings and news for further insights."
        ]
        return random.choice(analysis_templates) + " This is not financial advice."

    def get_analyst_recommendations(self):
        analyst_data = {
            "AAPL": {"buy": 65, "hold": 25, "sell": 10},
            "GOOGL": {"buy": 70, "hold": 20, "sell": 10},
            "TSLA": {"buy": 40, "hold": 40, "sell": 20},
            "AMZN": {"buy": 60, "hold": 30, "sell": 10},
            "MSFT": {"buy": 75, "hold": 20, "sell": 5},
        }
        return analyst_data.get(self.ticker, {"buy": 50, "hold": 30, "sell": 20})

    def generate_chart(self):
        # Calculate MACD and Signal Line
        exp12 = self.data['Close'].ewm(span=12, adjust=False).mean()
        exp26 = self.data['Close'].ewm(span=26, adjust=False).mean()
        self.data['MACD'] = exp12 - exp26
        self.data['Signal_Line'] = self.data['MACD'].ewm(span=9, adjust=False).mean()
        # Build the candlestick chart with Plotly
        candlestick = go.Candlestick(
            x=self.data.index,
            open=self.data['Open'],
            high=self.data['High'],
            low=self.data['Low'],
            close=self.data['Close'],
            name='Price'
        )
        macd_line = go.Scatter(
            x=self.data.index,
            y=self.data['MACD'],
            mode='lines',
            name='MACD'
        )
        signal_line = go.Scatter(
            x=self.data.index,
            y=self.data['Signal_Line'],
            mode='lines',
            name='Signal Line'
        )
        rsi_line = go.Scatter(
            x=self.data.index,
            y=self.data['RSI'],
            mode='lines',
            name='RSI',
            yaxis="y2"
        )
        layout = go.Layout(
            title=f"{self.ticker} Stock Analysis",
            xaxis=dict(title="Date"),
            yaxis=dict(title="Price (USD)"),
            yaxis2=dict(title="RSI", overlaying="y", side="right", range=[0, 100]),
            legend=dict(x=0, y=1.2),
            margin=dict(l=40, r=40, t=40, b=40)
        )
        fig = go.Figure(data=[candlestick, macd_line, signal_line, rsi_line], layout=layout)
        return fig.to_html(full_html=False)

@app.route('/')
def home():
    return render_template('index.html', articles=articles)

@app.route('/analyze', methods=['POST'])
def analyze():
    ticker = request.form['ticker'].upper()
    period = request.form['period']
    analyzer = StockAnalyzer(ticker, period)
    if not analyzer.fetch_data():
        return jsonify({"error": "Invalid ticker or no data found."})
    
    analyzer.calculate_rsi()
    analyzer.calculate_bollinger_bands()
    fundamentals = analyzer.get_fundamentals()
    # Convert all fundamentals values using safe_value
    for key, value in fundamentals.items():
        fundamentals[key] = safe_value(value)
    
    recommendation = analyzer.generate_recommendation()
    analysis_text = analyzer.generate_analysis()  # Headline now "Analysis"
    chart_url = analyzer.generate_chart()
    
    latest_price = safe_value(analyzer.data['Close'].iloc[-1])
    rsi = safe_value(analyzer.data['RSI'].iloc[-1])
    upper_band = safe_value(analyzer.data['Upper Band'].iloc[-1])
    lower_band = safe_value(analyzer.data['Lower Band'].iloc[-1])
    
    return jsonify({
        "ticker": ticker,
        "latest_price": latest_price,
        "rsi": rsi,
        "upper_band": upper_band,
        "lower_band": lower_band,
        "recommendation": recommendation,
        "chart_url": chart_url,
        "analysis": analysis_text,
        "fundamentals": fundamentals,
        "analyst_recommendations": analyzer.get_analyst_recommendations()
    })

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/account')
def account():
    return render_template('account.html')

@app.route('/info')
def info():
    return render_template('info.html')

if __name__ == '__main__':
    fetch_articles()  # Fetch articles on startup
    app.run(debug=True)
