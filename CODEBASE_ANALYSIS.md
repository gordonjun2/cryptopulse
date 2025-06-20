# CryptoPulse: AI-Powered Cryptocurrency Trading Bot

## 🔍 System Overview

**CryptoPulse** is an advanced cryptocurrency trading bot that monitors multiple Telegram channels for crypto-related news, uses AI to analyze sentiment, and automatically executes trades on Binance based on that sentiment analysis. It's a sophisticated system that combines social media monitoring, natural language processing, and automated trading.

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Telegram      │    │   AI Sentiment  │    │   Binance       │
│   Monitoring    │───►│   Analysis      │───►│   Trading       │
│   (Pyrogram)    │    │   (Gemini/LLM)  │    │   (API)         │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                        │                        │
         ▼                        ▼                        ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Message       │    │   Response      │    │   Trade         │
│   Forwarding    │    │   Bot           │    │   Execution     │
│   (Queue)       │    │   (Aiogram)     │    │   (Workers)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 📋 Core Components

### 1. **Configuration System** (`config.py`)
- **API Integration**: Telegram, Binance, and AI service credentials
- **Channel Monitoring**: 15+ cryptocurrency news channels/groups
- **Trading Parameters**: 
  - Initial capital: $3,000
  - Leverage: 1x
  - Hold time: 5 minutes
  - Sentiment threshold: 50%
- **AI Prompt**: Sophisticated prompt for extracting coins and sentiment (-100% to +100%)

### 2. **Telegram Integration** (Triple-layer approach)
- **Pyrogram**: Real-time message monitoring from crypto channels
- **Telebot**: Synchronous bot operations (fallback)
- **Aiogram**: Asynchronous bot with commands (`/pnl`, `/stats`, `/help`)

### 3. **AI Sentiment Analysis**
- **Dual LLM Support**: Gemini 2.0 Flash (primary) or Bitdeer AI (backup)
- **Advanced Sentiment Analysis**: Considers direct crypto factors and macro/geopolitical events
- **Structured Output**: Extracts cryptocurrency tickers and sentiment percentage
- **Smart Parsing**: Handles complex market sentiment indicators

### 4. **Binance Trading Engine**
- **Futures Trading**: USDT perpetual contracts
- **Risk Management**: Quantity precision handling, leverage control
- **Error Handling**: Comprehensive retry logic with exponential backoff
- **Order Types**: Market buy/sell orders with immediate execution

### 5. **Asynchronous Processing**
- **Message Queue**: Processes messages asynchronously
- **Worker Pool**: 100 concurrent workers for trade execution
- **Symbol Tracking**: Prevents duplicate trades on same assets
- **Trade Lifecycle**: Complete buy → hold → sell automation

## 🔄 System Workflow

### Step-by-Step Process:

1. **Message Monitoring**
   - Monitors 15+ Telegram crypto channels
   - Captures text messages and media captions
   - Forwards relevant messages to main chat

2. **AI Processing**
   - Sends message content to AI (Gemini/Bitdeer)
   - Extracts cryptocurrency tickers (e.g., BTC, ETH, SOL)
   - Analyzes sentiment (-100% to +100%)
   - Considers both direct crypto news and macro factors

3. **Trading Decision**
   - If sentiment ≥ 50%: Execute LONG position
   - If sentiment ≤ -50%: Execute SHORT position
   - Validates ticker availability on Binance
   - Prevents duplicate trades on same asset

4. **Trade Execution**
   - Places market order with calculated quantity
   - Holds position for 5 minutes (configurable)
   - Automatically closes position
   - Calculates and reports P&L

5. **Results Tracking**
   - Stores P&L by Telegram channel
   - Maintains trading statistics
   - Provides bot commands for reporting

## 📊 Data Management

### Files Structure:
- `pnl_data.json`: P&L by Telegram channel
- `stats_data.json`: Trading statistics (max gain, drawdown, avg gain)
- `store.json`: Sample P&L data showing channel performance
- `private.ini`: Secure API credentials (not included)

### Bot Commands:
- `/pnl`: Display P&L breakdown by channel
- `/stats`: Show trading performance statistics  
- `/help`: List available commands

## 🛠️ Technical Features

### Advanced Trading Features:
- **Precision Handling**: Respects Binance quantity precision requirements
- **Leverage Management**: Automatic leverage setting per symbol
- **Price Monitoring**: Real-time price fetching with retry logic
- **Position Sizing**: Dynamic calculation based on capital and price

### Reliability Features:
- **Error Recovery**: Comprehensive exception handling
- **API Retry Logic**: Max 5 retries with 2-second delays
- **Graceful Shutdown**: Signal handling for clean exit
- **Testnet Support**: Safe testing environment option

### Performance Features:
- **Async Architecture**: Non-blocking operations throughout
- **Concurrent Workers**: 100 parallel trade processors
- **Memory Efficiency**: Queue-based message processing
- **Resource Management**: CPU-aware worker allocation

## 🔧 Testing Suite

### 1. **Binance Trading Test** (`test_binance_trade.py`)
- Isolated Binance API testing
- Simulates real trading scenarios
- Tests precision calculations and order execution

### 2. **AI Integration Test** (`test_llm_ai.py`)
- Tests Gemini API integration
- Validates sentiment analysis with sample data
- Ensures proper response parsing

### 3. **Data Persistence Test** (`test_save_load_json.py`)
- Tests JSON file operations
- Validates P&L data management
- Simulates bot command functionality

## 🚀 Deployment

### Production Setup:
- **Script**: `run_cryptopulse_script.sh` for production deployment
- **Virtual Environment**: Isolated Python environment
- **Background Execution**: Runs with `nohup` for persistence
- **Logging**: Comprehensive output logging
- **Process Management**: Proper process isolation with `disown`

## 📈 Performance Metrics

### From Sample Data (`store.json`):
- **Total Channels**: 10 active channels
- **Performance Range**: -$13,160 to +$12,126 per channel
- **Net Performance**: Mix of profitable and loss-making channels
- **Channel Diversity**: Multiple crypto news sources

## 🔐 Security Features

- **Credential Management**: Separate config file for sensitive data
- **API Security**: SSL verification disabled for testnet (configurable)
- **Access Control**: Bot membership verification
- **Error Isolation**: Prevents credential exposure in logs

## 🎯 Key Strengths

1. **Comprehensive Integration**: Seamlessly connects social media, AI, and trading
2. **Scalable Architecture**: Handles multiple channels and concurrent trades
3. **Robust Error Handling**: Extensive retry logic and graceful degradation
4. **Advanced AI Analysis**: Considers both direct and indirect market factors
5. **Real-time Processing**: Immediate response to market sentiment
6. **Performance Tracking**: Detailed P&L and statistics monitoring

## 🔮 Use Cases

- **Sentiment-Driven Trading**: Capitalize on news-driven market movements
- **Social Media Analytics**: Monitor crypto community sentiment
- **Automated Risk Management**: Consistent position sizing and timing
- **Multi-Source Intelligence**: Aggregate insights from multiple channels
- **Performance Analysis**: Track and optimize trading strategies

This system represents a sophisticated approach to cryptocurrency trading that leverages the power of social media sentiment, advanced AI analysis, and automated execution to potentially profit from market movements driven by news and community sentiment.