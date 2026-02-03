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
    if cfg.has_section('general'):
        general = dict(cfg.items('general'))
        ENV = general.get('env', 'dev')
    else:
        ENV = 'dev'
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
    if cfg.has_section('llm'):
        llm = dict(cfg.items('llm'))
        BITDEER_AI_BEARER_TOKEN = llm.get('bitdeer_ai_bearer_token', '')
        GEMINI_API_KEY = llm.get('gemini_api_key', '')
        OPENAI_API_KEY = llm.get('openai_api_key', '')
    else:
        BITDEER_AI_BEARER_TOKEN = ''
        GEMINI_API_KEY = ''
        OPENAI_API_KEY = ''
    if cfg.has_section('binance'):
        binance = dict(cfg.items('binance'))
        BINANCE_TESTNET_API_KEY = binance.get('binance_testnet_api_key', '')
        BINANCE_TESTNET_API_SECRET = binance.get('binance_testnet_api_secret',
                                                 '')
        BINANCE_MAINNET_API_KEY = binance.get('binance_mainnet_api_key', '')
        BINANCE_MAINNET_API_SECRET = binance.get('binance_mainnet_api_secret',
                                                 '')
        TOP_N_MARKETCAP = int(binance.get('top_n_marketcap', 10))
    else:
        BINANCE_TESTNET_API_KEY = ''
        BINANCE_TESTNET_API_SECRET = ''
        BINANCE_MAINNET_API_KEY = ''
        BINANCE_MAINNET_API_SECRET = ''
        TOP_N_MARKETCAP = 10
else:
    ENV = 'dev'
    TELEGRAM_API_KEY = 0
    TELEGRAM_HASH = ''
    TELEGRAM_BOT_TOKEN = ''
    MAIN_CHAT_ID = ''
    BITDEER_AI_BEARER_TOKEN = ''
    GEMINI_API_KEY = ''
    OPENAI_API_KEY = ''
    BINANCE_TESTNET_API_KEY = ''
    BINANCE_TESTNET_API_SECRET = ''
    BINANCE_MAINNET_API_KEY = ''
    BINANCE_MAINNET_API_SECRET = ''
    TOP_N_MARKETCAP = 10

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
    # -1002019095590,
    -1001651524056,
    # -1001556054753,
    -1002457358877,
    -1002080590083,
    # -1001138057410,
    -4698918931,
    -1002638442145,
    -4817612340,
    -1001947652656
    
]
'''
    ~~~Examples of Channels and their Chat IDs~~~
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
    PhoenixNews (Only Important): -1002080590083
    ⚡️Followin 闪电快讯｜聚合全球币圈大小事: -1001138057410
    Crypto Fake News: -4698918931
    Crypto Fake News Channel: -1002638442145
    Blanket Cave: -4817612340
'''

LLM_OPTION = "OPENAI"  # "BITDEER" or "GEMINI" or "OPENAI"
MAX_RETRIES = 5
RETRY_AFTER = 2
INITIAL_CAPITAL = 100  # USD
LEVERAGE = 1
HODL_TIME = 300  # seconds
TRADE_SENTIMENT_THRESHOLD = 50  # %
BINANCE_MAINNET_FLAG = True
NUM_WORKERS = 100
MARKETCAP_UPDATE_INTERVAL = 3600  # seconds
PROVIDER_MODEL = "openai/gpt-4.1-nano"

