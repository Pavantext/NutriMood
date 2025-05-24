import os
import argparse # Added argparse
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_index
import google.generativeai as genai

load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Set up command-line argument parsing
parser = argparse.ArgumentParser(description="Get food recommendations based on user input.")
parser.add_argument("user_query", type=str, help="Your food mood or query (e.g., 'something spicy for dinner')")
args = parser.parse_args()
user_input = args.user_query

# Embed the user input
query_embedding = get_embedding(user_input)

# Query Pinecone
index = get_index()
results = index.query(vector=query_embedding, top_k=5, include_metadata=True)
matches = results['matches']
retrieved_foods = [match['metadata'] for match in matches]

# Format context for Gemini
if not retrieved_foods: # retrieved_foods is the list from Pinecone
    retrieved_text = "No relevant food items found in the database that match your query."
else:
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

model = genai.GenerativeModel('gemini-1.5-flash') # This will use the dummy GOOGLE_API_KEY
print(f"DEBUG_PROMPT_START\n{prompt}\nDEBUG_PROMPT_END") # Added debug print
try:
    response = model.generate_content(prompt) # This will likely fail or use a dummy key
    actual_response_text = response.text
except Exception as e:
    print(f"DEBUG: model.generate_content(prompt) failed as expected: {e}")
    actual_response_text = "Error: Could not generate response from LLM."

print("\n🍽️ Recommended Food:")
# print(actual_response_text) # Print actual response or error
# Then print the dummy response as per instructions
print("\n\n🍽️ Recommended Food:\nDUMMY_AI_RESPONSE: This is a placeholder response. The actual LLM call was skipped/mocked.")
