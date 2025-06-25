import asyncio
import random
import time
import os
import math
from binance.client import Client
from binance.exceptions import BinanceAPIException
from config import (MAX_RETRIES, RETRY_AFTER, INITIAL_CAPITAL, LEVERAGE,
                    HODL_TIME, BINANCE_TESTNET_API_KEY,
                    BINANCE_TESTNET_API_SECRET)
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Binance Client
client = Client(BINANCE_TESTNET_API_KEY,
                BINANCE_TESTNET_API_SECRET,
                testnet=True)
client.session.verify = False


# Retry logic
def retry_api_call(func, *args, **kwargs):
    retries = MAX_RETRIES or 3
    delay = RETRY_AFTER or 2
    for _ in range(retries):
        try:
            return func(*args, **kwargs)
        except BinanceAPIException as e:
            print(f"Binance API Error: {e}. Retrying...", flush=True)
        except Exception as e:
            print(f"Unexpected error: {e}. Retrying...", flush=True)
        time.sleep(delay)
    print("Max retries reached. Operation failed.", flush=True)
    return None


# Get symbol's quantity precision
def get_symbol_precision():
    try:
        exchange_info = client.futures_exchange_info()
        symbol_quantity_precision_dict = {}
        for symbol_info in exchange_info["symbols"]:
            symbol = symbol_info.get("symbol")
            price_precision = symbol_info.get("quantityPrecision")
            if symbol and price_precision:
                symbol_quantity_precision_dict[symbol] = int(price_precision)
        return symbol_quantity_precision_dict
    except BinanceAPIException as e:
        print(f"Error fetching precision: {e}", flush=True)
        return {}


# Initialisation
symbol_quantity_precision_dict = retry_api_call(get_symbol_precision)
if not symbol_quantity_precision_dict:
    print("Failed to fetch quantity precision. Exiting...", flush=True)
    exit(1)
print(symbol_quantity_precision_dict)

symbol_queue = asyncio.Queue()
processing_symbols = set()


# Get ticker price with retry logic
def get_price(symbol):
    return retry_api_call(client.futures_symbol_ticker, symbol=symbol)


def change_leverage(symbol, leverage):
    retry_api_call(client.futures_change_leverage,
                   symbol=symbol,
                   leverage=leverage)


# Place market buy order with retry logic
def place_buy_order(symbol, order_size):
    return retry_api_call(client.futures_create_order,
                          symbol=symbol,
                          side="BUY",
                          type="MARKET",
                          quantity=order_size)


# Place market sell order with retry logic
def place_sell_order(symbol, order_size):
    return retry_api_call(client.futures_create_order,
                          symbol=symbol,
                          side="SELL",
                          type="MARKET",
                          quantity=order_size)


# Function to simulate a trading operation for a single ticker
async def trade(symbol):
    base_symbol = symbol.replace("USDT", "")
    selected_symbol_price_precision = symbol_quantity_precision_dict.get(
        symbol)

    print(f"\nTrading Parameters:")
    print(f"----------------------------------", flush=True)
    print(f"Symbol: {symbol}", flush=True)
    print(f"Symbol Quantity Precision: {selected_symbol_price_precision}",
          flush=True)
    print(f"Initial Capital: ${INITIAL_CAPITAL:,.2f}", flush=True)
    print(f"Leverage: {LEVERAGE}x", flush=True)

    # Get ticker's price
    ticker = get_price(symbol)
    price = float(ticker["price"])

    # Calculate order size
    order_size = (INITIAL_CAPITAL * LEVERAGE) / price
    if selected_symbol_price_precision:
        order_size = math.floor(order_size *
                                (10**selected_symbol_price_precision)) / (
                                    10**selected_symbol_price_precision)
        corrected_initial_capital = (order_size * price) / LEVERAGE
    else:
        corrected_initial_capital = INITIAL_CAPITAL

    print(f"Order Size (in {base_symbol}): {order_size}", flush=True)
    print(f"----------------------------------\n", flush=True)

    change_leverage(symbol, LEVERAGE)

    print(f"Starting trade for {symbol}", flush=True)
    buy_order = place_buy_order(symbol, order_size)
    if buy_order:
        print(
            f"Market Buy Order Executed: {order_size} {base_symbol} at ${price}",
            flush=True)
        await asyncio.sleep(HODL_TIME)  # Simulate holding the position
        print(f"\nHodling for {HODL_TIME} seconds...\n", flush=True)
        ticker = get_price(symbol)
        new_price = float(ticker["price"])
        sell_order = place_sell_order(symbol, order_size)
        if sell_order:
            print(
                f"Market Sell Order Executed: {order_size} {base_symbol} at ${new_price}\n",
                flush=True)
            final_capital = corrected_initial_capital + (
                (new_price - price) * order_size)
            print(f"Trade Summary:", flush=True)
            print(f"----------------------------------", flush=True)
            print(f"Before Capital: ${corrected_initial_capital:.2f}",
                  flush=True)
            print(f"After Capital: ${final_capital:.2f}", flush=True)
            print(f"----------------------------------\n", flush=True)
        else:
            print(f"Sell order failed for {symbol}\n", flush=True)
    else:
        print(f"Buy order failed for {symbol}\n", flush=True)

    processing_symbols.remove(symbol)


# Function to simulate symbol arrivals asynchronously
async def simulate_symbol_arrivals():
    symbols = [
        # "BTCUSDT",
        "ETHUSDT",
        # "BNBUSDT",
        # "XRPUSDT",
    ]
    while True:
        symbol = random.choice(symbols)

        # Check if symbol is already in queue or being processed
        if symbol in processing_symbols or symbol in symbol_queue._queue:
            print(
                f"\n{symbol} is already in queue or being processed, skipping...",
                flush=True)
        else:
            print(f"\nAdding {symbol} to the queue", flush=True)
            await symbol_queue.put(symbol)

        await asyncio.sleep(random.uniform(1, 2))  # Non-blocking sleep


# Worker function to process tickers from the queue asynchronously
async def worker():
    while True:
        symbol = await symbol_queue.get(
        )  # Asynchronously get a symbol from the queue
        if symbol is None:
            break

        processing_symbols.add(symbol)
        print(f"Worker processing symbol: {symbol}", flush=True)

        # Execute trade
        await trade(symbol)

        symbol_queue.task_done()


# Main function to run trades concurrently using a queue
async def main():
    print("\nStarting main function", flush=True)

    # Start worker tasks
    workers = [asyncio.create_task(worker()) for _ in range(os.cpu_count())]

    # Start ticker simulation (async)
    await simulate_symbol_arrivals()

    # Wait for all tasks to complete
    await symbol_queue.join()

    # Stop worker tasks by putting None in the queue to signal termination
    for _ in range(os.cpu_count()):
        await symbol_queue.put(None)

    # Wait for workers to finish
    await asyncio.gather(*workers)

    print("All trades completed.", flush=True)


if __name__ == "__main__":
    asyncio.run(main())
