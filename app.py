import streamlit as st
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_index
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
        background-color: #fafafa;
    }

    .block-container {
        max-width: 800px;
        margin: 0 auto;
        padding-bottom: 100px; /* Extra space for sticky input */
    }

    .stApp {
        overflow: hidden;
    }

    /* Chat message bubbles */
    .user-message {
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%);
        color: white;
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
        color: #2b313e;
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
        border-radius: 25px;
        padding: 0 20px;
        font-size: 15px;
        color: #2b313e;
        border: 2px solid #f0f0f0;
        background-color: white;
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

    .stButton > button {
        border-radius: 25px;
        padding: 0 24px;
        background: linear-gradient(135deg, #FF6B6B 0%, #FF8E8E 100%);
        color: white;
        font-weight: 600;
        border: none;
        height: 44px;
        min-width: 80px;
        cursor: pointer;
        transition: all 0.3s ease;
        box-shadow: 0 4px 15px rgba(255, 107, 107, 0.13);
    }

    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(255, 107, 107, 0.18);
    }

    /* Welcome box */
    .welcome-message {
        text-align: center;
        padding: 1rem;
        background: white;
        border-radius: 20px;
        box-shadow: 0 4px 15px rgba(0,0,0,0.05);
        margin-bottom: 0.5rem;
    }

    .welcome-message h1 {
        color: #FF6B6B;
        font-size: 1.3rem;
    }

    .welcome-message p {
        color: #666;
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

def clean_response(text):
    # Remove any HTML tags
    text = re.sub(r'<[^>]+>', '', text)
    # Remove any div elements
    text = re.sub(r'div', '', text)
    # Remove extra whitespace
    text = ' '.join(text.split())
    return text

# Function to get recommendations
def get_recommendations(user_input):
    # Embed the user input
    query_embedding = get_embedding(user_input)

    # Query Pinecone
    index = get_index()
    results = index.query(vector=query_embedding, top_k=5, include_metadata=True)
    matches = results['matches']
    retrieved_foods = [match['metadata'] for match in matches]

    # Format context for Gemini
    retrieved_text = "\n".join([
        f"{item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']})"
        for item in retrieved_foods
    ])

    # Generate with Gemini
    prompt = f"""
    User query: {user_input}

    Here are relevant food items from the database:
    {retrieved_text}

    Respond in a friendly, conversational way as if you're a food expert having a chat. 
    Make your response personal and engaging, like you're talking to a friend.
    Keep it concise but informative. Do not use any HTML tags, div elements, or special formatting in your response.
    Just provide a clean, plain text response:
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return clean_response(response.text)

# Sidebar
with st.sidebar:
    st.image("https://img.icons8.com/color/96/000000/restaurant.png", width=50)
    st.markdown("### Food AI Chat")
    st.markdown("""
    Your personal food recommendation assistant. 
    Chat naturally about what you're craving!
    """)
    
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

# Input area
# Sticky input bar with input and button side by side
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
    st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner(""):
        response = get_recommendations(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})

    st.experimental_rerun()

    # Add user message to chat
    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # Get AI response
    with st.spinner(""):
        response = get_recommendations(user_input)
        st.session_state.messages.append({"role": "assistant", "content": response})
    
    # Rerun to update the chat
    st.experimental_rerun() 