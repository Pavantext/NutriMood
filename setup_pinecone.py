import json
from utils.embeddings import get_embedding
from utils.pinecone_helper import create_index, upsert_data

with open("data/food_items.json") as f:
    food_items = json.load(f)

index = create_index()
upsert_data(index, food_items, get_embedding)
print("✅ Pinecone index created and data inserted.")
