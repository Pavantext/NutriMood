import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))

# --- Mocking Setup ---
masala_dosa_metadata = {
    "id": "1", "name": "Masala Dosa",
    "description": "A South Indian classic: a crispy, golden rice and lentil crepe filled with a savory spiced potato masala.",
    "region": "South India", "mood": "Comforting", "diet": "Vegetarian", "time": "Breakfast"
}
hyderabadi_biryani_metadata = {
    "id": "3", "name": "Hyderabadi Biryani",
    "description": "A regal rice dish from Hyderabad, featuring fragrant basmati rice layered with marinated meat.",
    "region": "Telangana", "mood": "Celebratory", "diet": "Non-Vegetarian", "time": "Lunch"
}

STANDARD_MOCK_PINECONE_RESULTS = [masala_dosa_metadata, hyderabadi_biryani_metadata]
EMPTY_MOCK_PINECONE_RESULTS = []
current_pinecone_mock_data = STANDARD_MOCK_PINECONE_RESULTS

def mock_get_embedding(text, model="models/embedding-001"):
    # print(f"DEBUG_MOCK_VERIFY_EDGE: get_embedding called for text: {text[:30]}...") # Silenced for this test
    return [0.01] * 768

class MockPineconeIndex:
    def query(self, vector, top_k, include_metadata):
        global current_pinecone_mock_data
        # print(f"DEBUG_MOCK_VERIFY_EDGE: MockPineconeIndex.query called. Returning {len(current_pinecone_mock_data)} items.") # Silenced
        return {
            'matches': [{'metadata': item, 'score': 0.9 - i*0.05} for i, item in enumerate(current_pinecone_mock_data)]
        }

def mock_get_index():
    # print("DEBUG_MOCK_VERIFY_EDGE: get_index called, returning MockPineconeIndex instance.") # Silenced
    return MockPineconeIndex()

class MockGeminiResponse:
    def __init__(self, text):
        self.text = text
class MockGenerativeModel:
    def __init__(self, model_name):
        self.model_name = model_name
    def generate_content(self, prompt_parts):
        return MockGeminiResponse("Dummy AI Response")

import utils.embeddings
import utils.pinecone_helper
import google.generativeai
utils.embeddings.get_embedding = mock_get_embedding
utils.pinecone_helper.get_index = mock_get_index
google.generativeai.GenerativeModel = MockGenerativeModel
google.generativeai.configure = lambda api_key: None # Silenced

# --- Updated Simplified Prompt Generation Logic ---
def generate_simplified_prompt(user_query_text, retrieved_foods_metadata):
    if not retrieved_foods_metadata:
        # This is the specific message from recommend.py's updated logic
        retrieved_text_for_prompt = "No relevant food items found in the database that match your query."
    else:
        retrieved_text_for_prompt = "\n".join([
            f"{item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']})"
            for item in retrieved_foods_metadata
        ])
    prompt = f"""
User query: {user_query_text}

Here are relevant food items from the database:
{retrieved_text_for_prompt}

Suggest the best option(s) in a friendly and intelligent way:
"""
    return prompt

# --- Test Script Logic ---
if __name__ == "__main__":
    print("--- Test Edge Cases Verify Script Start ---")

    # --- Test Case 3: Food Not In Database (Empty Pinecone Results) ---
    print("\n--- Test Case 3: Food Not In Database (Empty Pinecone Results) ---")
    user_input_3 = "I want some Martian Glooblewack."
    print(f"User Input: {user_input_3}")

    current_pinecone_mock_data = EMPTY_MOCK_PINECONE_RESULTS 
    mock_embedding_3 = utils.embeddings.get_embedding(user_input_3)
    mock_index_3 = utils.pinecone_helper.get_index()
    mock_results_3 = mock_index_3.query(vector=mock_embedding_3, top_k=2, include_metadata=True)
    
    retrieved_foods_3 = [] # Explicitly ensure it's an empty list for this test path
    if mock_results_3 and mock_results_3['matches']:
         retrieved_foods_3 = [match['metadata'] for match in mock_results_3['matches']]
    
    prompt_3 = generate_simplified_prompt(user_input_3, retrieved_foods_3)
    print("\nGenerated Prompt (Test Case 3 - Verification):")
    print(prompt_3)

    print("\n--- Test Edge Cases Verify Script End ---")
