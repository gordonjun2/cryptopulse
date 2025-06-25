import os
import signal
import asyncio
import urllib3
from pyrogram import Client, utils, filters, idle

# Import our new modular components
from binance_client import BinanceClient
from data_storage import DataStorage
from llm_service import LLMService
from trading_engine import TradingEngine
from message_processor import MessageProcessor
from queue_manager import QueueManager
from telegram_handlers import TelegramHandlers
from market_cap_tracker import update_market_cap_loop

# Import configuration
from config import (TELEGRAM_API_KEY, TELEGRAM_HASH, CHAT_ID_LIST,
                    MAIN_CHAT_ID, NUM_WORKERS)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


# Pyrogram Monkey Patch (same as original)
def get_peer_type(peer_id: int) -> str:
    peer_id_str = str(peer_id)
    if not peer_id_str.startswith("-"):
        return "user"
    elif peer_id_str.startswith("-100"):
        return "channel"
    else:
        return "chat"


utils.get_peer_type = get_peer_type


class CryptoPulseApp:
    def __init__(self):
        # Initialize all components
        self.binance_client = BinanceClient()
        self.data_storage = DataStorage()
        self.llm_service = LLMService()
        self.trading_engine = TradingEngine(self.binance_client, self.data_storage)
        self.queue_manager = QueueManager(self.trading_engine)
        self.telegram_handlers = TelegramHandlers(self.data_storage)
        
        # Initialize Pyrogram client
        self.app = Client("text_listener", TELEGRAM_API_KEY, TELEGRAM_HASH)
        
        # Initialize message processor
        self.message_processor = MessageProcessor(
            self.llm_service,
            self.binance_client,
            self.queue_manager,
            self.telegram_handlers.is_bot_available()
        )
        
        # Set bot reference in message processor
        if self.telegram_handlers.is_bot_available():
            self.message_processor.set_bot(self.telegram_handlers.get_bot())
        
        # Initialize message queue
        self.message_queue = asyncio.Queue()
        
        # Chat ID and name dictionary
        self.chat_id_name_dict = {}
        
        # Task references
        self.workers = []
        self.market_cap_task = None
        self.bot_task = None
        self.idle_task = None
        self.bot_commands_task = None
        self.tg_bot_task = None

    async def get_chat_id_name_dict(self):
        """Get chat ID and name dictionary"""
        for chat_id in CHAT_ID_LIST:
            chat_id_str = str(chat_id)
            try:
                chat_info = await self.app.get_chat(chat_id)
                self.chat_id_name_dict[chat_id_str] = chat_info.title
            except Exception as e:
                self.chat_id_name_dict[chat_id_str] = chat_id_str
                continue
        
        # Set the dictionary in telegram handlers
        self.telegram_handlers.set_chat_id_name_dict(self.chat_id_name_dict)

    async def message_handler(self, client, message):
        """Handler for incoming messages"""
        if message.text or message.caption:
            print(f"Message received from chat: {message.chat.id}")
            print(f"Message: {message.text or message.caption}")

            try:
                forwarded_message = await message.forward(chat_id=int(MAIN_CHAT_ID))
                print("Message forwarded successfully.\n")

                await self.message_queue.put((forwarded_message, message))
            except Exception as e:
                print(f"Error forwarding message: {e}\n")

    def signal_handler(self, sig, frame):
        """Signal handler for graceful shutdown"""
        print("Stopping the application...")
        if self.app:
            self.app.stop()
        print("The application has stopped. Exiting.")
        exit(0)

    async def start_app(self):
        """Start the application"""
        try:
            print("Starting bot and trade system...\n")

            # Start Pyrogram
            try:
                await self.app.start()
            except Exception as e:
                print(f"Failed to start Pyrogram client: {e}\n")
                return False

            # Check if the bot is a member of the chat
            try:
                if not await self.telegram_handlers.check_bot_membership():
                    await self.app.stop()
                    return False
            except Exception as e:
                print(f"Failed to check bot membership: {e}\n")
                await self.app.stop()
                return False

            if not asyncio.get_event_loop().is_running():
                print("Event loop is not running\n")
                await self.app.stop()
                return False

            # Get chat ID and chat name dictionary
            try:
                await self.get_chat_id_name_dict()
            except Exception as e:
                print(f"Failed to get chat ID and name dictionary: {e}\n")
                await self.app.stop()
                return False

            return True

        except Exception as e:
            print(f"Critical error starting app: {e}\n")
            try:
                await self.app.stop()
            except:
                pass
            return False

    async def start_tasks(self):
        """Start all background tasks"""
        try:
            # Start worker tasks for trading system
            self.workers = self.queue_manager.create_workers()
            print(f"Started {len(self.workers)} worker tasks")

            # Start market cap tracker update loop
            self.market_cap_task = asyncio.create_task(update_market_cap_loop())
            print("Started market cap tracker")

            # Start message processor
            self.bot_task = asyncio.create_task(
                self.message_processor.run_processor(self.message_queue)
            )
            print("Started message processor")

            # Start Pyrogram idle task
            self.idle_task = asyncio.create_task(idle())
            print("Started Pyrogram idle task")

            # Set bot commands
            self.bot_commands_task = asyncio.create_task(
                self.telegram_handlers.set_commands()
            )
            print("Started bot commands setup")

            # Start Telegram bot polling
            self.tg_bot_task = asyncio.create_task(
                self.telegram_handlers.get_dispatcher().start_polling(
                    self.telegram_handlers.get_bot()
                )
            )
            print("Started Telegram bot polling")

            return True

        except Exception as e:
            print(f"Failed to start background tasks: {e}\n")
            await self.cleanup_tasks()
            return False

    async def cleanup_tasks(self):
        """Cleanup all tasks"""
        print("Cancelling tasks...\n")
        
        # Cancel worker tasks
        if self.workers:
            for worker in self.workers:
                worker.cancel()

        # Cancel other tasks
        tasks_to_cancel = [
            self.market_cap_task,
            self.bot_task,
            self.idle_task,
            self.bot_commands_task,
            self.tg_bot_task
        ]
        
        for task in tasks_to_cancel:
            if task:
                task.cancel()

        # Wait for all tasks to complete
        try:
            all_tasks = self.workers + [t for t in tasks_to_cancel if t]
            if all_tasks:
                await asyncio.gather(*all_tasks, return_exceptions=True)
        except Exception as e:
            print(f"Error during task cleanup: {e}\n")

        # Close bot session
        await self.telegram_handlers.close_bot()

        # Stop Pyrogram
        try:
            await self.app.stop()
        except Exception as e:
            print(f"Error stopping Pyrogram: {e}\n")

    async def run_main_loop(self):
        """Run the main application loop"""
        try:
            # Main loop that waits for workers to finish their tasks
            while True:
                await asyncio.sleep(0.5)  # Sleep to avoid busy-waiting
        except KeyboardInterrupt:
            print("\nShutting down gracefully...\n")
        except Exception as e:
            print(f"Error in main loop: {e}\n")

    async def main(self):
        """Main application entry point"""
        try:
            # Setup signal handlers
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTSTP, self.signal_handler)

            # Start the application
            if not await self.start_app():
                return

            # Register message handler
            @self.app.on_message(filters.chat(CHAT_ID_LIST))
            async def message_handler_wrapper(client, message):
                await self.message_handler(client, message)

            # Start background tasks
            if not await self.start_tasks():
                return

            # Run main loop
            await self.run_main_loop()

        except Exception as e:
            print(f"Critical error in main function: {e}\n")
        finally:
            await self.cleanup_tasks()


def main():
    """Entry point"""
    app = CryptoPulseApp()
    app.app.run(app.main())