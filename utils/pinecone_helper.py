# utils/pinecone_helper.py
import os
# from pinecone import Pinecone # Mocked
from dotenv import load_dotenv

load_dotenv()

# # Initialize Pinecone client # Mocked
# pc = Pinecone(api_key=os.getenv("PINECONE_API_KEY")) # Mocked
# INDEX_NAME = "food-items" # Mocked

# Metadata for mock response (as obtained from food_items.json)
masala_dosa_metadata = {
    "id": "1", "name": "Masala Dosa",
    "description": "A South Indian classic: a crispy, golden rice and lentil crepe filled with a savory spiced potato masala. Served hot with coconut chutney and tangy sambar, it's a breakfast favorite across India.",
    "region": "South India", "mood": "Comforting",
    "diet": "Vegetarian", "time": "Breakfast", "price": "120rs",
    "ingredients": ["rice", "urad dal", "potatoes", "onions", "mustard seeds", "curry leaves", "turmeric", "salt", "oil"],
    "image_url": "https://www.shutterstock.com/shutterstock/photos/2497874061/display_1500/stock-photo-south-indian-food-set-dosa-with-tomato-chutney-also-called-nice-set-dosa-homemade-dosa-dhosa-2497874061.jpg"
}

hyderabadi_biryani_metadata = {
    "id": "3", "name": "Hyderabadi Biryani",
    "description": "A regal rice dish from Hyderabad, featuring fragrant basmati rice layered with marinated meat, caramelized onions, and aromatic spices. Slow-cooked to perfection, it's a celebration on a plate.",
    "region": "Telangana", "mood": "Celebratory",
    "diet": "Non-Vegetarian", "time": "Lunch", "price": "280rs",
    "ingredients": ["basmati rice", "mutton", "yogurt", "onions", "ginger", "garlic", "biryani masala", "saffron", "mint leaves", "ghee"],
    "image_url": "https://www.shutterstock.com/shutterstock/photos/2496776077/display_1500/stock-photo-hyderabadi-chicken-biryani-aromatic-and-rich-this-dish-combines-marinated-chicken-with-basmati-2496776077.jpg"
}

class MockPineconeIndex:
    def query(self, vector, top_k, include_metadata):
        print(f"DEBUG: MockPineconeIndex.query called with top_k={top_k}, include_metadata={include_metadata}")
        # Ignores the actual vector and returns a fixed response
        return {
            'matches': [
                {'metadata': masala_dosa_metadata, 'score': 0.9}, # Added dummy score
                {'metadata': hyderabadi_biryani_metadata, 'score': 0.85} # Added dummy score
            ]
        }
    # Mock upsert if it's called during normal operation, though not strictly needed for recommend.py
    def upsert(self, vectors):
        print(f"DEBUG: MockPineconeIndex.upsert called with {len(vectors)} vectors.")
        return {"upserted_count": len(vectors)}


def get_index():
    # return pc.Index(INDEX_NAME) # Mocked
    print("DEBUG: get_index called, returning MockPineconeIndex instance.")
    return MockPineconeIndex()

def upsert_data(index, food_data, get_embedding):
    # This function might still be called by other parts (e.g. create_index.py)
    # For recommend.py, it's not essential if get_index() is properly mocked.
    # However, to be safe, we can make it use the mock index's upsert.
    print("DEBUG: upsert_data called. Using mock index if provided.")
    vectors = []
    for item in food_data:
        full_text = f"{item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']})"
        embedding = get_embedding(full_text) # This will use the mocked get_embedding
        vectors.append({
            "id": item["id"],
            "values": embedding,
            "metadata": item
        })
    return index.upsert(vectors=vectors)
