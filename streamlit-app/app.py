import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import json
import time
from functools import lru_cache
from config import MCP_SERVER_URL, STREAMLIT_CONFIG, CHAT_CONFIG

# Page configuration
st.set_page_config(**STREAMLIT_CONFIG)

class StockChatbot:
    def __init__(self):
        self.mcp_url = MCP_SERVER_URL
        self.cache_duration = 300  # 5 minutes cache
        
    def call_mcp_server(self, method: str, params: dict, max_retries: int = 3):
        """Call MCP server with retry logic and better error handling"""
        last_error = None
        
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.mcp_url}/mcp",
                    json={"method": method, "params": params},
                    timeout=15,  # Increased timeout
                    headers={
                        'User-Agent': 'StockChatbot/1.0',
                        'Accept': 'application/json'
                    }
                )
                
                if response.status_code == 429:  # Rate limited
                    wait_time = 2 ** attempt  # Exponential backoff
                    st.warning(f"Rate limited. Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)
                    continue
                    
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.Timeout:
                last_error = "Request timed out. The server might be overloaded."
                if attempt < max_retries - 1:
                    time.sleep(1)
                    continue
                    
            except requests.exceptions.ConnectionError:
                last_error = "Connection error. Please check your internet connection."
                if attempt < max_retries - 1:
                    time.sleep(2)
                    continue
                    
            except requests.exceptions.HTTPError as e:
                if e.response.status_code == 429:
                    last_error = "Too many requests. Please wait a moment before trying again."
                elif e.response.status_code == 500:
                    last_error = "Server error. Please try again later."
                else:
                    last_error = f"HTTP error {e.response.status_code}: {str(e)}"
                    
            except requests.exceptions.RequestException as e:
                last_error = f"Request failed: {str(e)}"
                
        return {"success": False, "error": last_error}
    
    @st.cache_data(ttl=300)  # Cache for 5 minutes
    def get_stock_info(_self, symbol: str):
        """Get stock information with caching"""
        return _self.call_mcp_server("get_stock_info", {"symbol": symbol.upper()})
    
    @st.cache_data(ttl=300)
    def get_historical_data(_self, symbol: str, period: str = "1mo"):
        """Get historical stock data with caching"""
        return _self.call_mcp_server("get_historical_data", {"symbol": symbol.upper(), "period": period})
    
    @st.cache_data(ttl=120)  # Cache market movers for 2 minutes (more dynamic)
    def get_market_movers(_self):
        """Get top gainers and losers with caching"""
        return _self.call_mcp_server("get_top_gainers_losers", {})
    
    @st.cache_data(ttl=600)  # Cache search results for 10 minutes
    def search_stocks(_self, query: str):
        """Search for stocks with caching"""
        return _self.call_mcp_server("search_stocks", {"query": query})

def init_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": CHAT_CONFIG["welcome_message"]}
        ]
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = StockChatbot()
    if "last_request_time" not in st.session_state:
        st.session_state.last_request_time = 0

def rate_limit_check():
    """Simple rate limiting to prevent too many requests"""
    current_time = time.time()
    if current_time - st.session_state.last_request_time < 1:  # 1 second between requests
        time.sleep(1)
    st.session_state.last_request_time = time.time()

