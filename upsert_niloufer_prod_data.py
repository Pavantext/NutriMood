import json
import os
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_new_index
from dotenv import load_dotenv

load_dotenv()

DATA_PATH = os.path.join('data', 'niloufer-prod-date.json')
INDEX_NAME = 'niloufer-prod-data'

def clean_metadata(item):
    # Remove keys with None values
    return {k: v for k, v in item.items() if v is not None}

# Load data
with open(DATA_PATH, 'r', encoding='utf-8') as f:
    food_data = json.load(f)

# Prepare Pinecone index
index = get_new_index(index_name=INDEX_NAME)

# Prepare vectors for upsert
vectors = []
for item in food_data:
    # Use only product name and description for embedding
    full_text = f"{item.get('ProductName', '')} {item.get('Description', '')}"
    embedding = get_embedding(full_text)
    vectors.append({
        "id": item["Id"],
        "values": embedding,
        "metadata": clean_metadata(item)
    })
    if len(vectors) % 50 == 0:
        print(f"Prepared {len(vectors)} vectors...")

# Upsert in batches
batch_size = 100
for i in range(0, len(vectors), batch_size):
    batch = vectors[i:i+batch_size]
    index.upsert(vectors=batch)
    print(f"Upserted batch {i//batch_size + 1} ({len(batch)} items)")

print(f"Done! Upserted {len(vectors)} items to Pinecone index '{INDEX_NAME}'.") 