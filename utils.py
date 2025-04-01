from pydantic_ai.models.gemini import GeminiModel
from dotenv import load_dotenv
import os

load_dotenv()

def get_model():
    llm = os.getenv('MODEL_CHOICE', 'gemini-2.0-flash')
    api_key= os.getenv('LLM_API_KEY', 'no-api-key-provided')

    return GeminiModel(
        llm,
        api_key=api_key
    )