def display_stock_card(stock_data):
    """Display stock information in a card format with better error handling"""
    if isinstance(stock_data, dict) and "error" in stock_data:
        st.error(f"❌ {stock_data['error']}")
        st.info("💡 Try again in a few moments or try a different stock symbol.")
        return
    
    if not isinstance(stock_data, dict):
        st.error("❌ Invalid stock data received")
        return
    
    try:
        # Create a more visually appealing layout
        st.markdown("---")
        
        # Header with company info
        col1, col2 = st.columns([3, 1])
        with col1:
            st.markdown(f"### {stock_data.get('symbol', 'N/A')} - {stock_data.get('company_name', 'Unknown Company')}")
        with col2:
            change = stock_data.get('change', 0)
            change_percent = stock_data.get('change_percent', 0)
            color = "green" if change >= 0 else "red"
            st.markdown(f"<h4 style='color: {color};'>{'📈' if change >= 0 else '📉'} {change_percent:.2f}%</h4>", unsafe_allow_html=True)
        
        # Main metrics
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            current_price = stock_data.get('current_price', 'N/A')
            if current_price != 'N/A':
                st.metric(
                    label="Current Price",
                    value=f"₹{current_price}",
                    delta=f"{change} ({change_percent:.2f}%)" if change != 'N/A' else None
                )
            else:
                st.metric(label="Current Price", value="N/A")
        
        with col2:
            market_cap = stock_data.get('market_cap', 'N/A')
            st.metric(label="Market Cap", value=format_market_cap(market_cap))
        
        with col3:
            volume = stock_data.get('volume', 'N/A')
            volume_str = f"{volume:,}" if volume != 'N/A' and volume is not None else 'N/A'
            st.metric(label="Volume", value=volume_str)
        
        with col4:
            pe_ratio = stock_data.get('pe_ratio', 'N/A')
            st.metric(label="P/E Ratio", value=str(pe_ratio))
        
        # Additional info
        col1, col2, col3 = st.columns(3)
        
        with col1:
            high_52w = stock_data.get('52_week_high', 'N/A')
            high_str = f"₹{high_52w}" if high_52w != 'N/A' else 'N/A'
            st.info(f"**52W High:** {high_str}")
        
        with col2:
            low_52w = stock_data.get('52_week_low', 'N/A')
            low_str = f"₹{low_52w}" if low_52w != 'N/A' else 'N/A'
            st.info(f"**52W Low:** {low_str}")
        
        with col3:
            sector = stock_data.get('sector', 'N/A')
            st.info(f"**Sector:** {sector}")
            
    except Exception as e:
        st.error(f"❌ Error displaying stock data: {str(e)}")
        st.json(stock_data)  # Show raw data for debugging

def format_market_cap(market_cap):
    """Format market cap in Indian format with better error handling"""
    if market_cap == 'N/A' or market_cap is None:
        return 'N/A'
    
    try:
        market_cap = float(market_cap)
        if market_cap >= 10000000000000:  # 10 lakh crore
            return f"₹{market_cap/10000000000000:.2f} L Cr"
        elif market_cap >= 10000000000:  # 1000 crore
            return f"₹{market_cap/10000000000:.2f} K Cr"
        elif market_cap >= 10000000:  # 1 crore
            return f"₹{market_cap/10000000:.2f} Cr"
        else:
            return f"₹{market_cap/100000:.2f} L"
    except (ValueError, TypeError):
        return str(market_cap)

def plot_stock_chart(historical_data):
    """Plot stock price chart with better error handling"""
    if isinstance(historical_data, dict) and "error" in historical_data:
        st.error(f"❌ {historical_data['error']}")
        return
    
    try:
        if "data" not in historical_data:
            st.error("❌ No chart data available")
            return
            
        df = pd.DataFrame(historical_data["data"])
        if df.empty:
            st.warning("📊 No historical data available for this stock")
            return
            
        df['date'] = pd.to_datetime(df['date'])
        
        fig = go.Figure()
        
        fig.add_trace(go.Candlestick(
            x=df['date'],
            open=df['open'],
            high=df['high'],
            low=df['low'],
            close=df['close'],
            name=historical_data.get("symbol", "Stock")
        ))
        
        fig.update_layout(
            title=f"{historical_data.get('symbol', 'Stock')} - Price Chart",
            yaxis_title="Price (₹)",
            xaxis_title="Date",
            template="plotly_white",
            height=500
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"❌ Error creating chart: {str(e)}")

def display_market_movers(movers_data):
    """Display top gainers and losers with better error handling"""
    if isinstance(movers_data, dict) and "error" in movers_data:
        st.error(f"❌ {movers_data['error']}")
        st.info("💡 Market movers data might be temporarily unavailable. Try again later.")
        return
    
    try:
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🚀 Top Gainers")
            gainers = movers_data.get("top_gainers", [])
            if gainers:
                for stock in gainers[:5]:  # Limit to top 5
                    st.success(
                        f"**{stock.get('symbol', 'N/A')}** - ₹{stock.get('current_price', 'N/A')} "
                        f"(+{stock.get('change_percent', 0):.2f}%)"
                    )
            else:
                st.info("No gainers data available")
        
        with col2:
            st.subheader("📉 Top Losers")
            losers = movers_data.get("top_losers", [])
            if losers:
                for stock in losers[:5]:  # Limit to top 5
                    st.error(
                        f"**{stock.get('symbol', 'N/A')}** - ₹{stock.get('current_price', 'N/A')} "
                        f"({stock.get('change_percent', 0):.2f}%)"
                    )
            else:
                st.info("No losers data available")
                
    except Exception as e:
        st.error(f"❌ Error displaying market movers: {str(e)}")

