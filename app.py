from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.conversation_manager import ConversationManager
import google.generativeai as genai
import time
import re
from datetime import timedelta, datetime
import json
from functools import wraps
from models import db, User, Conversation, Message
from flask_migrate import Migrate
import requests
import pytz
from utils.langchain_manager import LangChainManager
from langchain_core.messages import HumanMessage, AIMessage

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

# Store conversation managers in memory
conversation_managers = {}
langchain_manager = LangChainManager()

def get_conversation_manager(username):
    """Get or create a conversation manager for a user"""
    if username not in conversation_managers:
        conversation_managers[username] = ConversationManager()
    return conversation_managers[username]

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

        # Initialize conversation manager for the user
        get_conversation_manager(username)

        return jsonify({'success': True, 'username': username})
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/logout', methods=['POST'])
def logout():
    try:
        username = session.get('username')
        if username in conversation_managers:
            del conversation_managers[username]
        session.clear()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

def get_contextual_info():
    """Get weather, time, and holiday information"""
    context = {}
    
    # Get current time
    ist = pytz.timezone('Asia/Kolkata')
    current_time = datetime.now(ist)
    context['time'] = {
        'hour': current_time.hour,
        'day': current_time.strftime('%A'),
        'date': current_time.strftime('%Y-%m-%d')
    }
    
    # Get weather
    weather_api_key = os.getenv("WEATHER_API_KEY")
    if weather_api_key:
        try:
            response = requests.get(
                "http://api.openweathermap.org/data/2.5/weather",
                params={
                    'q': 'Hyderabad,IN',
                    'appid': weather_api_key,
                    'units': 'metric'
                }
            )
            if response.status_code == 200:
                weather_data = response.json()
                context['weather'] = {
                    'temperature': weather_data['main']['temp'],
                    'description': weather_data['weather'][0]['description'],
                    'humidity': weather_data['main']['humidity']
                }
        except Exception as e:
            print(f"Warning: Could not fetch weather data: {str(e)}")
    
    # Get holidays
    holiday_api_key = os.getenv("HOLIDAY_API_KEY")
    if holiday_api_key:
        try:
            response = requests.get(
                "https://calendarific.com/api/v2/holidays",
                params={
                    'api_key': holiday_api_key,
                    'country': 'IN',
                    'year': current_time.year,
                    'month': current_time.month
                }
            )
            if response.status_code == 200:
                holiday_data = response.json()
                holidays = holiday_data.get('response', {}).get('holidays', [])
                context['holidays'] = [
                    {
                        'name': holiday['name'],
                        'date': holiday['date']['iso']
                    }
                    for holiday in holidays
                ]
        except Exception as e:
            print(f"Warning: Could not fetch holiday data: {str(e)}")
    
    return context

# Utility to convert chat history to LangChain message objects
def convert_history(history):
    # If history is not a list, treat as empty
    if not isinstance(history, list):
        return []
    if history and isinstance(history[0], (HumanMessage, AIMessage)):
        return history
    messages = []
    for msg in history:
        if isinstance(msg, dict):
            if msg.get("role") == "user":
                messages.append(HumanMessage(content=msg.get("content", "")))
            elif msg.get("role") == "assistant":
                messages.append(AIMessage(content=msg.get("content", "")))
        elif isinstance(msg, str):
            if len(messages) % 2 == 0:
                messages.append(HumanMessage(content=msg))
            else:
                messages.append(AIMessage(content=msg))
    return messages

