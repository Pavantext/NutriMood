from flask import Flask, render_template, request, jsonify, session, redirect, url_for, abort
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper_new import get_new_index
import google.generativeai as genai
import time
import re
from datetime import timedelta, datetime
import json
from functools import wraps
from models import db, User, Conversation, Message
from flask_migrate import Migrate
from utils.conversation_manager import ConversationManager

# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
app.permanent_session_lifetime = timedelta(days=1)

# Admin credentials
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")

# Database configuration
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv("DATABASE_URL")
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db.init_app(app)
migrate = Migrate(app, db)

# Store conversation managers in memory
conversation_managers = {}

def get_conversation_manager(username):
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

# Routes
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

@app.route('/admin/dashboard')
@admin_required
def admin_dashboard():
    users = User.query.all()
    users_info = {}
    for user in users:
        conversations = Conversation.query.filter_by(user_id=user.id).all()
        total_recommendations = sum(
            len(msg.recommended_foods) 
            for conv in conversations 
            for msg in Message.query.filter_by(conversation_id=conv.id, sender='bot')
        )
        users_info[user.username] = {
            'login_time': user.login_time.isoformat(),
            'conversation_count': len(conversations),
            'total_recommendations': total_recommendations
        }
    return render_template('admin_dashboard.html', users=users_info)

@app.route('/login', methods=['POST'])
def login():
    try:
        data = request.json
        username = data.get('username', '').strip()
        if not username:
            return jsonify({'success': False, 'error': 'Username is required'}), 400

        # Clear existing session
        session.clear()
        
        # Create new session
        session.permanent = True
        session['username'] = username

        user = User.query.filter_by(username=username).first()
        if not user:
            user = User(username=username)
            db.session.add(user)
            db.session.commit()

        get_conversation_manager(username)
        return jsonify({'success': True, 'username': username})
    
    except Exception as e:
        print(f"Login error: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    if request.content_type != 'application/json':
        return jsonify({'error': 'Invalid content type'}), 415

    try:
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401

        data = request.json
        user_input = data['message']
        
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        conversation_manager = get_conversation_manager(username)
        intent_analysis = conversation_manager.analyze_user_intent(user_input)
        
        conversation = Conversation(user_id=user.id)
        db.session.add(conversation)
        db.session.commit()

        user_message = Message(
            conversation_id=conversation.id,
            sender='user',
            content=user_input
        )
        db.session.add(user_message)
        db.session.commit()

        query_embedding = get_embedding(user_input)
        index = get_new_index()
        
        if intent_analysis['is_followup']:
            context_terms = [
                conversation_manager.conversation_state.get('last_meal_type', ''),
                conversation_manager.conversation_state.get('last_dietary', ''),
                conversation_manager.conversation_state.get('last_price_range', '')
            ]
            enhanced_query = f"{user_input} {' '.join(context_terms)}"
            query_embedding = get_embedding(enhanced_query)
        
        results = index.query(vector=query_embedding, top_k=10, include_metadata=True)
        matches = results['matches']
        retrieved_foods = [match['metadata'] for match in matches]

        prompt = conversation_manager.generate_contextual_prompt(user_input, retrieved_foods)
        model = genai.GenerativeModel('gemini-1.5-flash')
        response = model.generate_content(prompt)
        
        cleaned_response, recommended_food_ids = parse_response_and_recommendations(response.text)
        filtered_foods = [
            food for food in retrieved_foods 
            if str(food.get('id', '')) in recommended_food_ids
        ] if recommended_food_ids else []

        bot_message = Message(
            conversation_id=conversation.id,
            sender='bot',
            content=cleaned_response,
            recommended_foods=filtered_foods
        )
        db.session.add(bot_message)
        db.session.commit()

        conversation_manager.add_exchange(user_input, cleaned_response, filtered_foods)

        return jsonify({
            'response': cleaned_response,
            'foods': filtered_foods,
            'is_followup': intent_analysis['is_followup'],
            'followup_type': intent_analysis['followup_type'],
            'intent': intent_analysis['intent'],
            'context_references': intent_analysis['context_references'],
            'referenced_items': intent_analysis.get('referenced_items', []),
            'conversation_state': conversation_manager.conversation_state
        })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        return jsonify({'error': 'An error occurred while processing your request.', 'details': str(e)}), 500

@app.route('/')
def home():
    if 'username' not in session:
        return redirect(url_for('login_page'))
    return render_template('index.html')

@app.route('/login')
def login_page():
    return render_template('index.html')  # This will trigger the login modal

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

@app.before_request
def check_valid_session():
    exempt_endpoints = ['admin_login', 'static', 'login_page', 'login']
    if request.endpoint in exempt_endpoints:
        return
    if 'username' not in session:
        return jsonify({'error': 'Session expired'}), 401

@app.after_request
def add_security_headers(response):
    response.headers['X-Content-Type-Options'] = 'nosniff'
    response.headers['X-Frame-Options'] = 'DENY'
    response.headers['Cache-Control'] = 'no-store, max-age=0'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    return response

if __name__ == '__main__':
    app.run(debug=True)
