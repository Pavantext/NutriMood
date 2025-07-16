import os
from dotenv import load_dotenv
from utils.embeddings import get_embedding
from utils.pinecone_helper import get_new_index
import google.generativeai as genai
import requests
from datetime import datetime
import pytz

load_dotenv()

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

# Configure Google Generative AI
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

user_input = input("What are you in the mood for? ")

# Get contextual information
context = get_contextual_info()

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

# Format contextual information
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

# Generate with Gemini
prompt = f"""
User query: {user_input}

Current Context:
{context_text}

Here are relevant food items from the database:
{retrieved_text}

Based on the user's mood, current time, weather conditions, and any upcoming holidays, suggest the best option(s) in a friendly and intelligent way. Consider:
1. Time of day (breakfast, lunch, dinner, snack)
2. Weather conditions (hot, cold, rainy)
3. Any special occasions or holidays
4. User's mood and preferences

Your recommendation:
"""

model = genai.GenerativeModel('gemini-2.0-flash')
response = model.generate_content(prompt)

print("\n🍽️ Recommended Food:")
print(response.text)
