import os
import json
import weaviate
from dotenv import load_dotenv
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from utils.embeddings import get_embedding
from weaviate.classes.config import DataType
from weaviate.classes.data import DataObject

load_dotenv()

WEAVIATE_URL = os.getenv("WEAVIATE_URL")
WEAVIATE_API_KEY = os.getenv("WEAVIATE_API_KEY")
DATA_FILE = os.path.join(os.path.dirname(__file__), '..', 'data', 'niloufer.json')
CLASS_NAME = "FoodItem"

# 1. Connect to Weaviate Cloud (v4.x, new method)
client = weaviate.connect_to_weaviate_cloud(
    cluster_url=WEAVIATE_URL,
    auth_credentials=weaviate.auth.AuthApiKey(WEAVIATE_API_KEY)
)

# 2. Create schema if not exists
if not client.collections.exists(CLASS_NAME):
    client.collections.create(
        name=CLASS_NAME,
        vectorizer_config=weaviate.classes.config.Configure.Vectorizer.none(),
        properties=[
            weaviate.classes.config.Property(name="name", data_type=DataType.TEXT),
            weaviate.classes.config.Property(name="description", data_type=DataType.TEXT),
            weaviate.classes.config.Property(name="metadata", data_type=DataType.TEXT),
        ]
    )
    print(f"Created schema for {CLASS_NAME}")
else:
    print(f"Schema for {CLASS_NAME} already exists")

# 3. Upload data
with open(DATA_FILE, 'r', encoding='utf-8') as f:
    food_items = json.load(f)

batch_size = 100
objects = []
for i, item in enumerate(food_items):
    text = f"{item['name']}: {item['description']}"
    embedding = get_embedding(text)
    obj = DataObject(
        properties={
            "name": item['name'],
            "description": item['description'],
            "metadata": json.dumps(item),
        },
        vector=embedding
    )
    objects.append(obj)
    if len(objects) == batch_size or i == len(food_items) - 1:
        client.collections.get(CLASS_NAME).data.insert_many(objects)
        print(f"Uploaded {i+1}/{len(food_items)} items...")
        objects = []

print("Upload complete!")

# 4. Example retrieval (semantic search)
query = "healthy vegetarian snack with protein"
query_vector = get_embedding(query)
results = client.collections.get(CLASS_NAME).query.near_vector(
    near_vector=query_vector,
    limit=5,
    return_properties=["name", "description", "metadata"]
)
print("\nTop 5 results for query:", query)
for res in results.objects:
    print(f"- {res.properties['name']}: {res.properties['description']}")

client.close() 