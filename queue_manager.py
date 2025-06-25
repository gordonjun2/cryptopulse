import asyncio
from config import NUM_WORKERS


class QueueManager:
    def __init__(self, trading_engine):
        self.trading_engine = trading_engine
        self.symbol_queue = asyncio.Queue()
        self.processing_symbols = set()
        self.pending_symbols = set()

    def is_symbol_queued_or_processing(self, symbol):
        """Check if symbol is already in queue or being processed"""
        return symbol in self.processing_symbols or symbol in self.pending_symbols

    async def add_to_queue(self, symbol, direction, message, original_chat_id):
        """Add symbol to trading queue"""
        self.pending_symbols.add(symbol)
        await self.symbol_queue.put((symbol, direction, message, original_chat_id))

    async def worker(self):
        """Worker function to process tickers from the queue asynchronously"""
        while True:
            item = await self.symbol_queue.get()
            if item is None:
                break

            symbol, direction, message, original_chat_id = item

            # Remove from pending and add to processing
            self.pending_symbols.remove(symbol)
            self.processing_symbols.add(symbol)

            try:
                # Execute trade
                await self.trading_engine.execute_trade(symbol, direction, message, original_chat_id)
            finally:
                self.processing_symbols.remove(symbol)
                self.symbol_queue.task_done()

    def create_workers(self):
        """Create worker tasks"""
        return [asyncio.create_task(self.worker()) for _ in range(NUM_WORKERS)]

    def stop_workers(self, workers):
        """Stop all worker tasks"""
        for worker in workers:
            worker.cancel()