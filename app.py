import streamlit as st
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_index
from utils.conversation_manager import ConversationManager
import google.generativeai as genai
import time
import re

# Page config
st.set_page_config(
    page_title="Food AI Chat",
    page_icon="🍽️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
    <style>
    /* General layout */
    .main {
        background-color: #fafafa !important;
    }

    .stApp {
        background-color: #fafafa !important;
    }

    .block-container {
        max-width: 800px;
        margin: 0 auto;
        padding-bottom: 100px; /* Extra space for sticky input */
    }

    /* Fix text colors */
    .st-emotion-cache-13k62yr, 
    .st-emotion-cache-ltfnpr,
    .st-emotion-cache-cnbvxy p,
    p,
    .strong,
    div,
    span,
    label,
    .st-emotion-cache-cnbvxy li {
        color: #2b313e !important;
    }

    /* Chat message bubbles */
    .user-message {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%);
        color: white !important;
        padding: 0.8rem;
        border-radius: 20px 20px 0 20px;
        margin: 0.3rem 0;
        max-width: 85%;
        margin-left: auto;
        font-size: 15px;
        line-height: 1.4;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.2);
    }

    .assistant-message {
        background: white;
        color: #2b313e !important;
        padding: 0.8rem;
        border-radius: 20px 20px 20px 0;
        margin: 0.3rem 0;
        max-width: 85%;
        font-size: 15px;
        line-height: 1.4;
        border: 1px solid #f0f0f0;
        box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
    }

    .message-wrapper {
        display: flex;
        align-items: flex-start;
        animation: fadeIn 0.3s ease-in-out;
    }

    .message-wrapper.user {
        flex-direction: row-reverse;
    }

    @keyframes fadeIn {
        from { opacity: 0; transform: translateY(10px); }
        to { opacity: 1; transform: translateY(0); }
    }

    /* Sticky input bar */
    .sticky-input-bar {
        position: fixed;
        bottom: 0;
        left: 0;
        right: 0;
        background: white;
        padding: 0.5rem 1rem;
        box-shadow: 0 -4px 20px rgba(0,0,0,0.08);
        z-index: 9999;
        border-top: 1px solid #f0f0f0;
        display: flex;
        justify-content: center;
        align-items: center;
    }

    .input-wrapper {
        width: 100%;
        max-width: 800px;
        display: flex;
        gap: 0.5rem;
        align-items: center;
        background: rgba(255,255,255,0.95);
        border-radius: 30px;
        padding: 0.25rem 0.5rem;
        box-shadow: 0 2px 10px rgba(0,0,0,0.03);
    }

    .stTextInput > div > div > input {
        color: #2b313e !important;
        background-color: white !important;
        border-radius: 25px;
        padding: 0 20px;
        font-size: 15px;
        border: 2px solid #f0f0f0;
        height: 44px;
        flex: 1;
        margin: 0;
        box-shadow: none;
        transition: all 0.3s ease;
    }

    .stTextInput > div > div > input:focus {
        border-color: #FF6B6B;
        box-shadow: 0 2px 15px rgba(255, 107, 107, 0.08);
        outline: none;
    }

    /* Button styles with stronger overrides */
    .stButton,
    .stButton > button,
    .stButton > button:hover,
    .stButton > button:active,
    .stButton > button:focus,
    button[kind="primary"],
    button[data-testid="baseButton-secondary"],
    .element-container .stButton > button,
    div[data-testid="stFormSubmitButton"] button {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%) !important;
        background-color: #FF6B6B !important;
        border-color: #FF6B6B !important;
        color: white !important;
        border-radius: 25px !important;
        padding: 0 24px !important;
        font-weight: 600 !important;
        border: none !important;
        height: 44px !important;
        min-width: 80px !important;
    }

    /* Style overrides for the form submit button specifically */
    div[data-testid="stFormSubmitButton"] {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%) !important;
        background-color: #FF6B6B !important;
        border: none !important;
    }

    /* Additional override for the button container */
    .stButton > div[data-testid="stFormSubmitButton"] {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%) !important;
        background-color: #FF6B6B !important;
    }

    /* Override for any nested elements */
    .stButton > button > div,
    .stButton > button > p,
    .stButton > button > span {
        color: white !important;
    }

    /* Hover state */
    .stButton > button:hover {
        background: linear-gradient(135deg, #FF8E8E 0%, #FF6B6B 100%) !important;
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.18) !important;
    }

    /* Active state */
    .stButton > button:active {
        transform: translateY(0) !important;
    }

    /* Focus state */
    .stButton > button:focus {
        box-shadow: 0 0 0 0.2rem rgba(255, 107, 107, 0.25) !important;
        outline: none !important;
    }

    /* Ensure text color stays white */
    .stButton > button * {
        color: white !important;
    }

    /* Welcome message */
    .welcome-message {
        text-align: center;
        padding: 1rem;
        background: white !important;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 0.5rem;
    }

    .welcome-message h1 {
        color: #FF6B6B !important;
        font-size: 1.3rem;
    }

    .welcome-message p {
        color: #666 !important;
        font-size: 0.9rem;
    }

    .food-decoration {
        font-size: 1.2rem;
        margin: 0 0.2rem;
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
        width: 6px;
    }

    ::-webkit-scrollbar-thumb {
        background: #FF6B6B;
        border-radius: 3px;
    }

    ::-webkit-scrollbar-track {
        background: #f1f1f1;
    }

    ::-webkit-scrollbar-thumb:hover {
        background: #FF8E8E;
    }

        /* Ensure the input caret is visible */
    .stTextInput input {
        caret-color: auto !important;
    }

    /* Hide Streamlit native UI */
    #MainMenu, footer {visibility: hidden;}

    /* Sidebar */
    .sidebar-desc-white {
        color: white !important;
        font-size: 1rem;
        margin-bottom: 0.5rem;
    }

    .food-card {
        background: white !important;
        border-radius: 18px;
        box-shadow: 0 2px 12px rgba(44,62,80,0.08);
        padding: 1rem;
        margin: 1rem 0;
        display: flex;
        flex-direction: column;
        gap: 1rem;
        max-width: 420px;
    }

    .food-card-main {
        display: flex;
        align-items: flex-start;
        gap: 1.2rem;
    }

    .food-card-footer {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-top: 0.5rem;
        border-top: 1px solid #f0f0f0;
    }

    .quantity-selector {
        display: flex;
        align-items: center;
        gap: 0.5rem;
    }

    .quantity-selector input {
        width: 60px !important;
        text-align: center;
        border: 1px solid #ddd;
        border-radius: 4px;
        padding: 0.2rem;
    }

    .order-button {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%) !important;
        color: white !important;
        border: none !important;
        padding: 0.5rem 1rem !important;
        border-radius: 8px !important;
        cursor: pointer !important;
        font-weight: 600 !important;
        transition: all 0.3s ease !important;
    }

    .order-button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 4px 12px rgba(255, 107, 107, 0.2) !important;
    }

    .success-popup {
        position: fixed;
        bottom: 20px;
        right: 20px;
        background: #28a745;
        color: white;
        padding: 1rem;
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.1);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    }

    @keyframes slideIn {
        from {
            transform: translateX(100%);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }

    /* Ensure all text elements are visible */
    [data-testid="stText"],
    [data-testid="stMarkdown"] {
        color: #2b313e !important;
    }

    /* Sidebar specific styles */
    [data-testid="stSidebar"] {
        background-color: #1E1E1E !important;
    }

    [data-testid="stSidebar"] p,
    [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2,
    [data-testid="stSidebar"] h3,
    [data-testid="stSidebar"] h4,
    [data-testid="stSidebar"] h5,
    [data-testid="stSidebar"] li {
        color: white !important;
    }

    [data-testid="stSidebar"] .sidebar-desc-white {
        color: white !important;
    }

    /* Sidebar markdown text */
    [data-testid="stSidebar"] [data-testid="stMarkdown"] {
        color: white !important;
    }

    /* Sidebar emoji */
    [data-testid="stSidebar"] .emoji {
        color: white !important;
    }

    /* Sidebar horizontal rule */
    [data-testid="stSidebar"] hr {
        border-color: rgba(255, 255, 255, 0.2);
    }

    /* Tips section */
    [data-testid="stSidebar"] ul li {
        color: white !important;
        margin-bottom: 8px;
    }

    .food-card-header {
        display: flex;
        justify-content: space-between;
        align-items: flex-start;
        margin-bottom: 0.3rem;
    }

    .food-card-title {
        color: #FF6B6B !important;
        font-size: 1.1rem;
        font-weight: bold;
    }

    .food-card-price {
        color: #28a745 !important;
        font-weight: bold;
        font-size: 1rem;
        padding: 0.2rem 0.5rem;
        background: rgba(40, 167, 69, 0.1);
        border-radius: 12px;
    }

    .food-card-desc {
        color: #444 !important;
        font-size: 0.97rem;
        margin-bottom: 0.7rem;
    }

    .food-card img {
        border-radius: 12px;
        width: 110px;
        height: 110px;
        object-fit: cover;
        box-shadow: 0 2px 8px rgba(44,62,80,0.07);
    }

    .food-card-content {
        flex: 1;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
    }
    </style>
""", unsafe_allow_html=True)


# Load environment variables
load_dotenv()

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = []
    st.session_state.first_visit = True
    st.session_state.conversation_manager = ConversationManager()

def clean_response(text):
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove any div elements
    text = re.sub(r'div', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

# Function to get recommendations and return both response and retrieved foods
def get_recommendations(user_input):
    # Embed the user input
    query_embedding = get_embedding(user_input)

    # Query Pinecone
    index = get_index()
    results = index.query(vector=query_embedding, top_k=5, include_metadata=True)
    matches = results['matches']
    retrieved_foods = [match['metadata'] for match in matches]

    # Analyze user intent
    intent_analysis = st.session_state.conversation_manager.analyze_user_intent(user_input)

    # If it's a follow-up question, adjust the search results
    if intent_analysis['is_followup']:
        # Include previously discussed foods in the context
        recent_foods = intent_analysis['recent_foods']
        # Combine recent and new foods, removing duplicates
        all_foods = {food['id']: food for food in retrieved_foods + recent_foods}
        retrieved_foods = list(all_foods.values())

    # Generate contextual prompt
    prompt = st.session_state.conversation_manager.generate_contextual_prompt(user_input, retrieved_foods)

    # Generate with Gemini
    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    cleaned_response = clean_response(response.text)

    # Add the exchange to conversation history
    st.session_state.conversation_manager.add_exchange(user_input, cleaned_response, retrieved_foods)

    return cleaned_response, retrieved_foods

# Helper function to extract food names from AI response
def extract_food_names(ai_response, foods):
    # Build a list of food names and their variations
    food_names = {food['name'].lower(): food for food in foods}
    
    # Common recommendation phrases
    recommendation_patterns = [
        r'how about (a |an |some )?(?P<food>[^?!.,]*)',
        r'recommend (?P<food>[^?!.,]*)',
        r'try (?P<food>[^?!.,]*)',
        r'suggest (?P<food>[^?!.,]*)',
        r'would hit the spot\?.*?(?P<food>[^?!.,]*)',
        r'maybe (?P<food>[^?!.,]*) would',
        r'consider (?P<food>[^?!.,]*)',
    ]
    
    recommended_foods = set()
    
    # First look for actively recommended foods
    for pattern in recommendation_patterns:
        matches = re.finditer(pattern, ai_response, re.IGNORECASE)
        for match in matches:
            food_name = match.group('food').strip().lower()
            # Check if this food name or part of it matches our food list
            for known_food in food_names:
                if known_food in food_name:
                    recommended_foods.add(known_food)
    
    # If no recommended foods found through patterns, fall back to direct mentions
    if not recommended_foods:
        for food_name in food_names:
            if food_name in ai_response.lower():
                recommended_foods.add(food_name)
    
    # Convert back to food objects
    return [food for food in foods if food['name'].lower() in recommended_foods]

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/restaurant.png", width=50)
    st.markdown("### Food AI Chat")
    st.markdown("""
<div class="sidebar-desc-white">
Your personal food recommendation assistant.<br>
Chat naturally about what you're craving!
</div>
""", unsafe_allow_html=True)
    
    st.markdown("---")
    st.markdown("### 💡 Tips")
    st.markdown("""
    - Tell me about your mood
    - Share any dietary preferences
    - Mention your favorite cuisines
    - Ask about specific ingredients
    """)

# Welcome message for first visit
if st.session_state.first_visit:
    st.markdown("""
        <div class="welcome-message">
            <h1>Welcome to Food AI Chat! 🍽️</h1>
            <p>I'm your personal food recommendation assistant. Tell me what you're craving!</p>
            <div style="margin-top: 0.3rem;">
                <span class="food-decoration">🍕</span>
                <span class="food-decoration">🍜</span>
                <span class="food-decoration">🍣</span>
                <span class="food-decoration">🍔</span>
            </div>
        </div>
    """, unsafe_allow_html=True)
    st.session_state.first_visit = False

# Display chat messages
for message in st.session_state.messages:
    if message["role"] == "user":
        st.markdown(f"""
            <div class="message-wrapper user">
                <div class="user-message">
                    {message["content"]}
                </div>
            </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
            <div class="message-wrapper">
                <div class="assistant-message">
                    {message["content"]}
                </div>
            </div>
        """, unsafe_allow_html=True)
        # Show food images and order buttons if available
        foods = message.get("foods", [])
        ai_response = message["content"]
        filtered_foods = extract_food_names(ai_response, foods)
        for food in filtered_foods:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.markdown(
                    f"""
                    <div class="food-card">
                        <div class="food-card-main">
                            <img src="{food.get('image_url', '')}" alt="{food['name']}">
                            <div class="food-card-content">
                                <div class="food-card-header">
                                    <div class="food-card-title">{food['name']}</div>
                                    <div class="food-card-price">{food.get('price', 'Price N/A')}</div>
                                </div>
                                <div class="food-card-desc">{food['description']}</div>
                            </div>
                        </div>
                        <div class="food-card-footer">
                            <div class="quantity-selector">
                                <label>Quantity:</label>
                                <input type="number" min="1" value="1" id="quantity_{food['id']}" />
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            
            # Order button and success message handling
            with col2:
                quantity = st.number_input(f"Quantity for {food['name']}", min_value=1, value=1, key=f"quantity_{food['id']}")
                if st.button(f"Order", key=f"order_{food['id']}"):
                    st.success(f"🎉 Successfully ordered {quantity} {food['name']}(s)!")
                    time.sleep(2)  # Show success message for 2 seconds

# Input area
# Sticky input bar with input and button side by side
# Input form inside sticky bar
with st.form(key="input_form", clear_on_submit=True):
    st.markdown('''<div class="sticky-input-bar"><div class="input-wrapper">''', unsafe_allow_html=True)

    col1, col2 = st.columns([5, 1])
    with col1:
        user_input = st.text_input(
            "",
            placeholder="What are you in the mood for?",
            key="user_input",
            label_visibility="collapsed"
        )
    with col2:
        send_clicked = st.form_submit_button("Send", use_container_width=True)

    st.markdown("</div></div>", unsafe_allow_html=True)



# Handle user input
if send_clicked and user_input:
    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})

    # Get AI response
    with st.spinner(""):
        response, retrieved_foods = get_recommendations(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response, "foods": retrieved_foods})
    
    # Rerun to update the chat
    st.rerun() 