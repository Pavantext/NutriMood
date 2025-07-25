import os
from pinecone import Pinecone, ServerlessSpec
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone client once
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
INDEX_NAME = "niloufer-menu"

def get_new_index(index_name=None):
    if index_name is None:
        index_name = INDEX_NAME
    # Create index if not exists with serverless spec
    if index_name not in pc.list_indexes().names():
        pc.create_index(
            name=index_name,
            dimension=768,
            metric="cosine",
            spec=ServerlessSpec(
                cloud='aws',
                region='us-east-1'
            )
        )
    return pc.Index(index_name)

def upsert_data(index, food_data, get_embedding):
    vectors = []
    for item in food_data:
        full_text = f"name: {item['name']}, description: {item['description']}, region: {item['region']}, mood: {item['mood']}, time: {item['time']}, diet: {item['diet']}, category: {item['category']}, spice_level: {item['spice_level']}, health_benefits: {item['health_benefits']}, region: {item['region']}, ingredients: {item['ingredients']}, sides: {item['sides']}, cooking_method: {item['cooking_method']}, dietary_tags: {item['dietary_tags']}, price: {item['price']}, calories: {item['calories']})"
        embedding = get_embedding(full_text)
        vectors.append({
            "id": item["id"],
            "values": embedding,
            "metadata": item
        })
    index.upsert(vectors=vectors)

def delete_all_data(index):
    """
    Delete all vectors from the Pinecone index.
    Args:
        index: Pinecone index instance
    """
    index.delete(delete_all=True)
    print(f"All data deleted from index: {INDEX_NAME}")