import asyncio
import textwrap
import prettytable as pt
from aiogram import Bot, Dispatcher, Router
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand
from data_manager import DataManager
from config import TELEGRAM_BOT_TOKEN, MAIN_CHAT_ID


class TelegramBot:
    """Handles Telegram bot operations and commands"""
    
    def __init__(self):
        self.bot = Bot(
            token=TELEGRAM_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.router = Router()
        self.data_manager = DataManager()
        self.chat_id_name_dict = {}
        
        # Register handlers
        self._register_handlers()
        
        # Include router in dispatcher
        self.dp.include_router(self.router)
    
    def _register_handlers(self):
        """Register all command handlers"""
        self.router.message.register(self._cmd_start, CommandStart())
        self.router.message.register(self._cmd_pnl, Command("pnl"))
        self.router.message.register(self._cmd_stats, Command("stats"))
        self.router.message.register(self._cmd_help, Command("help"))
    
    async def setup(self):
        """Setup bot and set commands"""
        try:
            await self._set_commands()
            await self._get_chat_id_name_dict()
            await self._check_bot_membership()
            print("Telegram bot setup completed")
        except Exception as e:
            print(f"Error setting up Telegram bot: {e}")
    
    async def _set_commands(self):
        """Set bot commands in Telegram"""
        commands = [
            BotCommand(command="start", description="Start the bot"),
            BotCommand(command="pnl", description="Show P&L summary"),
            BotCommand(command="stats", description="Show trading statistics"),
            BotCommand(command="help", description="Show help information")
        ]
        
        try:
            await self.bot.set_my_commands(commands)
            print("Bot commands set successfully")
        except Exception as e:
            print(f"Error setting bot commands: {e}")
    
    async def _check_bot_membership(self):
        """Check if bot is member of main chat"""
        try:
            bot_info = await self.bot.get_me()
            bot_member = await self.bot.get_chat_member(MAIN_CHAT_ID, bot_info.id)
            
            if bot_member.status in ["administrator", "member"]:
                print(f"Bot is in main chat (status: {bot_member.status})")
                return True
            else:
                print(f"Bot is not in main chat (status: {bot_member.status})")
                return False
        except Exception as e:
            print(f"Error checking bot membership: {e}")
            return False
    
    async def _get_chat_id_name_dict(self):
        """Get chat ID to name mapping"""
        try:
            pnl_data = await self.data_manager.get_pnl_data()
            
            for chat_id in pnl_data.keys():
                try:
                    chat_info = await self.bot.get_chat(int(chat_id))
                    if hasattr(chat_info, 'title') and chat_info.title:
                        self.chat_id_name_dict[chat_id] = chat_info.title
                    elif hasattr(chat_info, 'username') and chat_info.username:
                        self.chat_id_name_dict[chat_id] = f"@{chat_info.username}"
                    else:
                        self.chat_id_name_dict[chat_id] = f"Chat {chat_id}"
                except Exception as e:
                    print(f"Error getting chat info for {chat_id}: {e}")
                    self.chat_id_name_dict[chat_id] = f"Chat {chat_id}"
            
            print(f"Loaded {len(self.chat_id_name_dict)} chat mappings")
        except Exception as e:
            print(f"Error loading chat mappings: {e}")
    
    async def _cmd_start(self, message: Message):
        """Handle /start command"""
        welcome_text = textwrap.dedent("""\
        🚀 **CryptoPulse Trading Bot** 🚀
        
        Welcome to the AI-powered crypto trading bot!
        
        **Available Commands:**
        /pnl - View P&L summary by chat
        /stats - View overall trading statistics  
        /help - Show this help message
        
        The bot monitors crypto channels and executes trades based on AI sentiment analysis.
        """)
        
        await message.reply(welcome_text)
    
    async def _cmd_pnl(self, message: Message, chat_name_width: int = 17, pnl_width: int = 12):
        """Handle /pnl command - show P&L summary"""
        try:
            pnl_data = await self.data_manager.get_pnl_data()
            
            if not pnl_data:
                await message.reply("📊 No P&L data available yet.")
                return
            
            # Create table
            table = pt.PrettyTable()
            table.field_names = ["Chat", "P&L (USD)"]
            table.align["Chat"] = "l"
            table.align["P&L (USD)"] = "r"
            
            # Add rows
            total_pnl = 0
            for chat_id, pnl in pnl_data.items():
                chat_name = self.chat_id_name_dict.get(chat_id, f"Chat {chat_id}")
                # Truncate long names
                if len(chat_name) > chat_name_width:
                    chat_name = chat_name[:chat_name_width-3] + "..."
                
                table.add_row([chat_name, f"${pnl:,.2f}"])
                total_pnl += pnl
            
            # Add total row
            table.add_row(["─" * chat_name_width, "─" * pnl_width])
            table.add_row(["TOTAL", f"${total_pnl:,.2f}"])
            
            response = f"📊 **P&L Summary by Chat**\n\n```\n{table}\n```"
            await message.reply(response)
            
        except Exception as e:
            print(f"Error in P&L command: {e}")
            await message.reply("❌ Error retrieving P&L data.")
    
    async def _cmd_stats(self, message: Message):
        """Handle /stats command - show trading statistics"""
        try:
            stats_data = await self.data_manager.get_stats_data()
            
            if not stats_data or stats_data.get("total_trades", 0) == 0:
                await message.reply("📈 No trading statistics available yet.")
                return
            
            # Create stats table
            table = pt.PrettyTable()
            table.field_names = ["Metric", "Value"]
            table.align["Metric"] = "l"
            table.align["Value"] = "r"
            
            # Add stats rows
            table.add_row(["Total Trades", f"{stats_data['total_trades']:,}"])
            table.add_row(["Winning Trades", f"{stats_data['winning_trades']:,}"])
            table.add_row(["Losing Trades", f"{stats_data['losing_trades']:,}"])
            table.add_row(["Win Rate", f"{stats_data['win_rate']:.1f}%"])
            table.add_row(["Total P&L", f"${stats_data['total_pnl']:,.2f}"])
            table.add_row(["Average P&L", f"${stats_data['average_pnl']:,.2f}"])
            
            response = f"📈 **Trading Statistics**\n\n```\n{table}\n```"
            await message.reply(response)
            
        except Exception as e:
            print(f"Error in stats command: {e}")
            await message.reply("❌ Error retrieving statistics.")
    
    async def _cmd_help(self, message: Message):
        """Handle /help command"""
        help_text = textwrap.dedent("""\
        🤖 **CryptoPulse Bot Help**
        
        **Commands:**
        /start - Initialize bot and show welcome message
        /pnl - Display profit/loss summary by chat
        /stats - Show overall trading statistics
        /help - Show this help message
        
        **How it works:**
        1. Bot monitors crypto Telegram channels
        2. AI analyzes message sentiment
        3. Trades are executed based on sentiment thresholds
        4. Results are tracked and reported
        
        **Note:** This bot is for educational purposes only. 
        Always trade responsibly and at your own risk.
        """)
        
        await message.reply(help_text)
    
    async def send_message(self, chat_id: int, text: str, reply_to_message_id: int = None):
        """Send a message to a specific chat"""
        try:
            await self.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_to_message_id=reply_to_message_id
            )
        except Exception as e:
            print(f"Error sending message to {chat_id}: {e}")
    
    async def start_polling(self):
        """Start bot polling"""
        try:
            print("Starting Telegram bot polling...")
            await self.dp.start_polling(self.bot)
        except Exception as e:
            print(f"Error in bot polling: {e}")
    
    async def stop(self):
        """Stop bot and cleanup"""
        try:
            await self.bot.session.close()
            print("Telegram bot stopped")
        except Exception as e:
            print(f"Error stopping bot: {e}")