import sys
import os

# Add utils to sys.path to allow direct import of ConversationManager
# and to allow ConversationManager to import other utils like embeddings
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '.')))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'utils')))

# --- Mocking Setup ---

# Metadata for mock responses (simplified for brevity in the script, full data available)
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
hyderabadi_biryani_metadata = {
    "id": "3", "name": "Hyderabadi Biryani",
    "description": "A regal rice dish from Hyderabad, featuring fragrant basmati rice layered with marinated meat.",
    "region": "Telangana", "mood": "Celebratory", "diet": "Non-Vegetarian", "time": "Lunch"
}

# Store which items MockPineconeIndex should return for each turn
MOCK_PINECONE_RESULTS_TURN_1 = [masala_dosa_metadata, idli_metadata]
MOCK_PINECONE_RESULTS_TURN_2 = [masala_dosa_metadata, hyderabadi_biryani_metadata] # As per instruction
current_turn_pinecone_results = []


def mock_get_embedding(text, model="models/embedding-001"):
    print(f"DEBUG_MOCK: get_embedding called for text: {text[:30]}...")
    return [0.01] * 768 # Dummy embedding

class MockPineconeIndex:
    def query(self, vector, top_k, include_metadata):
        global current_turn_pinecone_results
        print(f"DEBUG_MOCK: MockPineconeIndex.query called. Returning {len(current_turn_pinecone_results)} items.")
        # Ignores the actual vector and returns a fixed response based on current_turn_pinecone_results
        return {
            'matches': [{'metadata': item, 'score': 0.9 - i*0.05} for i, item in enumerate(current_turn_pinecone_results)]
        }

def mock_get_index():
    print("DEBUG_MOCK: get_index called, returning MockPineconeIndex instance.")
    return MockPineconeIndex()

class MockGeminiResponse:
    def __init__(self, text):
        self.text = text
        self.candidates = [self] # To mimic the actual response structure if needed
        self.prompt_feedback = None

class MockGenerativeModel:
    def __init__(self, model_name):
        self.model_name = model_name
        print(f"DEBUG_MOCK: MockGenerativeModel initialized with model: {model_name}")

    def generate_content(self, prompt_parts):
        # If prompt_parts is a list, join it to simulate actual prompt generation
        if isinstance(prompt_parts, list):
            prompt_text = "".join([str(p) for p in prompt_parts])
        else:
            prompt_text = prompt_parts

        print(f"DEBUG_MOCK: MockGenerativeModel.generate_content called with prompt starting with: {prompt_text[:100]}...")
        # The actual AI response for Turn 1 is hardcoded in the test script logic
        # This mock is primarily to prevent errors for the *second* call if it happens.
        return MockGeminiResponse("Dummy AI Response from MockGenerativeModel")

# Apply mocks by replacing functions in their original modules
# This is safer than monkeypatching sys.modules if modules were already loaded.
import utils.embeddings
import utils.pinecone_helper
import google.generativeai

utils.embeddings.get_embedding = mock_get_embedding
utils.pinecone_helper.get_index = mock_get_index
google.generativeai.GenerativeModel = MockGenerativeModel
google.generativeai.configure = lambda api_key: print("DEBUG_MOCK: google.generativeai.configure called.")


# Must import ConversationManager after mocks are set up if it imports the mocked functions at module level
from utils.conversation_manager import ConversationManager
# --- End Mocking Setup ---


def simplified_get_recommendations(user_input, conversation_manager, pinecone_results_for_this_turn):
    """Simplified recommendation logic for the test script."""
    global current_turn_pinecone_results
    current_turn_pinecone_results = pinecone_results_for_this_turn

    # 1. Embed the user input (mocked)
    query_embedding = utils.embeddings.get_embedding(user_input)

    # 2. Query Pinecone (mocked)
    index = utils.pinecone_helper.get_index()
    results = index.query(vector=query_embedding, top_k=2, include_metadata=True) # top_k=2 for this test
    
    retrieved_foods_metadata = [match['metadata'] for match in results['matches']]

    # 3. Generate contextual prompt (using ConversationManager or simpler logic for test)
    # For this test, we'll use a simplified prompt string similar to recommend.py for Turn 1's AI response generation.
    # For Turn 2, we will specifically test conversation_manager.generate_contextual_prompt
    
    # This is where the actual AI call would happen.
    # For Turn 1, we hardcode the AI response. For Turn 2, this function won't be called directly for AI response.
    
    return retrieved_foods_metadata


# --- Test Script Logic ---
if __name__ == "__main__":
    # Initialize ConversationManager
    conversation_manager = ConversationManager() # Corrected: No arguments
    print("\n--- Test Conversation Script Start ---")

    # --- Simulate Turn 1 ---
    print("\n--- Turn 1 Start ---")
    user_input_1 = "I'm looking for something vegetarian."
    print(f"User Input 1: {user_input_1}")

    # Simulate retrieving 'Masala Dosa' and 'Idli' for Turn 1
    # The simplified_get_recommendations will set current_turn_pinecone_results
    retrieved_foods_turn1 = simplified_get_recommendations(user_input_1, conversation_manager, MOCK_PINECONE_RESULTS_TURN_1)
    
    # Mocked AI Response for Turn 1
    mocked_ai_response_1 = "Okay, for vegetarian options, how about Masala Dosa or Idli? Both are great South Indian choices."
    print(f"Mocked AI Response 1: {mocked_ai_response_1}")

    conversation_manager.add_exchange(user_input_1, mocked_ai_response_1, retrieved_foods_turn1)
    print("DEBUG: Turn 1 exchange added to conversation manager.")
    print("--- Turn 1 End ---")

    # --- Simulate Turn 2 ---
    print("\n--- Turn 2 Start ---")
    user_input_2 = "Tell me more about the first one."
    print(f"User Input 2: {user_input_2}")

    # 1. Analyze user intent
    print("\nCalling analyze_user_intent...")
    intent_analysis_output = conversation_manager.analyze_user_intent(user_input_2)
    print("\nOutput of analyze_user_intent:")
    print(intent_analysis_output) # This is one of the required outputs

    # For Turn 2, Pinecone "retrieves" 'Masala Dosa' and 'Hyderabadi Biryani'
    # We need to simulate the embedding and query part for the *new* user input of Turn 2
    # to get the "newly_retrieved_foods_turn2"
    # The simplified_get_recommendations will set current_turn_pinecone_results
    newly_retrieved_foods_turn2 = simplified_get_recommendations(user_input_2, conversation_manager, MOCK_PINECONE_RESULTS_TURN_2)
    
    # 2. Generate contextual prompt
    print("\nCalling generate_contextual_prompt...")
    contextual_prompt_turn2 = conversation_manager.generate_contextual_prompt(user_input_2, newly_retrieved_foods_turn2)
    print("\nOutput of generate_contextual_prompt (Turn 2):")
    print(contextual_prompt_turn2) # This is the other required output
    print("--- Turn 2 End ---")

    print("\n--- Test Conversation Script End ---")
