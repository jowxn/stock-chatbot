import yfinance as yf
import pandas as pd
import requests
from typing import Dict, List, Optional
import json
from datetime import datetime, timedelta

class IndianStockData:
    def __init__(self):
        self.nse_symbols = {}
        self.load_nse_symbols()
    
    def load_nse_symbols(self):
        """Load NSE stock symbols mapping"""
        # Common Indian stocks with their Yahoo Finance symbols
        self.nse_symbols = {
            "RELIANCE": "RELIANCE.NS",
            "TCS": "TCS.NS",
            "INFY": "INFY.NS",
            "HDFCBANK": "HDFCBANK.NS",
            "ICICIBANK": "ICICIBANK.NS",
            "HINDUNILVR": "HINDUNILVR.NS",
            "SBIN": "SBIN.NS",
            "BHARTIARTL": "BHARTIARTL.NS",
            "ITC": "ITC.NS",
            "KOTAKBANK": "KOTAKBANK.NS",
            "LT": "LT.NS",
            "ASIANPAINT": "ASIANPAINT.NS",
            "MARUTI": "MARUTI.NS",
            "BAJFINANCE": "BAJFINANCE.NS",
            "HCLTECH": "HCLTECH.NS"
        }
    
    def get_stock_info(self, symbol: str) -> Dict:
        """Get detailed stock information"""
        try:
            # Convert to Yahoo Finance format
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            
            stock = yf.Ticker(yf_symbol)
            info = stock.info
            hist = stock.history(period="1d")
            
            if hist.empty:
                return {"error": f"No data found for symbol {symbol}"}
            
            current_price = hist['Close'].iloc[-1]
            prev_close = info.get('previousClose', current_price)
            change = current_price - prev_close
            change_percent = (change / prev_close) * 100 if prev_close else 0
            
            return {
                "symbol": symbol.upper(),
                "company_name": info.get('longName', 'N/A'),
                "current_price": round(current_price, 2),
                "previous_close": round(prev_close, 2),
                "change": round(change, 2),
                "change_percent": round(change_percent, 2),
                "volume": info.get('volume', 'N/A'),
                "market_cap": info.get('marketCap', 'N/A'),
                "pe_ratio": info.get('trailingPE', 'N/A'),
                "dividend_yield": info.get('dividendYield', 'N/A'),
                "52_week_high": info.get('fiftyTwoWeekHigh', 'N/A'),
                "52_week_low": info.get('fiftyTwoWeekLow', 'N/A'),
                "sector": info.get('sector', 'N/A'),
                "industry": info.get('industry', 'N/A')
            }
        except Exception as e:
            return {"error": f"Error fetching data for {symbol}: {str(e)}"}
    
    def get_historical_data(self, symbol: str, period: str = "1mo") -> Dict:
        """Get historical stock data"""
        try:
            yf_symbol = self.nse_symbols.get(symbol.upper(), f"{symbol.upper()}.NS")
            stock = yf.Ticker(yf_symbol)
            hist = stock.history(period=period)
            
            if hist.empty:
                return {"error": f"No historical data found for {symbol}"}
            
            hist_data = []
            for date, row in hist.iterrows():
                hist_data.append({
                    "date": date.strftime("%Y-%m-%d"),
                    "open": round(row['Open'], 2),
                    "high": round(row['High'], 2),
                    "low": round(row['Low'], 2),
                    "close": round(row['Close'], 2),
                    "volume": int(row['Volume'])
                })
            
            return {
                "symbol": symbol.upper(),
                "period": period,
                "data": hist_data
            }
        except Exception as e:
            return {"error": f"Error fetching historical data for {symbol}: {str(e)}"}
    
    def get_top_gainers_losers(self) -> Dict:
        """Get top gainers and losers from major Indian stocks"""
        stocks_data = []
        
        for symbol in list(self.nse_symbols.keys())[:10]:  # Top 10 stocks
            data = self.get_stock_info(symbol)
            if "error" not in data:
                stocks_data.append(data)
        
        # Sort by change percentage
        gainers = sorted([s for s in stocks_data if s.get('change_percent', 0) > 0], 
                        key=lambda x: x.get('change_percent', 0), reverse=True)[:5]
        losers = sorted([s for s in stocks_data if s.get('change_percent', 0) < 0], 
                       key=lambda x: x.get('change_percent', 0))[:5]
        
        return {
            "top_gainers": gainers,
            "top_losers": losers,
            "timestamp": datetime.now().isoformat()
        }
    
    def search_stocks(self, query: str) -> List[Dict]:
        """Search for stocks based on query"""
        results = []
        query_lower = query.lower()
        
        for symbol, yf_symbol in self.nse_symbols.items():
            if query_lower in symbol.lower():
                try:
                    stock = yf.Ticker(yf_symbol)
                    info = stock.info
                    results.append({
                        "symbol": symbol,
                        "company_name": info.get('longName', 'N/A'),
                        "sector": info.get('sector', 'N/A')
                    })
                except:
                    results.append({
                        "symbol": symbol,
                        "company_name": "N/A",
                        "sector": "N/A"
                    })
        
        return results[:10]  # Return top 10 matches