def extract_stock_symbol(query: str):
    """Better stock symbol extraction"""
    query_upper = query.upper()
    words = query_upper.split()
    
    # Common Indian stock symbols
    known_stocks = ['RELIANCE', 'TCS', 'INFY', 'HDFCBANK', 'ICICIBANK', 'SBIN', 'ITC', 'LT', 'WIPRO', 'MARUTI']
    
    # First check for known stocks
    for word in words:
        if word in known_stocks:
            return word
    
    # Then check for potential symbols (3+ chars, all alpha)
    for word in words:
        if len(word) >= 3 and word.isalpha():
            return word
    
    return None

def process_user_query(query: str, chatbot: StockChatbot):
    """Process user query with improved parsing and error handling"""
    query_lower = query.lower()
    
    try:
        # Rate limiting
        rate_limit_check()
        
        # Stock price queries
        if any(keyword in query_lower for keyword in ["price", "quote", "current", "value"]):
            symbol = extract_stock_symbol(query)
            if symbol:
                result = chatbot.get_stock_info(symbol)
                if result.get("success") and "error" not in result.get("data", {}):
                    return "stock_info", result["data"]
                else:
                    error_msg = result.get("error", "Unknown error occurred")
                    return "text", f"❌ Sorry, couldn't fetch data for {symbol}. {error_msg}"
            return "text", "Please specify a valid stock symbol (e.g., 'RELIANCE price', 'TCS quote')"
        
        # Historical data queries
        elif any(keyword in query_lower for keyword in ["chart", "historical", "graph", "trend"]):
            symbol = extract_stock_symbol(query)
            if symbol:
                result = chatbot.get_historical_data(symbol)
                if result.get("success") and "error" not in result.get("data", {}):
                    return "chart", result["data"]
                else:
                    error_msg = result.get("error", "Unknown error occurred")
                    return "text", f"❌ Sorry, couldn't fetch chart for {symbol}. {error_msg}"
            return "text", "Please specify a valid stock symbol for the chart (e.g., 'TCS chart', 'RELIANCE graph')"
        
        # Market movers queries
        elif any(keyword in query_lower for keyword in ["gainers", "losers", "movers", "top"]):
            result = chatbot.get_market_movers()
            if result.get("success"):
                return "movers", result["data"]
            else:
                error_msg = result.get("error", "Unknown error occurred")
                return "text", f"❌ Sorry, couldn't fetch market movers. {error_msg}"
        
        # Search queries
        elif any(keyword in query_lower for keyword in ["search", "find", "lookup"]):
            # Extract search term
            search_terms = ["search", "find", "lookup"]
            search_term = None
            for term in search_terms:
                if term in query_lower:
                    parts = query.split(term)
                    if len(parts) > 1:
                        search_term = parts[1].strip()
                        break
            
            if search_term:
                result = chatbot.search_stocks(search_term)
                if result.get("success"):
                    return "search", result["data"]
                else:
                    error_msg = result.get("error", "Unknown error occurred")
                    return "text", f"❌ Sorry, couldn't search for '{search_term}'. {error_msg}"
            return "text", "Please specify what to search for (e.g., 'search banking', 'find IT companies')"
        
        # Help/default response
        else:
            help_text = """
🤖 **I can help you with:**

📊 **Stock Information:**
- "RELIANCE price" - Get current price and details
- "TCS quote" - Get stock quote

📈 **Charts & Trends:**
- "INFY chart" - View price chart
- "HDFCBANK graph" - Historical data

🏆 **Market Overview:**
- "top gainers" - Best performing stocks
- "market movers" - Gainers and losers

🔍 **Search:**
- "search banking" - Find banking stocks
- "find IT companies" - Search by sector

💡 **Tip:** Use exact stock symbols like RELIANCE, TCS, INFY for best results!
            """
            return "text", help_text.strip()
            
    except Exception as e:
        return "text", f"❌ Sorry, something went wrong processing your request: {str(e)}"

