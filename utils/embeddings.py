# utils/embeddings.py
# import google.generativeai as genai # Mocked
import os
from dotenv import load_dotenv

load_dotenv()
# genai.configure(api_key=os.getenv("GOOGLE_API_KEY")) # Mocked

def get_embedding(text):
    # result = genai.embed_content( # Mocked
    #     model="models/embedding-001",
    #     content=text,
    #     task_type="retrieval_document",
    #     title="Food item embedding"
    # )
    # return result['embedding'] # Mocked
    print(f"DEBUG: get_embedding called for text: {text[:50]}...")
    return [0.1] * 768 # Dummy embedding of size 768
