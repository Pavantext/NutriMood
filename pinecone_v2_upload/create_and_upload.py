import os
import json
import pinecone
from dotenv import load_dotenv
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.embeddings import get_embedding

load_dotenv()

PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
PINECONE_ENVIRONMENT = "us-east1-gcp"  # v2.x environment
INDEX_NAME = "niloufer-v2"
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'niloufer.json')

# 1. Initialize Pinecone v2.x
pinecone.init(api_key=PINECONE_API_KEY, environment=PINECONE_ENVIRONMENT)

# 2. Create index if not exists
if INDEX_NAME not in pinecone.list_indexes():
    pinecone.create_index(
        name=INDEX_NAME,
        dimension=768,
        metric="cosine"
    )
    print(f"Created index: {INDEX_NAME}")
else:
    print(f"Index already exists: {INDEX_NAME}")

index = pinecone.Index(INDEX_NAME)

# 3. Load data
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    food_items = json.load(f)

# 4. Prepare and upsert data in batches
batch_size = 100
vectors = []
for i, item in enumerate(food_items):
    # Use id as string
    item_id = str(item['id'])
    # Use name + description for embedding
    text = f"{item['name']}: {item['description']}"
    embedding = get_embedding(text)
    vectors.append((item_id, embedding, item))
    # Upsert in batches
    if len(vectors) == batch_size or i == len(food_items) - 1:
        index.upsert(vectors)
        print(f"Upserted {i+1}/{len(food_items)} items...")
        vectors = []

print("Upload complete!") 