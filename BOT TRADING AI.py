import ccxt
import pandas as pd
import numpy as np
import time
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

# Initialize the Binance exchange (or any other exchange)
exchange = ccxt.binance({
    'apiKey': 'YOUR_API_KEY',
    'secret': 'YOUR_SECRET_KEY',
    'enableRateLimit': True
})

# Set trading parameters
symbol = 'BTC/USDT'  # Trading pair
amount = 0.01         # Amount to trade (in BTC)
timeframe = '1h'      # Timeframe (1-hour candles)
limit = 100           # Number of data points to fetch
sma_short = 5         # Short-term SMA window
sma_long = 20         # Long-term SMA window
rsi_period = 14       # RSI period
rsi_threshold = 30    # RSI threshold for oversold/overbought

# Risk management
stop_loss_percentage = 0.02  # Stop loss at 2% loss
take_profit_percentage = 0.05  # Take profit at 5% gain

# Fetch historical data
def fetch_data():
    ohlcv = exchange.fetch_ohlcv(symbol, timeframe, limit=limit)
    df = pd.DataFrame(ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
    return df

# Calculate technical indicators (SMA and RSI)
def calculate_indicators(df):
    df['SMA5'] = df['close'].rolling(window=sma_short).mean()
    df['SMA20'] = df['close'].rolling(window=sma_long).mean()
    
    delta = df['close'].diff()
    gain = delta.where(delta > 0, 0)
    loss = -delta.where(delta < 0, 0)
    avg_gain = gain.rolling(window=rsi_period).mean()
    avg_loss = loss.rolling(window=rsi_period).mean()
    rs = avg_gain / avg_loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df

# Decision making (Buy/Sell/Hold)
def decide_trade(df):
    current_price = df['close'].iloc[-1]
    sma5 = df['SMA5'].iloc[-1]
    sma20 = df['SMA20'].iloc[-1]
    rsi = df['RSI'].iloc[-1]
    
    if sma5 > sma20 and rsi < 70:
        return 'buy'
    elif sma5 < sma20 and rsi > 30:
        return 'sell'
    return 'hold'

# Place an order (Buy/Sell)
def place_order(side):
    try:
        if side == 'buy':
            order = exchange.create_market_buy_order(symbol, amount)
            logger.info(f"Buy order placed: {order}")
        elif side == 'sell':
            order = exchange.create_market_sell_order(symbol, amount)
            logger.info(f"Sell order placed: {order}")
        return order
    except Exception as e:
        logger.error(f"Error placing {side} order: {e}")
        return None

# Apply stop-loss and take-profit
def risk_management(entry_price, current_price):
    stop_loss_price = entry_price * (1 - stop_loss_percentage)
    take_profit_price = entry_price * (1 + take_profit_percentage)
    
    if current_price <= stop_loss_price:
        logger.info("Stop-loss triggered, selling...")
        place_order('sell')
    elif current_price >= take_profit_price:
        logger.info("Take-profit triggered, selling...")
        place_order('sell')

# Main trading loop
def trade():
    entry_price = None
    while True:
        df = fetch_data()
        df = calculate_indicators(df)
        
        trade_signal = decide_trade(df)
        current_price = df['close'].iloc[-1]
        
        if trade_signal == 'buy' and entry_price is None:
            logger.info(f"Buy signal detected at {current_price}")
            place_order('buy')
            entry_price = current_price
        elif trade_signal == 'sell' and entry_price is not None:
            logger.info(f"Sell signal detected at {current_price}")
            place_order('sell')
            entry_price = None  # Reset entry price after selling
        
        # Check if risk management conditions are met
        if entry_price is not None:
            risk_management(entry_price, current_price)
        
        # Wait for the next cycle (e.g., 1 hour for '1h' timeframe)
        time.sleep(60)

if __name__ == "__main__":
    logger.info("Trading bot started...")
    trade()
