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
        results = index.query(vector=query_embedding, top_k=5, include_metadata=True)
        matches = results['matches']
        retrieved_foods = [match['metadata'] for match in matches]

        # Analyze user intent and generate response
        intent_analysis = conversation_manager.analyze_user_intent(user_input)
        
        # If it's a follow-up question, adjust the search results
        if intent_analysis['is_followup']:
            recent_foods = intent_analysis['recent_foods']
            # Combine recent and new foods, removing duplicates
            all_foods = {food['id']: food for food in retrieved_foods + recent_foods}
            retrieved_foods = list(all_foods.values())

        # Generate contextual prompt
        prompt = conversation_manager.generate_contextual_prompt(user_input, retrieved_foods)

        # Generate with Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Clean response
        cleaned_response = clean_response(response.text)

        # Add the exchange to conversation history
        conversation_manager.add_exchange(user_input, cleaned_response, retrieved_foods)

        return jsonify({
            'response': cleaned_response,
            'foods': retrieved_foods
        })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'error': 'An error occurred while processing your request.',
            'details': str(e)
        }), 500

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