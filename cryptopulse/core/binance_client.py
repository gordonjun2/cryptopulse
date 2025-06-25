"""
Binance API client and related functions for CryptoPulse trading bot.
"""

import time
import binance.client
from binance.exceptions import BinanceAPIException
from ..config import (MAX_RETRIES, RETRY_AFTER, BINANCE_TESTNET_API_KEY,
                     BINANCE_TESTNET_API_SECRET, BINANCE_TESTNET_FLAG, ENV)
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class BinanceClientManager:
    """Manages Binance client initialization and API calls."""
    
    def __init__(self):
        self.client = None
        self.perps_tokens = None
        self._initialize_client()
        self._initialize_symbols()
    
    def _initialize_client(self):
        """Initialize Binance client."""
        try:
            if BINANCE_TESTNET_FLAG:
                self.client = binance.client.Client(BINANCE_TESTNET_API_KEY,
                                                   BINANCE_TESTNET_API_SECRET,
                                                   testnet=True)
            else:
                self.client = binance.client.Client()

            if ENV == 'dev':
                self.client.session.verify = False
        except BinanceAPIException as e:
            print(f"Failed to initialize Binance client: {e}", flush=True)
            self.client = None
        except Exception as e:
            print(f"Unexpected error initializing Binance client: {e}", flush=True)
            self.client = None
    
    def _initialize_symbols(self):
        """Initialize perps tokens/symbols."""
        if BINANCE_TESTNET_FLAG:
            self.perps_tokens = self.retry_api_call(self.get_symbol_precision)
            if not self.perps_tokens:
                print("Failed to fetch quantity precision. Exiting...", flush=True)
                exit(1)
        else:
            if self.client:
                exchange_info = self.client.futures_exchange_info()
                self.perps_tokens = [
                    symbol['symbol'] for symbol in exchange_info['symbols']
                    if 'USDT' in symbol['symbol'] and symbol['status'] == 'TRADING'
                ]
    
    def retry_api_call(self, func, *args, **kwargs):
        """Retry logic for Binance API calls."""
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
    
    def get_symbol_precision(self):
        """Get symbol's quantity precision."""
        try:
            exchange_info = self.client.futures_exchange_info()
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
    
    def get_price(self, symbol):
        """Get ticker price with retry logic."""
        return self.retry_api_call(self.client.futures_symbol_ticker, symbol=symbol)
    
    def change_leverage(self, symbol, leverage):
        """Set leverage."""
        self.retry_api_call(self.client.futures_change_leverage,
                           symbol=symbol,
                           leverage=leverage)
    
    def place_buy_order(self, symbol, order_size):
        """Place market buy order with retry logic."""
        return self.retry_api_call(self.client.futures_create_order,
                                   symbol=symbol,
                                   side="BUY",
                                   type="MARKET",
                                   quantity=order_size)
    
    def place_sell_order(self, symbol, order_size):
        """Place market sell order with retry logic."""
        return self.retry_api_call(self.client.futures_create_order,
                                   symbol=symbol,
                                   side="SELL",
                                   type="MARKET",
                                   quantity=order_size)


# Global client instance
binance_client = BinanceClientManager()