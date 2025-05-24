import sys
import os

# Add utils to sys.path to allow direct import of ConversationManager
# and to allow ConversationManager to import other utils like embeddings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))

# --- Mocking Setup ---

# Metadata for mock responses
masala_dosa_metadata = {
    "id": "1", "name": "Masala Dosa",
    "description": "A South Indian classic: a crispy, golden rice and lentil crepe filled with a savory spiced potato masala.",
    "region": "South India", "mood": "Comforting", "diet": "Vegetarian", "time": "Breakfast"
}
idli_metadata = {
    "id": "2", "name": "Idli",
    "description": "Soft, fluffy steamed rice cakes made from fermented rice and lentil batter.",
    "region": "Tamil Nadu", "mood": "Light", "diet": "Vegetarian", "time": "Breakfast"
}
# Hyderabadi Biryani metadata is not needed for this specific verification script.

# Store which items MockPineconeIndex should return for each turn
MOCK_PINECONE_RESULTS_TURN_1 = [masala_dosa_metadata, idli_metadata]
# For Turn 2, Pinecone will return an empty list for this verification
MOCK_PINECONE_RESULTS_TURN_2_EMPTY = [] 
current_turn_pinecone_results = []


def mock_get_embedding(text, model="models/embedding-001"):
    print(f"DEBUG_MOCK_VERIFY: get_embedding called for text: {text[:30]}...")
    return [0.01] * 768 

class MockPineconeIndex:
    def query(self, vector, top_k, include_metadata):
        global current_turn_pinecone_results
        print(f"DEBUG_MOCK_VERIFY: MockPineconeIndex.query called. Returning {len(current_turn_pinecone_results)} items.")
        return {
            'matches': [{'metadata': item, 'score': 0.9 - i*0.05} for i, item in enumerate(current_turn_pinecone_results)]
        }

def mock_get_index():
    print("DEBUG_MOCK_VERIFY: get_index called, returning MockPineconeIndex instance.")
    return MockPineconeIndex()

class MockGeminiResponse:
    def __init__(self, text):
        self.text = text
        self.candidates = [self] 
        self.prompt_feedback = None

class MockGenerativeModel:
    def __init__(self, model_name):
        self.model_name = model_name
        print(f"DEBUG_MOCK_VERIFY: MockGenerativeModel initialized with model: {model_name}")

    def generate_content(self, prompt_parts):
        if isinstance(prompt_parts, list):
            prompt_text = "".join([str(p) for p in prompt_parts])
        else:
            prompt_text = prompt_parts
        print(f"DEBUG_MOCK_VERIFY: MockGenerativeModel.generate_content called with prompt starting with: {prompt_text[:100]}...")
        return MockGeminiResponse("Dummy AI Response from MockGenerativeModel")

import utils.embeddings
import utils.pinecone_helper
import google.generativeai

utils.embeddings.get_embedding = mock_get_embedding
utils.pinecone_helper.get_index = mock_get_index
google.generativeai.GenerativeModel = MockGenerativeModel
google.generativeai.configure = lambda api_key: print("DEBUG_MOCK_VERIFY: google.generativeai.configure called.")

from utils.conversation_manager import ConversationManager
# --- End Mocking Setup ---


def simplified_get_recommendations(user_input, pinecone_results_for_this_turn):
    """Simplified recommendation logic for the test script."""
    global current_turn_pinecone_results
    current_turn_pinecone_results = pinecone_results_for_this_turn

    query_embedding = utils.embeddings.get_embedding(user_input)
    index = utils.pinecone_helper.get_index()
    results = index.query(vector=query_embedding, top_k=2, include_metadata=True) 
    
    retrieved_foods_metadata = []
    if results and results['matches']: # Check if matches is not empty
        retrieved_foods_metadata = [match['metadata'] for match in results['matches']]
    return retrieved_foods_metadata


# --- Test Script Logic ---
if __name__ == "__main__":
    conversation_manager = ConversationManager()
    print("\n--- Test Conversation Verify Script Start ---")

    # --- Simulate Turn 1 ---
    print("\n--- Turn 1 Start ---")
    user_input_1 = "I'm looking for something vegetarian."
    print(f"User Input 1: {user_input_1}")

    retrieved_foods_turn1 = simplified_get_recommendations(user_input_1, MOCK_PINECONE_RESULTS_TURN_1)
    
    mocked_ai_response_1 = "Okay, for vegetarian options, how about Masala Dosa or Idli? Both are great South Indian choices."
    print(f"Mocked AI Response 1: {mocked_ai_response_1}")

    conversation_manager.add_exchange(user_input_1, mocked_ai_response_1, retrieved_foods_turn1)
    print("DEBUG_VERIFY: Turn 1 exchange added to conversation manager.")
    print("--- Turn 1 End ---")

    # --- Simulate Turn 2 ---
    print("\n--- Turn 2 Start ---")
    user_input_2 = "Tell me more about the first one."
    print(f"User Input 2: {user_input_2}")

    # 1. Analyze user intent
    print("\nCalling analyze_user_intent...")
    intent_analysis_output = conversation_manager.analyze_user_intent(user_input_2)
    print("\nOutput of analyze_user_intent (Turn 2):")
    print(intent_analysis_output) # Print entire dictionary

    # Simulate new retrieval for Turn 2, which will be empty
    newly_retrieved_foods_turn2 = simplified_get_recommendations(user_input_2, MOCK_PINECONE_RESULTS_TURN_2_EMPTY)
    print(f"DEBUG_VERIFY: newly_retrieved_foods_turn2 for prompt generation: {newly_retrieved_foods_turn2}") # Should be []
    
    # 2. Generate contextual prompt
    print("\nCalling generate_contextual_prompt...")
    # Pass the empty list explicitly as per instruction
    contextual_prompt_turn2 = conversation_manager.generate_contextual_prompt(user_input_2, newly_retrieved_foods_turn2) 
    print("\nOutput of generate_contextual_prompt (Turn 2):")
    print(contextual_prompt_turn2)
    print("--- Turn 2 End ---")

    print("\n--- Test Conversation Verify Script End ---")
