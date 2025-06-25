import math
import time
import textwrap
import asyncio
import binance.client
from binance.exceptions import BinanceAPIException
from config import (BINANCE_TESTNET_API_KEY, BINANCE_TESTNET_API_SECRET, 
                    BINANCE_TESTNET_FLAG, MAX_RETRIES, RETRY_AFTER, 
                    INITIAL_CAPITAL, LEVERAGE, HODL_TIME, ENV)


class BinanceTrader:
    """Handles all Binance-related trading operations"""
    
    def __init__(self):
        self.client = None
        self.perps_tokens = {}
        self.processing_symbols = set()
        self.pending_symbols = set()
        self._initialize_client()

    def _initialize_client(self):
        """Initialize the Binance client"""
        try:
            if BINANCE_TESTNET_FLAG:
                self.client = binance.client.Client(BINANCE_TESTNET_API_KEY,
                                                   BINANCE_TESTNET_API_SECRET,
                                                   testnet=True)
            else:
                self.client = binance.client.Client()

            if ENV == 'dev':
                self.client.session.verify = False
                
            # Get symbol precision data
            if BINANCE_TESTNET_FLAG:
                self.perps_tokens = self.retry_api_call(self.get_symbol_precision)
                if not self.perps_tokens:
                    print("Failed to fetch quantity precision. Exiting...", flush=True)
                    return
            else:
                exchange_info = self.client.futures_exchange_info()
                self.perps_tokens = [
                    symbol['symbol'] for symbol in exchange_info['symbols']
                    if 'USDT' in symbol['symbol'] and symbol['status'] == 'TRADING'
                ]
                
        except BinanceAPIException as e:
            print(f"Failed to initialize Binance client: {e}", flush=True)
            self.client = None
        except Exception as e:
            print(f"Unexpected error initializing Binance client: {e}", flush=True)
            self.client = None

    def retry_api_call(self, func, *args, **kwargs):
        """Retry logic for API calls"""
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
        """Get symbol's quantity precision"""
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
        """Get ticker price with retry logic"""
        return self.retry_api_call(self.client.futures_symbol_ticker, symbol=symbol)

    def change_leverage(self, symbol, leverage):
        """Set leverage for a symbol"""
        self.retry_api_call(self.client.futures_change_leverage,
                           symbol=symbol,
                           leverage=leverage)

    def place_buy_order(self, symbol, order_size):
        """Place market buy order with retry logic"""
        return self.retry_api_call(self.client.futures_create_order,
                                  symbol=symbol,
                                  side="BUY",
                                  type="MARKET",
                                  quantity=order_size)

    def place_sell_order(self, symbol, order_size):
        """Place market sell order with retry logic"""
        return self.retry_api_call(self.client.futures_create_order,
                                  symbol=symbol,
                                  side="SELL",
                                  type="MARKET",
                                  quantity=order_size)

    async def execute_trade(self, symbol, direction, message, original_chat_id, 
                           update_pnl_callback, update_stats_callback):
        """Execute a complete trade operation"""
        try:
            base_symbol = symbol.replace("USDT", "")

            print(f"\nTrading Parameters:")
            print(f"----------------------------------", flush=True)
            print(f"Symbol: {symbol}", flush=True)

            if not self.client:
                error_msg = "Binance client is not initialized. Cannot execute trade."
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return

            if BINANCE_TESTNET_FLAG:
                selected_symbol_price_precision = self.perps_tokens.get(symbol)
                if not selected_symbol_price_precision:
                    error_msg = f"Could not find precision for symbol {symbol}"
                    print(error_msg, flush=True)
                    await message.reply_text(error_msg, quote=True)
                    return

                print(f"Symbol Quantity Precision: {selected_symbol_price_precision}", flush=True)
                ticker = self.get_price(symbol)
            else:
                try:
                    ticker = self.client.futures_symbol_ticker(symbol=symbol)
                except BinanceAPIException as e:
                    error_msg = f"Failed to get ticker price for {symbol}: {e}"
                    print(error_msg, flush=True)
                    await message.reply_text(error_msg, quote=True)
                    return
                except Exception as e:
                    error_msg = f"Unexpected error getting ticker price for {symbol}: {e}"
                    print(error_msg, flush=True)
                    await message.reply_text(error_msg, quote=True)
                    return

            if not ticker:
                error_msg = f"Failed to get ticker data for {symbol}"
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return

            print(f"Initial Capital (Margin): ${INITIAL_CAPITAL:,.2f}", flush=True)
            print(f"Leverage: {LEVERAGE}x", flush=True)
            print(f"Order Size (in USDT): ${INITIAL_CAPITAL * LEVERAGE:,.2f}", flush=True)

            try:
                price = float(ticker["price"])
            except (KeyError, ValueError) as e:
                error_msg = f"Invalid ticker data for {symbol}: {e}"
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return

            # Calculate order size
            try:
                order_size = (INITIAL_CAPITAL * LEVERAGE) / price
                if BINANCE_TESTNET_FLAG and selected_symbol_price_precision:
                    self.change_leverage(symbol, LEVERAGE)
                    order_size = math.floor(order_size * (10**selected_symbol_price_precision)) / (10**selected_symbol_price_precision)
                    corrected_initial_capital = (order_size * price) / LEVERAGE
                else:
                    corrected_initial_capital = INITIAL_CAPITAL
            except Exception as e:
                error_msg = f"Error calculating order size: {e}"
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return

            print(f"Order Size (in {base_symbol}): {order_size:,.2f}", flush=True)
            print(f"----------------------------------\n", flush=True)

            try:
                buy_order = self.place_buy_order(symbol, order_size) if BINANCE_TESTNET_FLAG else True

                if buy_order:
                    print(f"Market {'Buy' if direction == 'LONG' else 'Sell'} Order Executed: {order_size:,.2f} {base_symbol} at ${price}\n", flush=True)

                    await asyncio.sleep(HODL_TIME)
                    print(f"\nHodling for {HODL_TIME} seconds...\n", flush=True)

                    if BINANCE_TESTNET_FLAG:
                        ticker = self.get_price(symbol)
                    else:
                        ticker = self.client.futures_symbol_ticker(symbol=symbol)

                    if not ticker:
                        error_msg = f"Failed to get updated ticker data for {symbol}"
                        print(error_msg, flush=True)
                        await message.reply_text(error_msg, quote=True)
                        return

                    try:
                        new_price = float(ticker["price"])
                    except (KeyError, ValueError) as e:
                        error_msg = f"Invalid updated ticker data for {symbol}: {e}"
                        print(error_msg, flush=True)
                        await message.reply_text(error_msg, quote=True)
                        return

                    sell_order = self.place_sell_order(symbol, order_size) if BINANCE_TESTNET_FLAG else True

                    if sell_order:
                        print(f"Market {'Sell' if direction == 'LONG' else 'Buy'} Order Executed: {order_size:,.2f} {base_symbol} at ${new_price}\n", flush=True)

                        if direction == 'LONG':
                            final_capital = corrected_initial_capital + ((new_price - price) * order_size)
                        else:
                            final_capital = corrected_initial_capital - ((new_price - price) * order_size)
                        percentage_gained = ((final_capital - corrected_initial_capital) / corrected_initial_capital) * 100

                        print(f"Trade Summary:", flush=True)
                        print(f"----------------------------------", flush=True)
                        print(f"Before Capital: ${corrected_initial_capital:.2f}", flush=True)
                        print(f"After Capital: ${final_capital:.2f} ({percentage_gained:+.2f}%)", flush=True)
                        print(f"----------------------------------\n", flush=True)

                        content = textwrap.dedent(f"""\
                        🚀 **{direction} Trade Simulated** 🚀

                        **Trading Parameters:**
                        __Symbol:__ {symbol}  
                        __Order Size (in USDT):__ ${INITIAL_CAPITAL * LEVERAGE:,.2f}  

                        **Market {'Buy' if direction == 'LONG' else 'Sell'} Order Executed:**  
                        {order_size:,.2f} {base_symbol} at ${price}  

                        **Market {'Sell' if direction == 'LONG' else 'Buy'} Order Executed {HODL_TIME / 60:,.2f} mins later:**  
                        {order_size:,.2f} {base_symbol} at ${new_price}  

                        **Trade Summary:**  
                        __Before Capital:__ ${corrected_initial_capital:.2f}  
                        __After Capital:__ ${final_capital:.2f} ({percentage_gained:+.2f}%)
                        """)

                        pnl = final_capital - corrected_initial_capital

                        new_pnl_data = {str(original_chat_id): pnl}

                        await update_pnl_callback(new_pnl_data)
                        await update_stats_callback(pnl)
                        await message.reply_text(content, quote=True)
                    else:
                        error_msg = f"Sell order failed for {symbol}"
                        print(error_msg + "\n", flush=True)
                        await message.reply_text(error_msg, quote=True)
                else:
                    error_msg = f"Buy order failed for {symbol}"
                    print(error_msg + "\n", flush=True)
                    await message.reply_text(error_msg, quote=True)
            except Exception as e:
                error_msg = f"Unexpected error during trade execution: {e}"
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
        except Exception as e:
            error_msg = f"Critical error in trade function: {e}"
            print(error_msg, flush=True)
            await message.reply_text(error_msg, quote=True)
        finally:
            self.processing_symbols.remove(symbol)

    def is_symbol_available(self, symbol):
        """Check if symbol is available for trading"""
        return symbol in self.perps_tokens
        
    def add_pending_symbol(self, symbol):
        """Add symbol to pending set"""
        self.pending_symbols.add(symbol)
        
    def remove_pending_symbol(self, symbol):
        """Remove symbol from pending set"""
        self.pending_symbols.remove(symbol)
        
    def add_processing_symbol(self, symbol):
        """Add symbol to processing set"""
        self.processing_symbols.add(symbol)
        
    def is_symbol_in_queue_or_processing(self, symbol):
        """Check if symbol is already in queue or being processed"""
        return symbol in self.processing_symbols or symbol in self.pending_symbols