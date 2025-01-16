import google.generativeai as genai
from dotenv import load_dotenv
import os


load_dotenv()

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

# Настройте свой API-ключ
genai.configure(api_key=GOOGLE_API_KEY)

# Получите список доступных моделей
models = genai.list_models()

for model in models:
    print(model.name)
    print(model.description)
    print("-" * 20)