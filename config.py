import os
from configparser import ConfigParser

root_dir = os.path.abspath(os.path.dirname(__file__))
config_file = os.path.join(root_dir, "private.ini")
cfg = ConfigParser()
cfg.read(config_file)

telegram = dict(cfg.items('telegram'))
TELEGRAM_API_KEY = int(telegram.get('telegram_api_key', 0))
TELEGRAM_HASH = telegram.get('telegram_hash', '')
TELEGRAM_BOT_TOKEN = telegram.get('telegram_bot_token', '')
MAIN_CHAT_ID = telegram.get('main_chat_id', '')

bitdeer = dict(cfg.items('bitdeer'))
BITDEER_AI_BEARER_TOKEN = bitdeer.get('bitdeer_ai_bearer_token', '')

CHAT_ID_LIST = [
    -1001488075213, -1002050038049, -1001369518127, -1001380328653,
    -1001683662707, -1001870913071, -1001219306781, -1001279597711,
    -1002233421487, -1002019095590, -4698918931
]
'''
    ~~~Examples of Channels and their Chat IDs~~~
    CRYPTO NEWS: -1001488075213
    ByteAI Crypto News: -1002050038049
    Crypto Mumbles: -1001369518127
    infinityhedge: -1001380328653
    Ian's Intel: -1001683662707
    Moonbags Personal Notes: -1001870913071
    Tree News: -1001219306781
    方程式新闻 BWEnews: -1001279597711
    RunnerXBT Insights: -1002233421487
    Anteater's Amazon: -1002019095590
    Crypto Fake News: -4698918931
'''

MAX_RETRIES = 3
RETRY_AFTER = 2

PROMPT = """
You are an assistant specialized in extracting cryptocurrencies mentioned in a given text and analyzing the sentiment to generate a Bullish or Bearish prediction. 
Your task is to extract any cryptocurrency tickers in uppercase (e.g., XRP, SOL, ADA) and assess the tone of the news article. 
Based on the tone, provide a prediction on the cryptocurrency using only one side of the scale, either Bullish or Bearish, with values ranging from 0% to 100%. 
The scale should be:
Bearish 100% (most negative sentiment)
Bearish 50% (moderately negative sentiment)
Bearish 0% (neutral sentiment, not negative or positive)
Bullish 0% (neutral sentiment, not negative or positive)
Bullish 50% (moderately positive sentiment)
Bullish 100% (most positive sentiment)
The value can be any number within the range (e.g., 37%, 68%, 12%, etc.) depending on the sentiment intensity.

Format your response strictly as: 
'Coins: [ticker 1], [ticker 2], ... 
Bullish: [percentage]% / Bearish: [percentage]%'

Example response: 
'Coins: XRP, ADA 
Bullish: 70%'
"""
