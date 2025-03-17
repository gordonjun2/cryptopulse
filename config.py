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
