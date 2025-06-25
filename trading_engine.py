import asyncio
import math
import textwrap
from config import (INITIAL_CAPITAL, LEVERAGE, HODL_TIME, BINANCE_TESTNET_FLAG)


class TradingEngine:
    def __init__(self, binance_client, data_storage):
        self.binance_client = binance_client
        self.data_storage = data_storage

    async def execute_trade(self, symbol, direction, message, original_chat_id):
        """Execute a trading operation for a single ticker"""
        try:
            base_symbol = symbol.replace("USDT", "")

            print(f"\nTrading Parameters:")
            print(f"----------------------------------", flush=True)
            print(f"Symbol: {symbol}", flush=True)

            if not self.binance_client.is_client_available():
                error_msg = "Binance client is not initialized. Cannot execute trade."
                print(error_msg, flush=True)
                await message.reply_text(error_msg, quote=True)
                return

            if BINANCE_TESTNET_FLAG:
                selected_symbol_price_precision = self.binance_client.get_symbol_precision_value(symbol)
                if not selected_symbol_price_precision:
                    error_msg = f"Could not find precision for symbol {symbol}"
                    print(error_msg, flush=True)
                    await message.reply_text(error_msg, quote=True)
                    return

                print(
                    f"Symbol Quantity Precision: {selected_symbol_price_precision}",
                    flush=True)
                # Get ticker's price
                ticker = self.binance_client.get_price(symbol)
            else:
                try:
                    # Get ticker's price
                    ticker = self.binance_client.client.futures_symbol_ticker(symbol=symbol)
                except Exception as e:
                    error_msg = f"Failed to get ticker price for {symbol}: {e}"
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
            print(f"Order Size (in USDT): ${INITIAL_CAPITAL * LEVERAGE:,.2f}",
                  flush=True)

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
                    self.binance_client.change_leverage(symbol, LEVERAGE)
                    order_size = math.floor(
                        order_size * (10**selected_symbol_price_precision)) / (
                            10**selected_symbol_price_precision)
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
                buy_order = self.binance_client.place_buy_order(
                    symbol, order_size) if BINANCE_TESTNET_FLAG else True

                if buy_order:
                    print(
                        f"Market {'Buy' if direction == 'LONG' else 'Sell'} Order Executed: {order_size:,.2f} {base_symbol} at ${price}\n",
                        flush=True)

                    await asyncio.sleep(HODL_TIME)  # Simulate holding the position
                    print(f"\nHodling for {HODL_TIME} seconds...\n", flush=True)

                    if BINANCE_TESTNET_FLAG:
                        ticker = self.binance_client.get_price(symbol)
                    else:
                        ticker = self.binance_client.client.futures_symbol_ticker(symbol=symbol)

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

                    sell_order = self.binance_client.place_sell_order(
                        symbol, order_size) if BINANCE_TESTNET_FLAG else True

                    if sell_order:
                        print(
                            f"Market {'Sell' if direction == 'LONG' else 'Buy'} Order Executed: {order_size:,.2f} {base_symbol} at ${new_price}\n",
                            flush=True)

                        if direction == 'LONG':
                            final_capital = corrected_initial_capital + (
                                (new_price - price) * order_size)
                        else:
                            final_capital = corrected_initial_capital - (
                                (new_price - price) * order_size)
                        percentage_gained = (
                            (final_capital - corrected_initial_capital) /
                            corrected_initial_capital) * 100

                        print(f"Trade Summary:", flush=True)
                        print(f"----------------------------------", flush=True)
                        print(f"Before Capital: ${corrected_initial_capital:.2f}",
                              flush=True)
                        print(
                            f"After Capital: ${final_capital:.2f} ({percentage_gained:+.2f}%)",
                            flush=True)
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

                        await self.data_storage.update_pnl_data(new_pnl_data)
                        await self.data_storage.update_stats_data(pnl)
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