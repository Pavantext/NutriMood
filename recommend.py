import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_index
import google.generativeai as genai

load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

user_input = input("What are you in the mood for? ")

# Embed the user input
query_embedding = get_embedding(user_input)

# Query Pinecone
index = get_index()
results = index.query(vector=query_embedding, top_k=5, include_metadata=True)
matches = results['matches']
retrieved_foods = [match['metadata'] for match in matches]

# Format context for Gemini
retrieved_text = "\n".join([
    f"{item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']})"
    for item in retrieved_foods
])

# Generate with Gemini
prompt = f"""
User query: {user_input}

Here are relevant food items from the database:
{retrieved_text}

Suggest the best option(s) in a friendly and intelligent way:
"""

model = genai.GenerativeModel('gemini-1.5-flash')
response = model.generate_content(prompt)

print("\n🍽️ Recommended Food:")
print(response.text)
