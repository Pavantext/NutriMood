# utils/pinecone_helper.py
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "food-items"

def get_index():
    return pc.Index(INDEX_NAME)

def upsert_data(index, food_data, get_embedding):
    vectors = []
    for item in food_data:
        full_text = f"{item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']})"
        embedding = get_embedding(full_text)
        vectors.append({
            "id": item["id"],
            "values": embedding,
            "metadata": item
        })
    index.upsert(vectors=vectors)
