from flask import Flask, render_template, request
import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper_new import get_new_index
import google.generativeai as genai

load_dotenv()

app = Flask(__name__)

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

def get_recommendation(user_input):
    # Embed the user input
    query_embedding = get_embedding(user_input)

    # Query Pinecone
    index = get_new_index()
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

    Suggest the best option(s) in a friendly and intelligent way:
    """

    model = genai.GenerativeModel('gemini-1.5-flash')
    response = model.generate_content(prompt)
    return response.text

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/recommend', methods=['POST'])
def recommend():
    user_input = request.form['query']
    recommendation = get_recommendation(user_input)
    return render_template('results.html', recommendation=recommendation)

if __name__ == '__main__':
    app.run(debug=True)
