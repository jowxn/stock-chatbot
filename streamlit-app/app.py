import streamlit as st
import requests
import plotly.graph_objects as go
import plotly.express as px
import pandas as pd
from datetime import datetime
import json
from config import MCP_SERVER_URL, STREAMLIT_CONFIG, CHAT_CONFIG

# Page configuration
st.set_page_config(**STREAMLIT_CONFIG)

class StockChatbot:
    def __init__(self):
        self.mcp_url = MCP_SERVER_URL
        
    def call_mcp_server(self, method: str, params: dict):
        """Call MCP server with given method and parameters"""
        try:
            response = requests.post(
                f"{self.mcp_url}/mcp",
                json={"method": method, "params": params},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}
    
    def get_stock_info(self, symbol: str):
        """Get stock information"""
        return self.call_mcp_server("get_stock_info", {"symbol": symbol})
    
    def get_historical_data(self, symbol: str, period: str = "1mo"):
        """Get historical stock data"""
        return self.call_mcp_server("get_historical_data", {"symbol": symbol, "period": period})
    
    def get_market_movers(self):
        """Get top gainers and losers"""
        return self.call_mcp_server("get_top_gainers_losers", {})
    
    def search_stocks(self, query: str):
        """Search for stocks"""
        return self.call_mcp_server("search_stocks", {"query": query})

def init_session_state():
    """Initialize session state variables"""
    if "messages" not in st.session_state:
        st.session_state.messages = [
            {"role": "assistant", "content": CHAT_CONFIG["welcome_message"]}
        ]
    if "chatbot" not in st.session_state:
        st.session_state.chatbot = StockChatbot()

def display_stock_card(stock_data):
    """Display stock information in a card format"""
    if "error" in stock_data:
        st.error(stock_data["error"])
        return
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(
            label=f"{stock_data['symbol']} - {stock_data['company_name']}",
            value=f"₹{stock_data['current_price']}",
            delta=f"{stock_data['change']} ({stock_data['change_percent']:.2f}%)"
        )
    
    with col2:
        st.write("**Market Cap:**", format_market_cap(stock_data['market_cap']))
        st.write("**Volume:**", f"{stock_data['volume']:,}" if stock_data['volume'] != 'N/A' else 'N/A')
        st.write("**P/E Ratio:**", stock_data['pe_ratio'])
    
    with col3:
        st.write("**52W High:**", f"₹{stock_data['52_week_high']}" if stock_data['52_week_high'] != 'N/A' else 'N/A')
        st.write("**52W Low:**", f"₹{stock_data['52_week_low']}" if stock_data['52_week_low'] != 'N/A' else 'N/A')
        st.write("**Sector:**", stock_data['sector'])

def format_market_cap(market_cap):
    """Format market cap in Indian format"""
    if market_cap == 'N/A' or market_cap is None:
        return 'N/A'
    
    try:
        if market_cap >= 10000000000000:  # 10 lakh crore
            return f"₹{market_cap/10000000000000:.2f} L Cr"
        elif market_cap >= 10000000000:  # 1000 crore
            return f"₹{market_cap/10000000000:.2f} K Cr"
        elif market_cap >= 10000000:  # 1 crore
            return f"₹{market_cap/10000000:.2f} Cr"
        else:
            return f"₹{market_cap/100000:.2f} L"
    except:
        return str(market_cap)