PROMPT = """
You are an assistant specialized in extracting cryptocurrencies mentioned in a given text and analyzing the sentiment for EACH coin individually.

Task:
Extract cryptocurrency tickers from the text. ALL tickers MUST be UPPERCASE (e.g., XRP, SOL, ADA, BTC, ETH).
If no cryptocurrency is mentioned, return an empty list for coins.

For EACH cryptocurrency mentioned, assign an individual Sentiment score ranging from -100.0 to 100.0:
- Negative values (-100.0 to -1.0) indicate Bearish sentiment.
- Positive values (1.0 to 100.0) indicate Bullish sentiment.
- A score of 0.0 means completely neutral sentiment.

IMPORTANT: Use CONTINUOUS and FLUID scoring with HUMAN JUDGMENT. Your scores should reflect nuanced sentiment intensity:
- Weak bearish: -5.0 to -25.0 (e.g., "concerns about", "slight downturn", "minor concerns")
- Moderate bearish: -26.0 to -50.0 (e.g., "decline", "pressure", "challenges", "headwinds")
- Strong bearish: -51.0 to -75.0 (e.g., "crash", "major sell-off", "fear", "regulatory crackdown")
- Extreme bearish: -76.0 to -100.0 (e.g., "collapse", "liquidation cascade", "rug pull", "depegging")
- Weak bullish: 5.0 to 25.0 (e.g., "hopeful", "optimistic", "slight uptick")
- Moderate bullish: 26.0 to 50.0 (e.g., "rally", "growth", "positive momentum")
- Strong bullish: 51.0 to 75.0 (e.g., "breakout", "strong adoption", "institutional buying")
- Extreme bullish: 76.0 to 100.0 (e.g., "parabolic", "ATH", "massive partnership", "nation-state adoption")

Consider both direct (crypto-specific) and indirect (macro/geopolitical) factors influencing sentiment:
Bearish Sentiment (use continuous -100.0 to -1.0 scale):
Look for context like "crash," "sell-off," "fear," "regulatory crackdown," "decline," "war," "uncertainty," 
"economic slowdown," "liquidity issues," "bank failures", "dump," "collapse," "downtrend," "bear market," "capitulation," "recession," "stagflation," 
"deflation," "bubble burst," "outflows," "sell pressure", "interest rate hike," "quantitative tightening," "high inflation," "debt crisis," 
"unemployment spike," "GDP contraction," "yield curve inversion", "rug pull," "liquidation cascade," "exchange insolvency," "hacked," "exploit," "FUD," 
"whale dumping," "token unlock," "sell wall," "depegging," "regulatory scrutiny", "sanctions," "trade war," "black swan event," "political instability," 
"supply chain disruptions," "energy crisis," "default risk", "fear index rising," "sentiment shift negative," "risk-off environment."

Bullish Sentiment (use continuous 1.0 to 100.0 scale):
Look for context like "rally," "bullish," "uptrend," "breakout," "growth," "institutional adoption," "rate cuts," 
"fiscal stimulus," "ETF approval", "deal", "partnership", "endorsement", "optimism", "interest", "price surge," "pump," "ATH (all-time high)," "parabolic," 
"breakout confirmation," "FOMO," "whale accumulation," "supply squeeze," "buy pressure," "strong support", "rate cut," "QE (quantitative easing)," 
"economic recovery," "disinflation," "GDP growth," "strong labor market", "token burn," "supply shock," "staking rewards," "mainnet launch," "protocol upgrade," 
"airdrops," "institutional investment," "on-chain activity spike," "exchange listing," "layer 2 adoption," "TVL (Total Value Locked) increase", 
"regulatory clarity," "mass adoption," "government support," "nation-state adoption," "market-friendly policies", "greed index rising," "retail interest," 
"positive funding rates," "risk-on environment." Someone famous liking a certain coin is also a bullish signal.

For each coin, only use one sentiment side (either positive or negative, never both). Provide a clear explanation for each coin's sentiment score.

Extract the following structured information:
- coins: A list of objects, where each object contains:
  - coin: The cryptocurrency ticker symbol in UPPERCASE (e.g., "BTC", "ETH", "SOL"). MUST be UPPERCASE.
  - sentiment: A float value from -100.0 to 100.0 for this specific coin (negative is bearish, positive is bullish).
  - explanation: A clear explanation describing the reasoning behind this coin's sentiment score.

Return an empty list for coins if no cryptocurrencies are mentioned.
"""
