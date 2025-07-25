from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_new_index
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

@app.route('/chat', methods=['POST'])
def chat():
    try:
        username = session.get('username')
        if not username:
            return jsonify({'success': False, 'error': 'User not logged in'}), 401

        data = request.json
        user_input = data['message']
        chat_history = data.get('history', [])
        use_weather_time = data.get('use_weather_time', False)

        # Get user
        user = User.query.filter_by(username=username).first()
        if not user:
            return jsonify({'success': False, 'error': 'User not found'}), 404

        # Get conversation manager for the user
        conversation_manager = get_conversation_manager(username)

        # Get contextual information if toggle is on
        context = get_contextual_info() if use_weather_time else None

        # Analyze intent before processing
        try:
            intent_analysis = conversation_manager.analyze_user_intent(user_input)
        except Exception as e:
            print(f"Error analyzing intent: {str(e)}")
            # Provide a default intent analysis if there's an error
            intent_analysis = {
                'is_followup': False,
                'followup_type': None,
                'intent': 'general_query',
                'context_references': [],
                'referenced_items': []
            }
        
        # Create a new conversation for each chat
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

        # Embed the user input
        query_embedding = get_embedding(user_input)

        # Query Pinecone with context-aware search
        index = get_new_index()
        
        # If it's a follow-up, include context in the search
        if intent_analysis['is_followup']:
            try:
                # Add context from conversation state to the search
                context_terms = []
                
                # Add last recommendations to context if this is a follow-up about specific items
                if intent_analysis['followup_type'] in ['clarification', 'modification', 'comparison']:
                    last_foods = conversation_manager.conversation_state.get('last_recommendations', [])
                    if last_foods:
                        context_terms.extend([food['name'] for food in last_foods])
                
                # Add other context terms
                if conversation_manager.conversation_state.get('last_meal_type'):
                    context_terms.append(conversation_manager.conversation_state['last_meal_type'])
                if conversation_manager.conversation_state.get('last_dietary'):
                    context_terms.append(conversation_manager.conversation_state['last_dietary'])
                if conversation_manager.conversation_state.get('last_price_range'):
                    context_terms.append(conversation_manager.conversation_state['last_price_range'])
                if conversation_manager.conversation_state.get('last_cuisine'):
                    context_terms.append(conversation_manager.conversation_state['last_cuisine'])
                
                # Add referenced items from intent analysis
                if intent_analysis.get('referenced_items'):
                    context_terms.extend(intent_analysis['referenced_items'])
                
                # Combine user input with context
                enhanced_query = f"{user_input} {' '.join(context_terms)}"
                query_embedding = get_embedding(enhanced_query)
            except Exception as e:
                print(f"Error updating preferences: {str(e)}")
                # Continue with original query if context update fails
                pass
        
        try:
            # Increase top_k to get more potential matches
            results = index.query(vector=query_embedding, top_k=20, include_metadata=True)
            matches = results['matches']
            retrieved_foods = [match['metadata'] for match in matches]
            
            # Ensure diversity in recommendations
            diverse_foods = conversation_manager._enforce_recommendation_diversity(retrieved_foods)
        except Exception as e:
            print(f"Error querying Pinecone: {str(e)}")
            retrieved_foods = []
            diverse_foods = []

        # Generate contextual prompt using AI-driven conversation manager
        try:
            prompt = conversation_manager.generate_contextual_prompt(user_input, retrieved_foods)
        except Exception as e:
            print(f"Error generating prompt: {str(e)}")
            prompt = f"User query: {user_input}\n\nAvailable foods:\n{format_foods_for_prompt(retrieved_foods)}\n\nPlease provide a helpful response about these food options."
        
        # Add contextual information to the prompt if toggle is on
        if use_weather_time and context:
            try:
                context_text = f"""
Current Time: {context['time']['hour']}:00 on {context['time']['day']}, {context['time']['date']}
"""
                if 'weather' in context:
                    context_text += f"""
Current Weather: {context['weather']['temperature']}°C, {context['weather']['description']}
Humidity: {context['weather']['humidity']}%
"""
                if 'holidays' in context:
                    context_text += "\nUpcoming Holidays:\n" + "\n".join([
                        f"- {holiday['name']} ({holiday['date']})"
                        for holiday in context['holidays']
                    ])

                prompt = f"""
Current Context:
{context_text}

{prompt}

Based on the user's mood, current time, weather conditions, and any upcoming holidays, suggest the best option(s) in a friendly and intelligent way. Consider:
1. Time of day (breakfast, lunch, dinner, snack)
2. Weather conditions (hot, cold, rainy)
3. Any special occasions or holidays
4. User's mood and preferences

Your recommendation:
"""
            except Exception as e:
                print(f"Error adding context: {str(e)}")
                # Continue without context if there's an error
                pass

        # Generate with Gemini
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            # Clean response and extract recommended food IDs
            cleaned_response, recommended_food_ids = parse_response_and_recommendations(response.text)

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

            # Update conversation manager with the exchange
            try:
                conversation_manager.add_exchange(user_input, cleaned_response, filtered_foods)
            except Exception as e:
                print(f"Error updating conversation manager: {str(e)}")
                # Continue even if conversation manager update fails
                pass

            # Return the successful response
            return jsonify({
                'response': cleaned_response,
                'foods': filtered_foods,
                'is_followup': intent_analysis['is_followup'],
                'followup_type': intent_analysis['followup_type'],
                'intent': intent_analysis['intent'],
                'context_references': intent_analysis['context_references'],
                'referenced_items': intent_analysis.get('referenced_items', []),
                'conversation_state': conversation_manager.conversation_state,
                'context': context if use_weather_time else None
            })

        except Exception as e:
            print(f"Error generating response: {str(e)}")
            # Return a single error response
            return jsonify({
                'response': "I apologize, but I'm having trouble processing your request right now. Could you please try again?",
                'foods': [],
                'is_followup': False,
                'followup_type': None,
                'intent': 'error',
                'context_references': [],
                'referenced_items': [],
                'conversation_state': conversation_manager.conversation_state,
                'context': None
            })

    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        # Return a single error response
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
    formatted_foods = []
    for food in foods:
        # Use the correct keys from Pinecone data
        food_id = food.get('Id', 'N/A')
        name = food.get('ProductName', '')
        image = food.get('Image', '')
        description = food.get('Description', '')
        price = food.get('Price', '')
        formatted_foods.append(
            f"[ID:{food_id}] {name} - {description} - {image} - {price}"
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

@app.route('/recommend', methods=['POST'])
def api_recommend():
    try:
        data = request.get_json()
        prompt = data.get('prompt')
        if not prompt:
            return jsonify({'error': 'No prompt provided'}), 400

        # Use a stateless ConversationManager for API calls
        conversation_manager = ConversationManager()

        # Embed the prompt
        query_embedding = get_embedding(prompt)

        # Use the 'niloufer-prod-data' Pinecone index
        from utils.pinecone_helper import get_new_index
        index = get_new_index(index_name='niloufer-prod-data')

        # Query Pinecone for relevant foods
        try:
            results = index.query(vector=query_embedding, top_k=50, include_metadata=True)
            matches = results['matches']
            retrieved_foods = [match['metadata'] for match in matches]
            diverse_foods = conversation_manager._enforce_recommendation_diversity(retrieved_foods)
        except Exception as e:
            print(f"Error querying Pinecone: {str(e)}")
            retrieved_foods = []
            diverse_foods = []

        # Fallback: if any product name matches the prompt, ensure it is included in the foods passed to Gemini
        prompt_lower = prompt.lower()
        matching_foods = [food for food in retrieved_foods if food.get('ProductName', '').lower() in prompt_lower or prompt_lower in food.get('ProductName', '').lower()]
        # Combine matching foods with the top 10, ensuring no duplicates
        foods_for_prompt = []
        seen_ids = set()
        for food in matching_foods + retrieved_foods[:10]:
            food_id = food.get('Id')
            if food_id and food_id not in seen_ids:
                foods_for_prompt.append(food)
                seen_ids.add(food_id)

        # Debug print: show the foods being sent to Gemini
        print("Foods for Gemini prompt:", [food.get('ProductName', '') for food in foods_for_prompt])

        foods_section = f"Available foods:\n{format_foods_for_prompt(foods_for_prompt)}"

        # Few-shot example to help Gemini recommend using [RECOMMENDED_FOODS:...]
        example_block = (
            "Example:\n"
            "User query: I want something spicy.\n"
            "Available foods:\n"
            "[ID:12] Spicy Paneer Wrap - A wrap filled with spicy paneer and veggies.\n"
            "[ID:15] Chilli Chicken - Chicken cooked in spicy sauce.\n"
            "[ID:23] Veg Biryani - Aromatic rice with vegetables and spices.\n\n"
            "Response:\n"
            "Here are some spicy options you might like:\n"
            "- Spicy Paneer Wrap\n"
            "- Chilli Chicken\n\n"
            "Would you like something vegetarian or non-vegetarian?\n\n"
            "[RECOMMENDED_FOODS:12,15]\n"
            "---\n"
        )

        # Generate prompt for Gemini, always including the food list
        try:
            base_prompt = conversation_manager.generate_contextual_prompt(prompt, foods_for_prompt)
        except Exception as e:
            print(f"Error generating prompt: {str(e)}")
            base_prompt = f"User query: {prompt}"

        prompt_text = (
            f"{example_block}"
            f"{base_prompt}\n\n{foods_section}\n\n"
            "IMPORTANT: You are a friendly, intelligent food suggestion bot. "
            "Always recommend 1–3 food options from the list above that are most relevant to the user's prompt. "
            "If the user's query is unclear, make your best guess and still recommend food options. "
            "Only ask a follow-up question if absolutely necessary, and always after making recommendations. "
            "At the end of your response, include a line in the format [RECOMMENDED_FOODS:id1,id2,...] "
            "where id1, id2, etc. are the IDs of the foods you are recommending from the list above. "
            "If you don't want to recommend any, still include the tag as [RECOMMENDED_FOODS:]."
        )

        # Debug print: show the prompt text sent to Gemini
        print("Prompt sent to Gemini:\n", prompt_text)

        # Generate with Gemini
        try:
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt_text)
            cleaned_response, recommended_food_ids = parse_response_and_recommendations(response.text)

            # Post-process: if Gemini's response contains a food name, return its ID
            recommended_ids = set(recommended_food_ids)
            response_lower = cleaned_response.lower()
            for food in foods_for_prompt:
                name = food.get('ProductName', '').lower()
                if name and name in response_lower:
                    recommended_ids.add(food.get('Id'))

            return jsonify({'response': cleaned_response, 'recommended_food_ids': list(recommended_ids)})
        except Exception as e:
            print(f"Error generating response: {str(e)}")
            return jsonify({'error': 'AI generation failed', 'details': str(e)}), 500

    except Exception as e:
        print(f"Error in /api/recommend: {str(e)}")
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True) 