def plot_stock_chart(historical_data):
    """Plot stock price chart"""
    if "error" in historical_data:
        st.error(historical_data["error"])
        return
    
    df = pd.DataFrame(historical_data["data"])
    df['date'] = pd.to_datetime(df['date'])
    
    fig = go.Figure()
    
    fig.add_trace(go.Candlestick(
        x=df['date'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name=historical_data["symbol"]
    ))
    
    fig.update_layout(
        title=f"{historical_data['symbol']} - Stock Price Chart",
        yaxis_title="Price (₹)",
        xaxis_title="Date",
        template="plotly_white"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def display_market_movers(movers_data):
    """Display top gainers and losers"""
    if "error" in movers_data:
        st.error(movers_data["error"])
        return
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🚀 Top Gainers")
        for stock in movers_data["top_gainers"]:
            st.success(
                f"**{stock['symbol']}** - ₹{stock['current_price']} "
                f"(+{stock['change_percent']:.2f}%)"
            )
    
    with col2:
        st.subheader("📉 Top Losers")
        for stock in movers_data["top_losers"]:
            st.error(
                f"**{stock['symbol']}** - ₹{stock['current_price']} "
                f"({stock['change_percent']:.2f}%)"
            )

def process_user_query(query: str, chatbot: StockChatbot):
    """Process user query and return appropriate response"""
    query_lower = query.lower()
    
    # Stock price queries
    if "price" in query_lower or "quote" in query_lower:
        # Extract stock symbol (simple approach)
        words = query.split()
        for word in words:
            if len(word) >= 3 and word.upper().isalpha():
                result = chatbot.get_stock_info(word)
                if result["success"] and "error" not in result["data"]:
                    return "stock_info", result["data"]
        return "text", "Please specify a valid stock symbol (e.g., RELIANCE, TCS, INFY)"
    
    # Historical data queries
    elif "chart" in query_lower or "historical" in query_lower or "graph" in query_lower:
        words = query.split()
        for word in words:
            if len(word) >= 3 and word.upper().isalpha():
                result = chatbot.get_historical_data(word)
                if result["success"] and "error" not in result["data"]:
                    return "chart", result["data"]
        return "text", "Please specify a valid stock symbol for the chart"
    
    # Market movers queries
    elif "gainers" in query_lower or "losers" in query_lower or "movers" in query_lower:
        result = chatbot.get_market_movers()
        if result["success"]:
            return "movers", result["data"]
        else:
            return "text", "Sorry, couldn't fetch market movers data"
    
    # Search queries
    elif "search" in query_lower or "find" in query_lower:
        query_word = query.split()[-1]  # Take last word as search term
        result = chatbot.search_stocks(query_word)
        if result["success"]:
            return "search", result["data"]
        else:
            return "text", "Sorry, couldn't search for stocks"
    
    # Default response
    else:
        return "text", "I can help you with:\n- Stock prices (e.g., 'RELIANCE price')\n- Stock charts (e.g., 'TCS chart')\n- Market movers (e.g., 'top gainers')\n- Stock search (e.g., 'search banking')"

def main():
    st.title("📈 Indian Stock Market Chatbot")
    st.markdown("Get real-time stock information, charts, and market insights!")
    
    init_session_state()
    chatbot = st.session_state.chatbot
    
    # Sidebar with quick actions
    with st.sidebar:
        st.header("Quick Actions")
        
        if st.button("📊 Market Movers"):
            result = chatbot.get_market_movers()
            if result["success"]:
                st.session_state.messages.append({
                    "role": "user", 
                    "content": "Show market movers"
                })
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "movers",
                    "data": result["data"]
                })
        
        st.markdown("---")
        
        # Stock lookup
        st.subheader("Quick Stock Lookup")
        stock_symbol = st.text_input("Enter stock symbol:", placeholder="e.g., RELIANCE")
        
        if st.button("Get Stock Info") and stock_symbol:
            result = chatbot.get_stock_info(stock_symbol)
            if result["success"]:
                st.session_state.messages.append({
                    "role": "user", 
                    "content": f"Get info for {stock_symbol}"
                })
                st.session_state.messages.append({
                    "role": "assistant", 
                    "content": "stock_info",
                    "data": result["data"]
                })
        
        st.markdown("---")
        st.markdown("**Popular Stocks:**")
        popular_stocks = ["RELIANCE", "TCS", "INFY", "HDFCBANK", "ICICIBANK"]
        for stock in popular_stocks:
            if st.button(stock, key=f"pop_{stock}"):
                result = chatbot.get_stock_info(stock)
                if result["success"]:
                    st.session_state.messages.append({
                        "role": "user", 
                        "content": f"Get info for {stock}"
                    })
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": "stock_info",
                        "data": result["data"]
                    })
    
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
                    st.write("**Search Results:**")
                    for stock in data:
                        st.write(f"• **{stock['symbol']}** - {stock['company_name']} ({stock['sector']})")
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
            with st.spinner("Fetching data..."):
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
                        st.write("**Search Results:**")
                        for stock in response_data:
                            st.write(f"• **{stock['symbol']}** - {stock['company_name']} ({stock['sector']})")
                    
                    st.session_state.messages.append({
                        "role": "assistant", 
                        "content": response_type,
                        "data": response_data
                    })
        
        # Limit message history
        if len(st.session_state.messages) > CHAT_CONFIG["max_messages"]:
            st.session_state.messages = st.session_state.messages[-CHAT_CONFIG["max_messages"]:]

if __name__ == "__main__":
    main()