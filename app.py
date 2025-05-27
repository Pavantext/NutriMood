from flask import Flask, render_template, request, jsonify, session, redirect, url_for
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_index
from utils.conversation_manager import ConversationManager
import google.generativeai as genai
import time
import re
from datetime import timedelta, datetime
import json
from functools import wraps
from models import db, User, Conversation, Message
from flask_migrate import Migrate

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Flask app
app = Flask(__name__)

# Set a stable secret key - in production, use an environment variable
app.secret_key = os.getenv("SECRET_KEY")  # Replace this with a secure key in production
app.permanent_session_lifetime = timedelta(days=1)  # Session expires after 1 day

# Admin credentials - In production, use environment variables
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")  # Paste your Supabase connection string here
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
migrate = Migrate(app, db)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('is_admin'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard'))
        
        return render_template('admin_login.html', error="Invalid credentials")
    
    return render_template('admin_login.html')

@app.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    return redirect(url_for('admin_login'))

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users = User.query.all()
    users_info = {}
    for user in users:
        conversations = Conversation.query.filter_by(user_id=user.id).all()
        total_recommendations = 0
        for conv in conversations:
            messages = Message.query.filter_by(conversation_id=conv.id, sender='bot').all()
            for msg in messages:
                if msg.recommended_foods:
                    total_recommendations += len(msg.recommended_foods)
        users_info[user.username] = {
            'login_time': user.login_time.isoformat(),
            'conversation_count': len(conversations),
            'total_recommendations': total_recommendations
        }
    return render_template('admin_dashboard.html', users=users_info)

@app.route('/admin/user/<username>')
@admin_required
def admin_user_details(username):
    user = User.query.filter_by(username=username).first()
    if not user:
        return redirect(url_for('admin_dashboard'))
    conversations = Conversation.query.filter_by(user_id=user.id).all()
    user_data = {
        'login_time': user.login_time.isoformat(),
        'conversations': []
    }
    for conv in conversations:
        messages = Message.query.filter_by(conversation_id=conv.id).all()
        for i in range(0, len(messages), 2):
            user_msg = messages[i]
            bot_msg = messages[i+1] if i+1 < len(messages) else None
            recommended_foods = []
            if bot_msg and bot_msg.recommended_foods is not None:
                recommended_foods = bot_msg.recommended_foods
            user_data['conversations'].append({
                'timestamp': user_msg.timestamp.isoformat(),
                'user_input': user_msg.content,
                'ai_response': bot_msg.content if bot_msg else '',
                'recommended_foods': recommended_foods,
                'is_followup': False
            })
    return render_template('admin_user_details.html', username=username, user_data=user_data)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400

        session.permanent = True
        session['username'] = username

        # Check if user exists, else create
        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()

        return jsonify({'success': True, 'username': username})
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    try:
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    try:
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401

        data = request.json
        user_input = data['message']
        chat_history = data.get('history', [])

        # Get user
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Create a new conversation for each chat (or group by session if you want)
        conversation = Conversation(user_id=user.id)
        db.session.add(conversation)
        db.session.commit()

        # Store user message
        user_message = Message(
            conversation_id=conversation.id,
            sender='user',
            content=user_input
        )
        db.session.add(user_message)
        db.session.commit()

        # Build conversation context from history
        conversation_context = ""
        if chat_history:
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
        prompt = f"""You are a friendly and helpful food recommendation assistant. \n\nPrevious conversation:\n{conversation_context}\n\nCurrent user query: \"{user_input}\"\n\nAvailable food items:\n{format_foods_for_prompt(retrieved_foods)}\n\nImportant instructions:\n1. For casual greetings (like 'hi', 'hello', 'how are you'):
   - Respond in a friendly, conversational way
   - Don't mention food recommendations
   - Don't include [RECOMMENDED_FOODS:] tag
   - Ask what they're looking for in a natural way

2. If this is a follow-up question about a specific food (detected: {is_followup}):
   - Focus ONLY on the food item discussed in the previous exchange
   - Do not introduce new, unrelated food items
   - If asking about ingredients/details of a specific food, only discuss that food

3. If this is a new food-related question:
   - Only mention and recommend foods that match the user's query
   - Do not mention unsuitable foods
   - Focus on directly answering the user's query
   - End your response with a list of recommended food IDs in this format: [RECOMMENDED_FOODS:id1,id2,id3]
   - No spaces after commas
   - Only include IDs of foods you actually discuss
   - For follow-up questions about a specific food, only include that food's ID

Example formats:
Greeting: "Hi there! I'm your food recommendation assistant. What kind of food are you interested in today?"
New question: "Here are some great options... [RECOMMENDED_FOODS:41,1,16]"
Follow-up about specific food: "The ingredients in this dish are... [RECOMMENDED_FOODS:41]"
"""

        # Generate with Gemini
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        # Clean response and extract recommended food IDs
        cleaned_response, recommended_food_ids = parse_response_and_recommendations(response.text)

        # For casual greetings, don't include food recommendations
        if any(greeting in user_input.lower() for greeting in ['hi', 'hello', 'hey', 'how are you', 'how\'s it going']):
            recommended_food_ids = []
            filtered_foods = []

        # Filter retrieved foods based on recommendations
        filtered_foods = [
            food for food in retrieved_foods 
            if str(food.get('id', '')) in recommended_food_ids
        ] if recommended_food_ids else []

        # Store bot message
        bot_message = Message(
            conversation_id=conversation.id,
            sender='bot',
            content=cleaned_response,
            recommended_foods=filtered_foods
        )
        db.session.add(bot_message)
        db.session.commit()

        return jsonify({
            'response': cleaned_response,
            'foods': filtered_foods
        })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request.', 'details': str(e)}), 500

@app.route('/user_data', methods=['GET'])
def get_user_data():
    try:
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': 'No data found for user'}), 404

        conversations = Conversation.query.filter_by(user_id=user.id).all()
        data = []
        for conv in conversations:
            messages = Message.query.filter_by(conversation_id=conv.id).all()
            for i in range(0, len(messages), 2):
                user_msg = messages[i]
                bot_msg = messages[i+1] if i+1 < len(messages) else None
                data.append({
                    'timestamp': user_msg.timestamp.isoformat(),
                    'user_input': user_msg.content,
                    'ai_response': bot_msg.content if bot_msg else '',
                    'recommended_foods': bot_msg.recommended_foods if bot_msg else [],
                    'is_followup': False
                })
        return jsonify({
            'success': True,
            'data': {
                'login_time': user.login_time.isoformat(),
                'conversations': data
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/all_users', methods=['GET'])
def get_all_users():
    try:
        users = User.query.all()
        users_info = {}
        for user in users:
            conversations = Conversation.query.filter_by(user_id=user.id).all()
            users_info[user.username] = {
                'login_time': user.login_time.isoformat(),
                'conversation_count': len(conversations)
            }
        return jsonify({
            'success': True,
            'users': users_info
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

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
        # Store ID in a hidden format that the AI can still parse
        formatted_foods.append(
            f"[ID:{food.get('id', 'N/A')}] {food.get('name', '')}{dietary_str} - {food.get('description', '')}"
        )
    return "\n".join(formatted_foods)

def parse_response_and_recommendations(text):
    """Extract the response and recommended food IDs"""
    # First, remove any visible food IDs from the response
    text = re.sub(r'\[ID:\d+\]', '', text)
    
    # Then extract the recommended food IDs
    match = re.search(r'\[RECOMMENDED_FOODS:([^\]]+)\]', text)
    if match:
        food_ids_str = match.group(1).strip()
        recommended_food_ids = [id.strip() for id in food_ids_str.split(',')]
        cleaned_response = text[:match.start()].strip()
    else:
        cleaned_response = text.strip()
        recommended_food_ids = []
    return clean_response(cleaned_response), recommended_food_ids

def clean_response(text):
    """Clean the response text by removing HTML tags and extra whitespace"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove any remaining ID references
    text = re.sub(r'\[ID:\d+\]', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

@app.route('/user_data_page')
def user_data_page():
    if not session.get('username'):
        return redirect(url_for('home'))
    return render_template('user_data.html')

if __name__ == '__main__':
    app.run(debug=True) 