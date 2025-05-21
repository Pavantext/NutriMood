import os
import pinecone
from dotenv import load_dotenv

load_dotenv()
pinecone.init(api_key=os.getenv("PINECONE_API_KEY"), environment=os.getenv("PINECONE_ENVIRONMENT"))
INDEX_NAME = "food-items"

def create_index():
    if INDEX_NAME not in pinecone.list_indexes():
        pinecone.create_index(name=INDEX_NAME, dimension=1536, metric="cosine")
    return pinecone.Index(INDEX_NAME)

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
