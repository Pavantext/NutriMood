import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone client once
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "niloufer-menu"

def get_new_index():
    # Create index if not exists with serverless spec
    if INDEX_NAME not in pc.list_indexes().names():
        pc.create_index(
            name=INDEX_NAME,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
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