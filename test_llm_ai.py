# import requests
# import json

# response = requests.post(
#     url="https://openrouter.ai/api/v1/chat/completions",
#     headers={
#         "Authorization":
#         "Bearer ",
#         "Content-Type": "application/json",
#     },
#     data=json.dumps({
#         "model":
#         "deepseek/deepseek-chat-v3-0324:free",
#         "messages": [{
#             "role": "user",
#             "content": "What is the meaning of life?"
#         }],
#     }),
#     verify=False)

# # Print the response with verbose-like information
# print(f"Response status code: {response.status_code}")
# print("Response headers:")
# for header, value in response.headers.items():
#     print(f"  {header}: {value}")
# print("\nResponse content:")
# print(response.text)

# from google import genai
# from google.genai import types
import requests
import json
from config import PROMPT, GEMINI_API_KEY

# client = genai.Client(api_key=GEMINI_API_KEY)

example_message = """
BWENEWS: Hut 8 Launches 'American Bitcoin' Mining Firm Backed by Eric Trump and Donald Trump Jr. https://www.globenewswire.com/news-release/2025/03/31/3052066/0/en/Hut-8-and-Eric-Trump-Launch-American-Bitcoin-to-Set-a-New-Standard-in-Bitcoin-Mining.html

方程式新闻: Hut 8 推出由埃里克·特朗普和小唐纳德·特朗普支持的“美国比特币”挖矿公司

$BTC
————————————
2025-03-31 17:28:28
"""

# response = client.models.generate_content(model="gemini-2.0-flash",
#                                           config=types.GenerateContentConfig(
#                                               system_instruction=PROMPT,
#                                               max_output_tokens=1024,
#                                               temperature=0.1),
#                                           contents=example_message)
# print(response.text)

url = 'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key=' + GEMINI_API_KEY
headers = {'Content-Type': 'application/json'}

data = {
    "contents": [{
        "parts": [{
            "text": example_message
        }]
    }],
    "system_instruction": {
        "parts": [{
            "text": PROMPT
        }]
    },
    "generationConfig": {
        "temperature": 0.1,
        "maxOutputTokens": 1024,
    }
}

# Send the POST request
response = requests.post(url, headers=headers, data=json.dumps(data))

# Check the response
if response.status_code == 200:
    print(response.json())
else:
    print(f"Error: {response.status_code}")
    print(response.text)
