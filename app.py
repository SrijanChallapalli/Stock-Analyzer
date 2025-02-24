from flask import Flask, render_template, request, jsonify
import numpy as np
import pandas as pd
import yfinance as yf
import matplotlib.pyplot as plt
import io
import base64
import random
import requests
from bs4 import BeautifulSoup
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# Ensure Flask Serves Static Files Properly
app = Flask(__name__, static_folder="static")

# Global variable to store CNBC articles
articles = []

def fetch_articles():
    global articles
    url = "https://www.cnbc.com/"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')

    # Extract article titles and links
    articles = []
    for item in soup.select('a.Card-title'):
        title = item.get_text(strip=True)
        link = item['href']
        if not link.startswith('http'):
            link = f"https://www.cnbc.com{link}"
        articles.append({"title": title, "link": link})

    print("Fetched new articles from CNBC")

# Schedule the fetch_articles function to run every hour
scheduler = BackgroundScheduler()
scheduler.add_job(func=fetch_articles, trigger="interval", hours=1)
scheduler.start()

# Shut down the scheduler when the app exits
atexit.register(lambda: scheduler.shutdown())

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

        rs = avg_gain / avg_loss.replace(0, 1)  # Avoid division by zero
        self.data['RSI'] = 100 - (100 / (1 + rs))

    def calculate_bollinger_bands(self):
        ma = self.data['Close'].rolling(window=20).mean()
        std = self.data['Close'].rolling(window=20).std()
        self.data['Upper Band'] = ma + (2 * std)
        self.data['Lower Band'] = ma - (2 * std)

    def generate_recommendation(self):
        # Get the latest RSI and Bollinger Bands values
        latest_rsi = self.data['RSI'].iloc[-1]
        latest_close = self.data['Close'].iloc[-1]
        upper_band = self.data['Upper Band'].iloc[-1]
        lower_band = self.data['Lower Band'].iloc[-1]

        # Recommendation logic
        if latest_rsi < 30 and latest_close < lower_band:
            return "Buy"  # Oversold and below lower Bollinger Band
        elif latest_rsi > 70 and latest_close > upper_band:
            return "Sell"  # Overbought and above upper Bollinger Band
        else:
            return "Hold"  # Neutral conditions

    def generate_ai_analysis(self):
        analysis_templates = [
            f"{self.ticker} has been experiencing volatility in the past few months. The stock’s moving averages suggest a potential shift in momentum. If the market continues its current trend, this stock could either stabilize or face further fluctuations. Investors should consider macroeconomic factors and sector trends before making any decisions.",
            f"Technical indicators for {self.ticker} show interesting movement. The RSI suggests that the stock might be overbought, while the Bollinger Bands indicate increased volatility. This could be a sign of upcoming price corrections. Investors looking for stability might want to wait before entering a position.",
            f"The performance of {self.ticker} suggests mixed signals. While the moving averages indicate strength, external market conditions might play a critical role in determining the next trend. Analysts often recommend monitoring earnings reports and upcoming news to make informed decisions.",
            f"{self.ticker} has been consolidating within a defined range. If a breakout occurs, it could present an opportunity for short-term traders. Long-term investors, however, might want to wait for more stability before making a move."
        ]
        return random.choice(analysis_templates) + " This is not financial advice."

    def get_analyst_recommendations(self):
        # Mock data for analyst recommendations
        analyst_data = {
            "AAPL": {"buy": 65, "hold": 25, "sell": 10},
            "GOOGL": {"buy": 70, "hold": 20, "sell": 10},
            "TSLA": {"buy": 40, "hold": 40, "sell": 20},
            "AMZN": {"buy": 60, "hold": 30, "sell": 10},
            "MSFT": {"buy": 75, "hold": 20, "sell": 5},
        }
        # Default values if ticker not found
        return analyst_data.get(self.ticker, {"buy": 50, "hold": 30, "sell": 20})

    def generate_chart(self):
        plt.figure(figsize=(10, 5))
        plt.plot(self.data.index, self.data['Close'], label="Stock Price", color='blue')
        plt.plot(self.data['Moving Average (10)'], label="10-Day MA", color='orange')
        plt.fill_between(self.data.index, self.data['Upper Band'], self.data['Lower Band'], color='gray', alpha=0.3)
        plt.legend()
        plt.xlabel("Date")
        plt.ylabel("Price (USD)")
        plt.title(f"{self.ticker} Stock Price Analysis")

        img = io.BytesIO()
        plt.savefig(img, format='png')
        img.seek(0)
        chart_url = base64.b64encode(img.getvalue()).decode()
        plt.close()
        return f"data:image/png;base64,{chart_url}"

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

    def safe_value(value):
        return round(value, 2) if not np.isnan(value) else "N/A"

    latest_price = safe_value(analyzer.data['Close'].iloc[-1])
    rsi = safe_value(analyzer.data['RSI'].iloc[-1])
    upper_band = safe_value(analyzer.data['Upper Band'].iloc[-1])
    lower_band = safe_value(analyzer.data['Lower Band'].iloc[-1])

    recommendation = analyzer.generate_recommendation()
    chart_url = analyzer.generate_chart()
    ai_analysis = analyzer.generate_ai_analysis()
    analyst_recommendations = analyzer.get_analyst_recommendations()

    return jsonify({
        "ticker": ticker,
        "latest_price": latest_price,
        "rsi": rsi,
        "upper_band": upper_band,
        "lower_band": lower_band,
        "recommendation": recommendation,
        "chart_url": chart_url,
        "ai_analysis": ai_analysis,
        "analyst_recommendations": analyst_recommendations
    })

@app.route('/about')
def about():
    return render_template('about.html')

if __name__ == '__main__':
    fetch_articles()  # Fetch articles on startup
    app.run(debug=True)
