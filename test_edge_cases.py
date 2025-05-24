import sys
import os

# Add utils to sys.path to allow potential imports if any underlying util is called
# (though for this simplified script, it might not be strictly necessary)
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))

# --- Mocking Setup ---

# Metadata for mock responses
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

# Global variable to control Pinecone mock behavior per test case
current_pinecone_mock_data = STANDARD_MOCK_PINECONE_RESULTS

def mock_get_embedding(text, model="models/embedding-001"):
    print(f"DEBUG_MOCK: get_embedding called for text: {text[:30]}...")
    return [0.01] * 768 # Dummy embedding

class MockPineconeIndex:
    def query(self, vector, top_k, include_metadata):
        global current_pinecone_mock_data
        print(f"DEBUG_MOCK: MockPineconeIndex.query called. Returning {len(current_pinecone_mock_data)} items based on current test case.")
        return {
            'matches': [{'metadata': item, 'score': 0.9 - i*0.05} for i, item in enumerate(current_pinecone_mock_data)]
        }

def mock_get_index():
    print("DEBUG_MOCK: get_index called, returning MockPineconeIndex instance.")
    return MockPineconeIndex()

class MockGeminiResponse:
    def __init__(self, text):
        self.text = text

class MockGenerativeModel:
    def __init__(self, model_name):
        self.model_name = model_name
        print(f"DEBUG_MOCK: MockGenerativeModel initialized with model: {model_name}")

    def generate_content(self, prompt_parts):
        # This function won't be directly used for output, but good to have.
        print(f"DEBUG_MOCK: MockGenerativeModel.generate_content called. (Not used for prompt output in this test)")
        return MockGeminiResponse("Dummy AI Response from MockGenerativeModel")

# Apply mocks
# Assuming these modules might be imported by underlying code, even if not directly used by this script's main logic.
import utils.embeddings
import utils.pinecone_helper
import google.generativeai

utils.embeddings.get_embedding = mock_get_embedding
utils.pinecone_helper.get_index = mock_get_index # This mock is actually used
google.generativeai.GenerativeModel = MockGenerativeModel
google.generativeai.configure = lambda api_key: print("DEBUG_MOCK: google.generativeai.configure called.")

# --- Simplified Prompt Generation Logic ---

def generate_simplified_prompt(user_query_text, retrieved_foods_metadata):
    retrieved_text_for_prompt = "\n".join([
        f"{item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']})"
        for item in retrieved_foods_metadata
    ])
    if not retrieved_foods_metadata:
        retrieved_text_for_prompt = "No relevant food items found in the database."

    prompt = f"""
User query: {user_query_text}

Here are relevant food items from the database:
{retrieved_text_for_prompt}

Suggest the best option(s) in a friendly and intelligent way:
"""
    return prompt

# --- Test Script Logic ---
if __name__ == "__main__":
    print("--- Test Edge Cases Script Start ---")

    # --- Test Case 1: Irrelevant Query ---
    print("\n--- Test Case 1: Irrelevant Query ---")
    user_input_1 = "What's the weather like?"
    print(f"User Input: {user_input_1}")
    
    current_pinecone_mock_data = STANDARD_MOCK_PINECONE_RESULTS # Set pinecone mock for this case
    # Simulate embedding and query (though embedding isn't used by prompt directly)
    mock_embedding_1 = utils.embeddings.get_embedding(user_input_1)
    mock_index_1 = utils.pinecone_helper.get_index()
    mock_results_1 = mock_index_1.query(vector=mock_embedding_1, top_k=2, include_metadata=True)
    retrieved_foods_1 = [match['metadata'] for match in mock_results_1['matches']]
    
    prompt_1 = generate_simplified_prompt(user_input_1, retrieved_foods_1)
    print("\nGenerated Prompt (Test Case 1):")
    print(prompt_1)

    # --- Test Case 2: Misspelled Query ---
    print("\n--- Test Case 2: Misspelled Query ---")
    user_input_2 = "I wnt vegiterian food"
    print(f"User Input: {user_input_2}")

    current_pinecone_mock_data = STANDARD_MOCK_PINECONE_RESULTS # Set pinecone mock
    mock_embedding_2 = utils.embeddings.get_embedding(user_input_2)
    mock_index_2 = utils.pinecone_helper.get_index()
    mock_results_2 = mock_index_2.query(vector=mock_embedding_2, top_k=2, include_metadata=True)
    retrieved_foods_2 = [match['metadata'] for match in mock_results_2['matches']]

    prompt_2 = generate_simplified_prompt(user_input_2, retrieved_foods_2)
    print("\nGenerated Prompt (Test Case 2):")
    print(prompt_2)

    # --- Test Case 3: Food Not In Database ---
    print("\n--- Test Case 3: Food Not In Database (Empty Pinecone Results) ---")
    user_input_3 = "I want some Martian Glooblewack."
    print(f"User Input: {user_input_3}")

    current_pinecone_mock_data = EMPTY_MOCK_PINECONE_RESULTS # Set pinecone mock for empty results
    mock_embedding_3 = utils.embeddings.get_embedding(user_input_3)
    mock_index_3 = utils.pinecone_helper.get_index()
    mock_results_3 = mock_index_3.query(vector=mock_embedding_3, top_k=2, include_metadata=True)
    retrieved_foods_3 = [match['metadata'] for match in mock_results_3['matches']]
    
    prompt_3 = generate_simplified_prompt(user_input_3, retrieved_foods_3)
    print("\nGenerated Prompt (Test Case 3):")
    print(prompt_3)

    print("\n--- Test Edge Cases Script End ---")
