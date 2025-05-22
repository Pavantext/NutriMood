# create_index.py
import os
from pinecone import Pinecone
from dotenv import load_dotenv

load_dotenv()

# Initialize Pinecone client
pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))

INDEX_NAME = "food-items"

# Create the index with dimension 768 (matching Gemini embeddings)
pc.create_index(
    name=INDEX_NAME,
    dimension=768,  # This matches the dimension of Gemini embeddings
    metric="cosine",
    spec=dict(
        serverless=dict(
            cloud="aws",
            region="us-east-1"
        )
    )
)

print(f"✅ Successfully created index '{INDEX_NAME}' with dimension 768") 