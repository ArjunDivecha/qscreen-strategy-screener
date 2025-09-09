# 📊 Quantpedia Strategy Screener

> **Discover, analyze, and understand 1000+ quantitative investment strategies with AI-powered insights**

## 🚀 Live Demo
**[Try it now →](https://your-railway-url.railway.app)** *(Deployed on Railway)*

## ✨ What This App Does

The Quantpedia Strategy Screener transforms how you explore quantitative investment strategies. Instead of manually browsing through hundreds of complex academic papers, this tool provides:

### 🔍 **Smart Strategy Discovery**
- **Browse 1000+ strategies** from momentum to mean reversion, crypto to commodities
- **Filter by performance** (Sharpe ratio, max drawdown, returns)
- **Search by asset class** (stocks, bonds, forex, crypto, options, futures)
- **Find by trading style** (momentum, reversal, arbitrage, carry trades)

### 🤖 **AI-Powered Analysis** 
- **Instant summaries** of complex strategies using advanced AI models
- **Plain English explanations** of academic research
- **Dual AI perspectives** for comprehensive understanding
- **No more reading 50-page papers** - get the key insights in seconds

### 📈 **Performance Intelligence**
- **Sort by Sharpe ratio** to find risk-adjusted winners
- **Filter by drawdown** to match your risk tolerance  
- **Analyze by time period** to see recent vs historical performance
- **Compare strategies** side-by-side

### 🏷️ **Smart Categorization**
- **1000+ keywords** automatically extracted and categorized
- **Trading Style**: momentum, reversal, trend-following, mean reversion
- **Asset Classes**: equities, fixed income, currencies, commodities, crypto
- **Factors**: value, size, quality, volatility, profitability
- **Regions**: US, Europe, Asia, emerging markets, global

## 🎯 Perfect For

- **Quantitative Researchers** - Quickly find strategies matching your research criteria
- **Portfolio Managers** - Discover new alpha sources and diversification opportunities  
- **Algorithmic Traders** - Find implementable strategies with clear performance metrics
- **Finance Students** - Learn from 1000+ real-world quantitative strategies
- **Investment Professionals** - Stay current with latest quantitative research

## 🛠️ How It Works

1. **Browse** - Explore strategies by category or search for specific terms
2. **Filter** - Use performance metrics, asset classes, and keywords to narrow results
3. **Analyze** - Get AI-powered summaries of complex academic research
4. **Compare** - Sort by Sharpe ratio, returns, or other metrics to find the best strategies
5. **Implement** - Access detailed methodology and backtest results

## 📊 Sample Strategies You'll Find

- **"Momentum Effect in Stocks"** - Sharpe 1.2, 15% annual returns
- **"Cryptocurrency Pairs Trading"** - Sharpe 0.8, market-neutral approach  
- **"VIX Futures Term Structure"** - Volatility risk premium capture
- **"Cross-Asset Time Series Momentum"** - Multi-asset trend following
- **"Post-Earnings Announcement Drift"** - Equity anomaly exploitation

## 🚀 Quick Start

### Option 1: Use the Live App
Visit **[the deployed application](https://your-railway-url.railway.app)** - no setup required!

### Option 2: Run Locally
```bash
git clone https://github.com/ArjunDivecha/qscreen-strategy-screener.git
cd qscreen-strategy-screener
pip install -r requirements.txt
python app.py
```

## 🔧 Technical Details

- **Backend**: Flask (Python) with caching and parallel processing
- **AI Models**: Groq GPT-OSS-120B and Kimi K2 Instruct for dual perspectives
- **Data**: 1000+ strategies with metadata, performance metrics, and full content
- **Performance**: LRU caching, optimized queries, memory-efficient processing

## 📈 Usage Analytics & Improvements

To understand how users interact with the app and improve the README:

### Add Usage Tracking (Optional)
```python
# Add to app.py for basic analytics
import logging
from datetime import datetime

# Log user interactions
@app.route('/api/strategies')
def get_strategies_endpoint():
    logging.info(f"Strategy search: filters={request.args}")
    # ... existing code

@app.route('/api/strategy/<strategy_name>/summary')  
def get_strategy_summary(strategy_name):
    logging.info(f"AI summary requested: {strategy_name}")
    # ... existing code
```

### Monitor Popular Features
- Most searched keywords
- Most requested AI summaries  
- Popular filter combinations
- Performance metrics usage

## 🤝 Contributing

Found a bug or want to add a feature? 
1. Fork the repository
2. Create a feature branch
3. Submit a pull request

## 📄 License

MIT License - feel free to use for personal or commercial projects

---

**Built with ❤️ for the quantitative finance community** 