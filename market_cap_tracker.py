import asyncio
import json
import time
import os
import requests
from config import (TOP_N_MARKETCAP, MARKETCAP_UPDATE_INTERVAL)

# Constants
MARKET_CAP_FILE = "top_market_cap.json"
COINGECKO_API_URL = "https://api.coingecko.com/api/v3/coins/markets"

# Common stablecoin patterns
STABLECOIN_PATTERNS = [
    'usd', 'usdt', 'usdc', 'busd', 'dai', 'tusd', 'usdd', 'usdp', 'gusd',
    'husd', 'susd', 'nusd', 'cusd', 'musd', 'usdn', 'usdx', 'eurs', 'eurt',
    'ceur'
]


def is_stablecoin(coin_data):
    """
    Check if a coin is a stablecoin based on its symbol and other properties
    """
    symbol = coin_data['symbol'].lower()
    name = coin_data['name'].lower()

    # Check common stablecoin patterns in symbol and name
    if any(pattern in symbol for pattern in STABLECOIN_PATTERNS):
        return True
    if any(pattern in name for pattern in STABLECOIN_PATTERNS):
        return True

    return False


def get_top_market_cap():
    """
    Fetch top N cryptocurrencies by market cap from CoinGecko, excluding stablecoins
    Returns a list of symbols (e.g., ['BTCUSDT', 'ETHUSDT', ...])
    """
    try:
        # Request more coins than needed since we'll filter out stablecoins
        params = {
            'vs_currency': 'usd',
            'order': 'market_cap_desc',
            'per_page':
            TOP_N_MARKETCAP * 2,  # Request more to account for filtered coins
            'page': 1,
        }

        response = requests.get(COINGECKO_API_URL, params=params)
        response.raise_for_status()  # Raise exception for bad status codes

        data = response.json()

        # Filter out stablecoins and get top N
        non_stablecoin_symbols = []
        for coin in data:
            if not is_stablecoin(coin):
                non_stablecoin_symbols.append(f"{coin['symbol'].upper()}USDT")
                if len(non_stablecoin_symbols) >= TOP_N_MARKETCAP:
                    break

        return non_stablecoin_symbols[:TOP_N_MARKETCAP]

    except requests.exceptions.RequestException as e:
        print(f"Error fetching market cap data from CoinGecko: {e}",
              flush=True)
        return []
    except Exception as e:
        print(f"Unexpected error fetching market cap data: {e}", flush=True)
        return []


def save_top_market_cap(symbols):
    """Save the top market cap symbols to a JSON file with timestamp"""
    data = {'timestamp': int(time.time()), 'symbols': symbols}
    try:
        with open(MARKET_CAP_FILE, 'w') as f:
            json.dump(data, f, indent=4)
        print(
            f"Saved top {TOP_N_MARKETCAP} market cap symbols to {MARKET_CAP_FILE}",
            flush=True)
    except Exception as e:
        print(f"Error saving market cap data: {e}", flush=True)


def load_top_market_cap():
    """Load the top market cap symbols from the JSON file"""
    try:
        if not os.path.exists(MARKET_CAP_FILE):
            return None

        with open(MARKET_CAP_FILE, 'r') as f:
            data = json.load(f)

        # Check if data is stale (older than MARKETCAP_UPDATE_INTERVAL)
        if int(time.time()) - data['timestamp'] > MARKETCAP_UPDATE_INTERVAL:
            return None

        return data['symbols']
    except Exception as e:
        print(f"Error loading market cap data: {e}", flush=True)
        return None


def is_top_market_cap(symbol):
    """
    Check if a symbol is in the top market cap list
    Returns True if the symbol is in the top N market cap list
    """
    symbols = load_top_market_cap()

    # If no cached data or data is stale, fetch new data
    if symbols is None:
        symbols = get_top_market_cap()
        if symbols:  # Only save if we successfully got data
            save_top_market_cap(symbols)

    return symbol in symbols if symbols else False


async def update_market_cap_loop():
    """Background task to update market cap data periodically"""
    while True:
        try:
            print("\nUpdating top market cap data...", flush=True)
            symbols = get_top_market_cap()
            if symbols:
                save_top_market_cap(symbols)
                print(f"Top {TOP_N_MARKETCAP} market cap symbols: {symbols}\n",
                      flush=True)
            else:
                print("Failed to update market cap data\n", flush=True)
        except Exception as e:
            print(f"Error in market cap update loop: {e}\n", flush=True)

        await asyncio.sleep(MARKETCAP_UPDATE_INTERVAL)


# Initialize the market cap data on module load
if __name__ == "__main__":
    print("Initializing market cap tracker...\n", flush=True)
    symbols = get_top_market_cap()
    if symbols:
        save_top_market_cap(symbols)
        print(f"Initial top {TOP_N_MARKETCAP} market cap symbols: {symbols}\n",
              flush=True)

    # Run the update loop
    asyncio.run(update_market_cap_loop())
