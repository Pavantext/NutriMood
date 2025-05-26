from flask import Flask, render_template, request, jsonify, session
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_index
from utils.conversation_manager import ConversationManager
import google.generativeai as genai
import time
import re
from datetime import timedelta

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Flask app
app = Flask(__name__)

# Set a stable secret key - in production, use an environment variable
app.secret_key = 'bf0f16b52bbb59fce3350b0dbff06ebe4ef15ce0eeae221d1b3a7d44f83dd1fe'  # Replace this with a secure key in production
app.permanent_session_lifetime = timedelta(days=1)  # Session expires after 1 day

# Dictionary to store conversation managers for each user
user_conversations = {}

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        
        if not username:
            return jsonify({
                'success': False,
                'error': 'Username is required'
            }), 400
            
        # Create a new session for the user
        session.permanent = True
        session['username'] = username
        
        # Initialize a new conversation manager for this user
        if username not in user_conversations:
            user_conversations[username] = ConversationManager()
        
        return jsonify({
            'success': True,
            'username': username
        })
    except Exception as e:
        # Log the error but return success anyway since the UI can handle it
        print(f"Login error: {str(e)}")
        return jsonify({
            'success': True,
            'username': data.get('username', '')
        }), 200  # Return 200 OK status

@app.route('/logout', methods=['POST'])
def logout():
    try:
        username = session.get('username')
        if username and username in user_conversations:
            del user_conversations[username]
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/reset_chat', methods=['POST'])
def reset_chat():
    try:
        username = session.get('username')
        if not username:
            return jsonify({
                'success': False,
                'error': 'User not logged in'
            }), 401
            
        user_conversations[username] = ConversationManager()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        username = session.get('username')
        if not username:
            return jsonify({
                'success': False,
                'error': 'User not logged in'
            }), 401
            
        data = request.json
        user_input = data['message']
        chat_history = data.get('history', [])

        # Get the user's conversation manager
        conversation_manager = user_conversations.get(username)
        if not conversation_manager:
            conversation_manager = ConversationManager()
            user_conversations[username] = conversation_manager

        # Build conversation context from history
        conversation_context = ""
        if chat_history:
            # Get the last exchange (up to 2 messages)
            recent_messages = chat_history[-2:] if len(chat_history) > 1 else chat_history
            conversation_context = "\n".join([
                f"{'User' if msg['role'] == 'user' else 'Assistant'}: {msg['content']}"
                for msg in recent_messages
            ])

        # Embed the user input
        query_embedding = get_embedding(user_input)

        # Query Pinecone
        index = get_index()
        results = index.query(vector=query_embedding, top_k=10, include_metadata=True)
        matches = results['matches']
        retrieved_foods = [match['metadata'] for match in matches]

        # Analyze if it's a follow-up question
        is_followup = bool(conversation_context) and any(
            phrase in user_input.lower() 
            for phrase in ["what", "how", "why", "where", "when", "who", "which", "their", "there", "it", "this", "that", "these", "those"]
        )

        # Generate contextual prompt
        prompt = f"""You are a helpful food recommendation assistant. 

Previous conversation:
{conversation_context}

Current user query: "{user_input}"

Available food items:
{format_foods_for_prompt(retrieved_foods)}

Important instructions:
1. If this is a follow-up question about a specific food (detected: {is_followup}):
   - Focus ONLY on the food item discussed in the previous exchange
   - Do not introduce new, unrelated food items
   - If asking about ingredients/details of a specific food, only discuss that food

2. If this is a new question:
   - Only mention and recommend foods that match the user's query
   - Do not mention unsuitable foods
   - Focus on directly answering the user's query

3. End your response with a list of recommended food IDs in this format: [RECOMMENDED_FOODS:id1,id2,id3]
   - No spaces after commas
   - Only include IDs of foods you actually discuss
   - For follow-up questions about a specific food, only include that food's ID

Example formats:
New question: "Here are some great options... [RECOMMENDED_FOODS:41,1,16]"
Follow-up about specific food: "The ingredients in this dish are... [RECOMMENDED_FOODS:41]"
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