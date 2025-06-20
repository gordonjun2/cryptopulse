# CryptoPulse 🚀

An AI-powered cryptocurrency trading bot that monitors Telegram channels, analyzes market sentiment using Large Language Models (LLMs), and executes automated trades on Binance based on sentiment analysis.

## 🌟 Features

- **Multi-Channel Monitoring**: Monitors multiple Telegram channels for cryptocurrency-related news and discussions
- **AI-Powered Sentiment Analysis**: Uses Gemini AI or Bitdeer AI APIs to analyze message sentiment and extract cryptocurrency mentions  
- **Automated Trading**: Executes long/short positions on Binance based on sentiment thresholds
- **Risk Management**: Configurable trading parameters (capital, leverage, hold time, sentiment threshold)
- **Real-time Updates**: Provides live trading updates and notifications via Telegram bot
- **P&L Tracking**: Comprehensive profit/loss tracking and statistics
- **Async Processing**: High-performance concurrent message and trade processing
- **Testnet Support**: Safe testing environment with Binance testnet integration
- **Queue-based Architecture**: Prevents duplicate trades and manages trading workflow

## 🛠️ Requirements

- Python 3.7+
- Virtual environment (recommended)
- Telegram API credentials
- Binance API access (testnet or live)
- AI API access (Gemini or Bitdeer AI)

## 📋 Dependencies

```bash
pip install -r requirements.txt
```

**Main Dependencies:**
- `pyrotgfork` - Telegram client for monitoring channels
- `aiogram` - Async Telegram bot framework
- `python-binance` - Binance API wrapper
- `aiohttp` - Async HTTP client for AI APIs
- `google-genai` - Google Gemini AI integration
- `prettytable` - Formatted output display

## ⚙️ Setup & Configuration

### 1. Clone and Setup Environment

```bash
git clone <repository-url>
cd cryptopulse
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Configuration File

Create a `private.ini` file based on `private_template.ini`:

```ini
[telegram]
TELEGRAM_API_KEY = your_telegram_api_id
TELEGRAM_HASH = your_telegram_api_hash
TELEGRAM_BOT_TOKEN = your_bot_token
MAIN_CHAT_ID = your_main_chat_id

[llm]
BITDEER_AI_BEARER_TOKEN = your_bitdeer_token
GEMINI_API_KEY = your_gemini_api_key

[binance]
BINANCE_TESTNET_API_KEY = your_testnet_api_key
BINANCE_TESTNET_API_SECRET = your_testnet_secret_key
```

### 3. API Setup Instructions

#### Telegram API
1. Visit https://my.telegram.org/apps
2. Create a new application to get `API_ID` and `API_HASH`
3. Create a bot via @BotFather to get `BOT_TOKEN`
4. Get your chat ID using @userinfobot

#### Binance API
1. Register at https://testnet.binance.vision/ (for testnet)
2. Create API keys with futures trading permissions
3. For live trading, use https://www.binance.com/

#### AI APIs
- **Gemini**: Get API key from https://aistudio.google.com/
- **Bitdeer AI**: Get bearer token from Bitdeer AI platform

## 🚀 Usage

### Quick Start

```bash
# Make the script executable
chmod +x run_cryptopulse_script.sh

# Run the bot
./run_cryptopulse_script.sh
```

Or run directly with Python:

```bash
python run_cryptopulse.py
```

### Configuration Parameters

Key parameters in `config.py`:

```python
LLM_OPTION = "GEMINI"  # "BITDEER" or "GEMINI"
INITIAL_CAPITAL = 3000  # USD
LEVERAGE = 1  # Trading leverage
HODL_TIME = 5 * 60  # Position hold time in seconds
TRADE_SENTIMENT_THRESHOLD = 50  # Minimum sentiment % for trading
BINANCE_TESTNET_FLAG = False  # Set to True for testnet
```

## 🤖 Bot Commands

The Telegram bot supports these commands:

- `/start` - Initialize the bot and display welcome message
- `/pnl` - Display profit/loss summary by chat
- `/stats` - Show overall trading statistics
- `/help` - Display available commands and usage info

## 📊 How It Works

1. **Message Monitoring**: Bot monitors configured Telegram channels for new messages
2. **Message Forwarding**: Relevant messages are forwarded to the main analysis chat
3. **AI Analysis**: Messages are sent to the configured LLM for sentiment analysis and coin extraction
4. **Trading Decision**: If sentiment exceeds threshold, trading signals are generated
5. **Order Execution**: Buy/sell orders are placed on Binance with configured parameters
6. **Position Management**: Positions are automatically closed after the specified hold time
7. **Results Tracking**: P&L is calculated and stored for performance analysis

## 📁 Project Structure

```
cryptopulse/
├── run_cryptopulse.py          # Main application
├── config.py                   # Configuration management
├── requirements.txt            # Python dependencies
├── private_template.ini        # Configuration template
├── run_cryptopulse_script.sh   # Launch script
├── test_*.py                   # Test files
├── store.json                  # Data storage
├── pnl_data.json              # P&L tracking (auto-generated)
├── stats_data.json            # Statistics (auto-generated)
└── README.md                   # Documentation
```

## 🔧 Monitored Channels

The bot monitors these types of crypto channels (configurable in `config.py`):
- Crypto news channels
- Trading signal groups  
- Market analysis channels
- Influencer channels
- Technical analysis groups

## ⚠️ Risk Management

- **Start with Testnet**: Always test with Binance testnet first
- **Small Position Sizes**: Use conservative capital allocation
- **Sentiment Threshold**: Set appropriate sentiment thresholds to filter noise
- **Hold Time**: Configure reasonable position hold times
- **Monitor Performance**: Regularly check P&L and adjust parameters

## 🐛 Troubleshooting

### Common Issues

1. **Bot not receiving messages**: Check Telegram API credentials and chat permissions
2. **Binance API errors**: Verify API keys and account permissions
3. **AI API failures**: Check API keys and rate limits
4. **Trading failures**: Ensure sufficient account balance and trading permissions

### Debugging

- Check logs in `script_cryptopulse_output.log`
- Enable verbose logging by modifying print statements
- Test individual components using the provided test files

## 📝 Testing

The project includes several test files:

- `test_binance_trade.py` - Test Binance trading functionality
- `test_llm_ai.py` - Test AI API integration
- `test_save_load_json.py` - Test data persistence

Run tests individually to verify functionality:

```bash
python test_binance_trade.py
python test_llm_ai.py
```

## 🚨 Disclaimer

**IMPORTANT**: This bot is for educational and research purposes only. Cryptocurrency trading involves significant financial risk.

- **No Financial Advice**: This software does not provide financial advice
- **Use at Your Own Risk**: You are responsible for all trading losses
- **Test First**: Always test with small amounts or testnet before live trading
- **Monitor Actively**: Automated trading requires active monitoring
- **Regulatory Compliance**: Ensure compliance with local regulations

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is provided as-is without warranty. Use responsibly and at your own risk.

## 🔮 Future Enhancements

- Multi-exchange support
- Advanced technical analysis integration
- Portfolio management features
- Web dashboard for monitoring
- Enhanced risk management tools
- Machine learning sentiment models

---

**Happy Trading! 🚀💎**

*Remember: Past performance does not guarantee future results. Always trade responsibly.*