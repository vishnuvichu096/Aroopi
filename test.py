import os
import requests
from dotenv import load_dotenv

load_dotenv()
key = os.getenv('GEMINI_API_KEY').strip().strip('\'').strip('\"')

url = f'https://generativelanguage.googleapis.com/v1beta/models?key={key}'
response = requests.get(url)

try:
    data = response.json()
    if 'error' in data:
        print("API ERROR:", data)
    else:
        models = [m['name'] for m in data.get('models', []) if 'generateContent' in m.get('supportedGenerationMethods', [])]
        print(models)
except Exception as e:
    print("Error:", e, response.text)
