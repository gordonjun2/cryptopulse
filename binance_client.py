import math
import time
import binance.client
from binance.exceptions import BinanceAPIException
from config import (
    BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET,
    BINANCE_TESTNET_FLAG, MAX_RETRIES, RETRY_AFTER, ENV
)


class BinanceClient:
    """Handles all Binance API operations"""
    
    def __init__(self):
        self.client = None
        self.perps_tokens = {}
        self._initialize_client()
        self._load_trading_pairs()
    
    def _initialize_client(self):
        """Initialize Binance client with proper configuration"""
        try:
            if BINANCE_TESTNET_FLAG:
                self.client = binance.client.Client(
                    BINANCE_TESTNET_API_KEY,
                    BINANCE_TESTNET_API_SECRET,
                    testnet=True
                )
            else:
                self.client = binance.client.Client()

            if ENV == 'dev':
                self.client.session.verify = False
                
            print("Binance client initialized successfully")
        except BinanceAPIException as e:
            print(f"Failed to initialize Binance client: {e}")
            self.client = None
        except Exception as e:
            print(f"Unexpected error initializing Binance client: {e}")
            self.client = None
    
    def _load_trading_pairs(self):
        """Load available trading pairs and their precision"""
        if not self.client:
            return
            
        try:
            if BINANCE_TESTNET_FLAG:
                self.perps_tokens = self._get_symbol_precision()
            else:
                exchange_info = self.client.futures_exchange_info()
                self.perps_tokens = [
                    symbol['symbol'] for symbol in exchange_info['symbols']
                    if 'USDT' in symbol['symbol'] and symbol['status'] == 'TRADING'
                ]
        except Exception as e:
            print(f"Error loading trading pairs: {e}")
            self.perps_tokens = {}
    
    def retry_api_call(self, func, *args, **kwargs):
        """Retry API calls with exponential backoff"""
        retries = MAX_RETRIES or 3
        delay = RETRY_AFTER or 2
        
        for attempt in range(retries):
            try:
                return func(*args, **kwargs)
            except BinanceAPIException as e:
                print(f"Binance API Error (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(delay * (2 ** attempt))  # Exponential backoff
            except Exception as e:
                print(f"Unexpected error (attempt {attempt + 1}): {e}")
                if attempt < retries - 1:
                    time.sleep(delay)
        
        print("Max retries reached. Operation failed.")
        return None
    
    def _get_symbol_precision(self):
        """Get symbol quantity precision for testnet"""
        try:
            exchange_info = self.client.futures_exchange_info()
            precision_dict = {}
            
            for symbol_info in exchange_info["symbols"]:
                symbol = symbol_info.get("symbol")
                precision = symbol_info.get("quantityPrecision")
                if symbol and precision:
                    precision_dict[symbol] = int(precision)
            
            return precision_dict
        except BinanceAPIException as e:
            print(f"Error fetching precision: {e}")
            return {}
    
    def get_price(self, symbol):
        """Get current price for a symbol"""
        if not self.client:
            return None
        return self.retry_api_call(self.client.futures_symbol_ticker, symbol=symbol)
    
    def change_leverage(self, symbol, leverage):
        """Change leverage for a symbol"""
        if not self.client:
            return None
        return self.retry_api_call(
            self.client.futures_change_leverage,
            symbol=symbol,
            leverage=leverage
        )
    
    def place_buy_order(self, symbol, quantity):
        """Place a market buy order"""
        if not self.client:
            return None
        return self.retry_api_call(
            self.client.futures_create_order,
            symbol=symbol,
            side="BUY",
            type="MARKET",
            quantity=quantity
        )
    
    def place_sell_order(self, symbol, quantity):
        """Place a market sell order"""
        if not self.client:
            return None
        return self.retry_api_call(
            self.client.futures_create_order,
            symbol=symbol,
            side="SELL",
            type="MARKET",
            quantity=quantity
        )
    
    def calculate_order_size(self, symbol, price, capital, leverage):
        """Calculate order size based on capital and leverage"""
        try:
            order_size = (capital * leverage) / price
            
            if BINANCE_TESTNET_FLAG and symbol in self.perps_tokens:
                precision = self.perps_tokens[symbol]
                order_size = math.floor(order_size * (10 ** precision)) / (10 ** precision)
            
            return order_size
        except Exception as e:
            print(f"Error calculating order size: {e}")
            return None
    
    def is_valid_symbol(self, symbol):
        """Check if symbol is valid for trading"""
        if BINANCE_TESTNET_FLAG:
            return symbol in self.perps_tokens
        else:
            return symbol in self.perps_tokens
    
    def get_symbol_precision(self, symbol):
        """Get precision for a specific symbol"""
        if BINANCE_TESTNET_FLAG:
            return self.perps_tokens.get(symbol)
        return None