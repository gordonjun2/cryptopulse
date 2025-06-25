import signal
import asyncio
import urllib3
from pyrogram import idle
from config import NUM_WORKERS
from market_cap_tracker import update_market_cap_loop
from modules.binance_trader import BinanceTrader
from modules.llm_client import LLMClient
from modules.data_manager import DataManager
from modules.message_processor import MessageProcessor
from modules.telegram_bots import TelegramBots

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


class CryptoPulseApp:
    """Main application class that orchestrates all components"""
    
    def __init__(self):
        print("Initializing CryptoPulse application components...\n")
        
        # Initialize core components
        self.binance_trader = BinanceTrader()
        self.llm_client = LLMClient()
        self.data_manager = DataManager()
        
        # Initialize message processor with dependencies
        self.message_processor = MessageProcessor(
            self.binance_trader,
            self.llm_client,
            self.data_manager
        )
        
        # Initialize Telegram bots
        self.telegram_bots = TelegramBots(
            self.message_processor,
            self.data_manager
        )
        
        # Update message processor with bot usage info
        self.message_processor.use_bot = self.telegram_bots.use_bot
        
        # Task tracking
        self.workers = []
        self.market_cap_task = None
        self.bot_task = None
        self.idle_task = None
        self.bot_commands_task = None
        self.tg_bot_task = None
        
        # Setup signal handlers
        self._setup_signal_handlers()
    
    def _setup_signal_handlers(self):
        """Setup signal handlers for graceful shutdown"""
        def signal_handler(sig, frame):
            print("Stopping the application...")
            if hasattr(self, 'telegram_bots') and self.telegram_bots.pyrogram_app:
                try:
                    # Use asyncio to stop the app
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.telegram_bots.stop_pyrogram())
                    else:
                        asyncio.run(self.telegram_bots.stop_pyrogram())
                except Exception as e:
                    print(f"Error stopping Pyrogram: {e}")
            print("The application has stopped. Exiting.")
            exit(0)

        signal.signal(signal.SIGINT, signal_handler)   # SIGINT for Ctrl + C
        signal.signal(signal.SIGTSTP, signal_handler)  # SIGTSTP for Ctrl + Z
    
    async def start_workers(self):
        """Start worker tasks for trading system"""
        try:
            self.workers = [
                asyncio.create_task(self.message_processor.trading_worker()) 
                for _ in range(NUM_WORKERS)
            ]
            print(f"Started {NUM_WORKERS} trading workers")
        except Exception as e:
            print(f"Failed to create worker tasks: {e}\n")
            raise
    
    async def start_market_cap_tracker(self):
        """Start market cap tracker update loop"""
        try:
            self.market_cap_task = asyncio.create_task(update_market_cap_loop())
            print("Started market cap tracker")
        except Exception as e:
            print(f"Failed to start market cap tracker: {e}\n")
            raise
    
    async def start_telegram_services(self):
        """Start all Telegram-related services"""
        try:
            # Start Pyrogram
            await self.telegram_bots.start_pyrogram()
            print("Started Pyrogram client")
            
            # Check bot membership
            await self.telegram_bots.check_bot_membership()
            
            # Get chat ID and name dictionary
            await self.telegram_bots.get_chat_id_name_dict()
            print("Retrieved chat ID and name dictionary")
            
            # Start bot tasks
            self.bot_task = asyncio.create_task(
                self.message_processor.message_processor_worker(
                    self.telegram_bots.get_bot_for_message_processor()
                )
            )
            self.idle_task = asyncio.create_task(idle())
            self.bot_commands_task = asyncio.create_task(self.telegram_bots.set_commands())
            self.tg_bot_task = await self.telegram_bots.start_aiogram_polling()
            
            print("Started all Telegram services")
            
        except Exception as e:
            print(f"Failed to start Telegram services: {e}\n")
            raise
    
    async def cleanup(self):
        """Clean up all tasks and resources"""
        print("Cancelling tasks...\n")
        
        # Cancel all tasks
        for w in self.workers:
            w.cancel()
        
        if self.market_cap_task:
            self.market_cap_task.cancel()
        if self.bot_task:
            self.bot_task.cancel()
        if self.idle_task:
            self.idle_task.cancel()
        if self.bot_commands_task:
            self.bot_commands_task.cancel()
        if self.tg_bot_task:
            self.tg_bot_task.cancel()

        # Wait for all tasks to complete
        try:
            all_tasks = [
                *self.workers,
                self.market_cap_task,
                self.bot_task,
                self.idle_task,
                self.bot_commands_task,
                self.tg_bot_task
            ]
            # Filter out None tasks
            all_tasks = [task for task in all_tasks if task is not None]
            
            await asyncio.gather(*all_tasks, return_exceptions=True)
        except Exception as e:
            print(f"Error during task cleanup: {e}\n")

        # Close bot sessions
        try:
            await self.telegram_bots.close_aiogram_session()
        except Exception as e:
            print(f"Error closing bot session: {e}\n")

        # Stop Pyrogram
        try:
            await self.telegram_bots.stop_pyrogram()
        except Exception as e:
            print(f"Error stopping Pyrogram: {e}\n")
    
    async def run(self):
        """Main application loop"""
        try:
            print("Starting bot and trade system...\n")

            # Start all services
            await self.start_workers()
            await self.start_market_cap_tracker()
            await self.start_telegram_services()
            
            print("All services started successfully. Running main loop...\n")

            # Main loop that waits for workers to finish their tasks
            try:
                while True:
                    await asyncio.sleep(0.5)  # Sleep to avoid busy-waiting
            except KeyboardInterrupt:
                print("\nShutting down gracefully...\n")
            except Exception as e:
                print(f"Error in main loop: {e}\n")
                
        except Exception as e:
            print(f"Critical error in main function: {e}\n")
        finally:
            await self.cleanup()


async def main():
    """Main entry point"""
    app = CryptoPulseApp()
    await app.run()


if __name__ == "__main__":
    # Start the application using Pyrogram's run method
    from pyrogram import Client
    from config import TELEGRAM_API_KEY, TELEGRAM_HASH
    
    # Create a temporary client just for running the main function
    temp_app = Client("temp_client", TELEGRAM_API_KEY, TELEGRAM_HASH)
    temp_app.run(main())