@app.route('/chat', methods=['POST'])
def chat():
    try:
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401

        data = request.json
        user_input = data['message']
        use_weather_time = data.get('use_weather_time', False)

        # Get user
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Get contextual information if toggle is on
        context = get_contextual_info() if use_weather_time else None

        # Use LangChain (now with LangGraph memory) for food recommendations
        try:
            result = langchain_manager.ask(user_input, username)
            response_text = result['answer']
        except Exception as e:
            print(f"Error generating response with LangChain: {str(e)}")
            return jsonify({
                'response': "I apologize, but I'm having trouble processing your request right now. Could you please try again?",
                'foods': [],
                'is_followup': False,
                'followup_type': None,
                'intent': 'error',
                'context_references': [],
                'referenced_items': [],
                'conversation_state': {},
                'context': None
            })

        return jsonify({
            'response': response_text,
            'foods': [],
            'is_followup': False,
            'followup_type': None,
            'intent': '',
            'context_references': [],
            'referenced_items': [],
            'conversation_state': {},
            'context': context if use_weather_time else None
        })
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({
            'response': "I apologize, but I'm having trouble processing your request right now. Could you please try again?",
            'foods': [],
            'is_followup': False,
            'followup_type': None,
            'intent': 'error',
            'context_references': [],
            'referenced_items': [],
            'conversation_state': {},
            'context': None
        }), 500

@app.route('/user_data', methods=['GET'])
def get_user_data():
    try:
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401

        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': 'No data found for user'}), 404

        conversations = Conversation.query.filter_by(user_id=user.id).order_by(Conversation.id.desc()).all()
        data = []
        
        for conv in conversations:
            messages = Message.query.filter_by(conversation_id=conv.id).order_by(Message.id).all()
            
            # Process messages in pairs (user message followed by bot response)
            for i in range(0, len(messages), 2):
                if i + 1 < len(messages):  # Ensure we have both user and bot messages
                    user_msg = messages[i]
                    bot_msg = messages[i + 1]
                    
                    conversation_data = {
                        'timestamp': user_msg.timestamp.isoformat(),
                        'user_input': user_msg.content,
                        'ai_response': bot_msg.content,
                        'recommended_foods': bot_msg.recommended_foods if bot_msg.recommended_foods else [],
                        'is_followup': False  # You can implement followup detection logic here if needed
                    }
                    data.append(conversation_data)

        return jsonify({
            'success': True,
            'data': {
                'login_time': user.login_time.isoformat(),
                'conversations': data
            }
        })
    except Exception as e:
        print(f"Error in get_user_data: {str(e)}")
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
        # Remove the [RECOMMENDED_FOODS:...] line from the response
        cleaned_response = text[:match.start()].strip()
    else:
        cleaned_response = text.strip()
        recommended_food_ids = []
    
    # Clean the response
    cleaned_response = clean_response(cleaned_response)
    
    return cleaned_response, recommended_food_ids

def clean_response(text):
    """Clean the response text by removing HTML tags and extra whitespace"""
    # Remove HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove any remaining ID references
    text = re.sub(r'\[ID:\d+\]', '', text)
    # Remove the [RECOMMENDED_FOODS:...] line if it exists
    text = re.sub(r'\[RECOMMENDED_FOODS:[^\]]+\]', '', text)
    # Remove [FOOD RECOMMENDATION] text
    text = re.sub(r'\[FOOD RECOMMENDATION\]', '', text)
    # Remove ID references in the format "ID: number"
    text = re.sub(r'\(ID:\s*\d+\)', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

@app.route('/user_data_page')
def user_data_page():
    if not session.get('username'):
        return redirect(url_for('home'))
    return render_template('user_data.html')

@app.route('/menu')
def menu():
    if not session.get('username'):
        return redirect(url_for('home'))
    
    # Load food items from JSON file
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'data', 'niloufer.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            menu_items = json.load(file)
    except Exception as e:
        print(f"Error loading menu items: {str(e)}")
        menu_items = []
    
    return render_template('menu.html', menu_items=menu_items)

@app.route('/menu-data')
def menu_data():
    if not session.get('username'):
        return jsonify({'error': 'Not authorized'}), 401
    
    try:
        json_path = os.path.join(os.path.dirname(__file__), 'data', 'niloufer.json')
        with open(json_path, 'r', encoding='utf-8') as file:
            menu_items = json.load(file)
        return jsonify(menu_items)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/reset_chat', methods=['POST'])
def reset_chat():
    try:
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401

        # Clear the conversation manager for this user
        if username in conversation_managers:
            del conversation_managers[username]
        
        # Create a new conversation manager
        get_conversation_manager(username)
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Reset chat error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 