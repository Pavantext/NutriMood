import json
from utils.embeddings import get_embedding
from utils.pinecone_helper_new import get_new_index, upsert_data

# Load sample data
with open('data/niloufer_menu.json') as f:
    food_data = json.load(f)

# Get index and upsert data
index = get_new_index()
upsert_data(index, food_data, get_embedding)
print(f"Inserted {len(food_data)} items into Pinecone")