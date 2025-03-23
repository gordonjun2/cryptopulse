import os
from configparser import ConfigParser

root_dir = os.path.abspath(os.path.dirname(__file__))
config_file = os.path.join(root_dir, "private.ini")
cfg = ConfigParser()

if os.path.exists(config_file):
    cfg.read(config_file)
else:
    cfg = None

if cfg:
    if cfg.has_section('telegram'):
        telegram = dict(cfg.items('telegram'))
        TELEGRAM_API_KEY = int(telegram.get('telegram_api_key', 0))
        TELEGRAM_HASH = telegram.get('telegram_hash', '')
        TELEGRAM_BOT_TOKEN = telegram.get('telegram_bot_token', '')
        MAIN_CHAT_ID = telegram.get('main_chat_id', '')
    else:
        TELEGRAM_API_KEY = 0
        TELEGRAM_HASH = ''
        TELEGRAM_BOT_TOKEN = ''
        MAIN_CHAT_ID = ''
    if cfg.has_section('bitdeer'):
        bitdeer = dict(cfg.items('bitdeer'))
        BITDEER_AI_BEARER_TOKEN = bitdeer.get('bitdeer_ai_bearer_token', '')
    else:
        BITDEER_AI_BEARER_TOKEN = ''
    if cfg.has_section('binance'):
        binance = dict(cfg.items('binance'))
        BINANCE_TESTNET_API_KEY = binance.get('binance_testnet_api_key', '')
        BINANCE_TESTNET_API_SECRET = binance.get('binance_testnet_api_secret',
                                                 '')
    else:
        BINANCE_TESTNET_API_KEY = ''
        BINANCE_TESTNET_API_SECRET = ''
else:
    TELEGRAM_API_KEY = 0
    TELEGRAM_HASH = ''
    TELEGRAM_BOT_TOKEN = ''
    MAIN_CHAT_ID = ''
    BITDEER_AI_BEARER_TOKEN = ''
    BINANCE_TESTNET_API_KEY = ''
    BINANCE_TESTNET_API_SECRET = ''

CHAT_ID_LIST = [
    # -1001488075213,
    -1002050038049,
    # -1001369518127,
    -1001380328653,
    # -1001683662707,
    # -1001870913071,
    -1001219306781,
    -1001279597711,
    # -1002233421487,
    -1002019095590,
    -1001651524056,
    # -1001556054753,
    -1002457358877,
    -4698918931,
    -1002638442145,
]
'''
    ~~~Examples of Channels and their Chat IDs~~~
    CRYPTO NEWS: -1001488075213
    ByteAI Crypto News: -1002050038049
    Crypto Mumbles: -1001369518127
    infinityhedge: -1001380328653
    Ian's Intel: -1001683662707
    # Moonbags Personal Notes: -1001870913071
    Tree News: -1001219306781
    方程式新闻 BWEnews: -1001279597711
    RunnerXBT Insights: -1002233421487
    Anteater's Amazon: -1002019095590
    Zoomer News: -1001651524056
    Watcher Guru: -1001556054753
    Solid Intel: -1002457358877
    Crypto Fake News: -4698918931
    Crypto Fake News Channel: -1002638442145
'''

MAX_RETRIES = 5
RETRY_AFTER = 2
INITIAL_CAPITAL = 3000  # USD
LEVERAGE = 1
HODL_TIME = 5 * 60  # seconds
TRADE_SENTIMENT_THRESHOLD = 50  # %
BINANCE_TESTNET_FLAG = False

PROMPT = """
You are an assistant specialized in extracting cryptocurrencies mentioned in a given text and analyzing the sentiment to generate a prediction.

Task:
Extract cryptocurrency tickers (e.g., XRP, SOL, ADA) from the text.
If no cryptocurrency is mentioned, return "Coins: N/A".
Assess the sentiment of the text and assign a Sentiment score ranging from -100% to 100% (The sentiment score will be a continuous value between 
-100 and 100, not just fixed steps.):
Negative values (-100% to -1%) indicate Bearish sentiment.
Positive values (1% to 100%) indicate Bullish sentiment.
A score of 0% means completely neutral sentiment.
Consider both direct (crypto-specific) and indirect (macro/geopolitical) factors influencing sentiment:
Bearish Sentiment (-100% to -1%): Look for context like "crash," "sell-off," "fear," "regulatory crackdown," "decline," "war," "uncertainty," "economic slowdown," "liquidity issues," "bank failures."
Bullish Sentiment (1% to 100%): Look for context like "rally," "bullish," "uptrend," "breakout," "growth," "institutional adoption," "rate cuts," "fiscal stimulus," "ETF approval", "deal", "partnership."
Only use one sentiment side per response (either positive or negative, never both). Provide a clear explanation for the assigned sentiment score.
STRICTLY format the response as follows (DO NOT DEVIATE and Coins and Sentiment are on separate lines without extra space. Sentiment and Explanation are separated by one blank line.):
Coins: [ticker 1], [ticker 2], ...
Sentiment: [percentage]%

Explanation: [explanation]
"""
