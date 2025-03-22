from binance.client import Client
from binance.enums import *
import time

# Set up your Binance API keys
API_KEY = ""
API_SECRET = ""

# Initialize Binance client
client = Client(API_KEY, API_SECRET,
                testnet=True)  # Set testnet=False for live trading

# Trading parameters
symbol = "BTCUSDT"
initial_capital = 1000  # USD
leverage = 5

# Get BTC price
ticker = client.futures_symbol_ticker(symbol=symbol)
btc_price = float(ticker["price"])

# Calculate order size
order_size = (initial_capital * leverage) / btc_price

# Set leverage (Ensure leverage is set before placing the order)
client.futures_change_leverage(symbol=symbol, leverage=leverage)

# Place market buy order
buy_order = client.futures_create_order(symbol=symbol,
                                        side=SIDE_BUY,
                                        type=ORDER_TYPE_MARKET,
                                        quantity=order_size)

print(f"Market Buy Order Executed: {order_size} BTC at ${btc_price}")

# Wait 5 minutes
time.sleep(300)

# Get new BTC price
ticker = client.futures_symbol_ticker(symbol=symbol)
new_btc_price = float(ticker["price"])

# Place market sell order
sell_order = client.futures_create_order(symbol=symbol,
                                         side=SIDE_SELL,
                                         type=ORDER_TYPE_MARKET,
                                         quantity=order_size)

# Calculate profit/loss
final_capital = initial_capital + (
    (new_btc_price - btc_price) * order_size * leverage)

print(f"Market Sell Order Executed: {order_size} BTC at ${new_btc_price}")
print(f"Before Capital: ${initial_capital}")
print(f"After Capital: ${final_capital:.2f}")