def safe_button_click(button_func, *args, **kwargs):
    """Wrapper for button clicks with error handling"""
    try:
        return button_func(*args, **kwargs)
    except Exception as e:
        st.error(f"❌ Button action failed: {str(e)}")
        return False

def main():
    st.title("📈 Indian Stock Market Chatbot")
    st.markdown("Get real-time stock information, charts, and market insights!")
    
    init_session_state()
    chatbot = st.session_state.chatbot
    
    # Sidebar with quick actions
    with st.sidebar:
        st.header("🚀 Quick Actions")
        
        if st.button("📊 Market Movers"):
            with st.spinner("Fetching market movers..."):
                result = chatbot.get_market_movers()
                if result.get("success"):
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": "Show market movers"
                    })
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "movers",
                        "data": result["data"]
                    })
                    st.rerun()
        
        st.markdown("---")
        
        # Stock lookup
        st.subheader("🔍 Quick Stock Lookup")
        stock_symbol = st.text_input("Enter stock symbol:", placeholder="e.g., RELIANCE, TCS")
        
        if st.button("Get Stock Info") and stock_symbol:
            with st.spinner(f"Fetching {stock_symbol} data..."):
                result = chatbot.get_stock_info(stock_symbol)
                if result.get("success"):
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": f"Get info for {stock_symbol}"
                    })
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "stock_info",
                        "data": result["data"]
                    })
                    st.rerun()
        
        st.markdown("---")
        st.markdown("**📈 Popular Stocks:**")
        popular_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        
        for stock in popular_stocks:
            if st.button(stock, key=f"pop_{stock}"):
                with st.spinner(f"Fetching {stock} data..."):
                    result = chatbot.get_stock_info(stock)
                    if result.get("success"):
                        st.session_state.messages.append({
                            "role": "user", 
                            "content": f"Get info for {stock}"
                        })
                        st.session_state.messages.append({
                            "role": "assistant", 
                            "content": "stock_info",
                            "data": result["data"]
                        })
                        st.rerun()
        
        # Add status indicator
        st.markdown("---")
        st.markdown("**🟢 System Status:** Online")
        st.caption(f"Last updated: {datetime.now().strftime('%H:%M:%S')}")
    
    # Main chat interface
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and "data" in message:
                content_type = message["content"]
                data = message["data"]
                
                if content_type == "stock_info":
                    display_stock_card(data)
                elif content_type == "chart":
                    plot_stock_chart(data)
                elif content_type == "movers":
                    display_market_movers(data)
                elif content_type == "search":
                    st.write("🔍 **Search Results:**")
                    if isinstance(data, list) and data:
                        for stock in data[:10]:  # Limit results
                            st.write(f"• **{stock.get('symbol', 'N/A')}** - {stock.get('company_name', 'Unknown')} ({stock.get('sector', 'N/A')})")
                    else:
                        st.info("No search results found")
                else:
                    st.write(message["content"])
            else:
                st.write(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me about stocks, market trends, or any stock-related queries..."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.write(prompt)
        
        # Process query and generate response
        with st.chat_message("assistant"):
            with st.spinner("🔄 Processing your request..."):
                response_type, response_data = process_user_query(prompt, chatbot)
                
                if response_type == "text":
                    st.write(response_data)
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_data
                    })
                else:
                    # Display the appropriate visualization
                    if response_type == "stock_info":
                        display_stock_card(response_data)
                    elif response_type == "chart":
                        plot_stock_chart(response_data)
                    elif response_type == "movers":
                        display_market_movers(response_data)
                    elif response_type == "search":
                        st.write("🔍 **Search Results:**")
                        if isinstance(response_data, list) and response_data:
                            for stock in response_data[:10]:
                                st.write(f"• **{stock.get('symbol', 'N/A')}** - {stock.get('company_name', 'Unknown')} ({stock.get('sector', 'N/A')})")
                        else:
                            st.info("No search results found")
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_type,
                        "data": response_data
                    })
        
        # Limit message history to prevent memory issues
        max_messages = CHAT_CONFIG.get("max_messages", 50)
        if len(st.session_state.messages) > max_messages:
            st.session_state.messages = st.session_state.messages[-max_messages:]

if __name__ == "__main__":
    main()
