from flask import Flask, render_template, request, jsonify
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_index
from utils.conversation_manager import ConversationManager
import google.generativeai as genai
import time
import re

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Flask app
app = Flask(__name__)

# Initialize conversation manager
conversation_manager = ConversationManager()

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/reset_chat', methods=['POST'])
def reset_chat():
    try:
        global conversation_manager
        conversation_manager = ConversationManager()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_input = data['message']
        chat_history = data.get('history', [])

        # Embed the user input
        query_embedding = get_embedding(user_input)

        # Query Pinecone
        index = get_index()
        results = index.query(vector=query_embedding, top_k=10, include_metadata=True)  # Increased to 10 for better options
        matches = results['matches']
        retrieved_foods = [match['metadata'] for match in matches]

        # Analyze user intent and generate response
        intent_analysis = conversation_manager.analyze_user_intent(user_input)
        
        # Generate contextual prompt
        prompt = f"""
You are a helpful food recommendation assistant. The user's query is: "{user_input}"

Here are relevant food items from the database:
{format_foods_for_prompt(retrieved_foods)}

Important instructions:
1. ONLY mention and recommend foods that match the user's dietary preferences and needs
2. DO NOT mention or discuss unsuitable foods (e.g., don't mention meat dishes to vegetarians)
3. Focus on directly answering the user's query with appropriate recommendations
4. End your response with a list of recommended food IDs in this exact format: [RECOMMENDED_FOODS:id1,id2,id3]
   - No spaces after commas
   - Only include IDs of foods you actually recommend
   - Make sure these IDs match your recommendations in the text

Example format:
"Here are some great vegetarian options... [RECOMMENDED_FOODS:41,1,16]"
"""

        # Generate with Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Clean response and extract recommended food IDs
        cleaned_response, recommended_food_ids = parse_response_and_recommendations(response.text)

        # Filter retrieved foods based on recommendations
        filtered_foods = [
            food for food in retrieved_foods 
            if str(food.get('id', '')) in recommended_food_ids
        ] if recommended_food_ids else []

        # Add the exchange to conversation history
        conversation_manager.add_exchange(user_input, cleaned_response, filtered_foods)

        return jsonify({
            'response': cleaned_response,
            'foods': filtered_foods
        })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your request.',
            'details': str(e)
        }), 500

def format_foods_for_prompt(foods):
    """Format food items for the prompt with dietary information"""
    formatted_foods = []
    for food in foods:
        dietary_info = []
        if food.get('is_veg', False):
            dietary_info.append('vegetarian')
        if food.get('is_vegan', False):
            dietary_info.append('vegan')
        
        dietary_str = f" ({', '.join(dietary_info)})" if dietary_info else ""
        formatted_foods.append(
            f"ID {food.get('id', 'N/A')}: {food.get('name', '')}{dietary_str} - {food.get('description', '')}"
        )
    return "\n".join(formatted_foods)

def parse_response_and_recommendations(text):
    """Extract the response and recommended food IDs"""
    # Look for the recommendations list at the end of the response
    match = re.search(r'\[RECOMMENDED_FOODS:([^\]]+)\]', text)
    
    if match:
        # Get the recommended food IDs and clean them
        food_ids_str = match.group(1).strip()
        recommended_food_ids = [id.strip() for id in food_ids_str.split(',')]
        
        # Remove the recommendations list from the response
        cleaned_response = text[:match.start()].strip()
    else:
        cleaned_response = text.strip()
        recommended_food_ids = []
    
    return clean_response(cleaned_response), recommended_food_ids

@app.route('/order', methods=['POST'])
def order():
    try:
        data = request.json
        food_id = data['food_id']
        quantity = data['quantity']

        # Here you would typically implement order processing logic
        # For now, we'll just return success
        return jsonify({
            'success': True,
            'message': f'Successfully ordered {quantity} item(s)'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def clean_response(text):
    """Clean the response text from any unwanted elements"""
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove any div elements
    text = re.sub(r'div', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

if __name__ == '__main__':
    app.run(debug=True) 