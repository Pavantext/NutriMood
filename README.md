# Food AI - Intelligent Food Recommendation System 🍽️

An AI-powered food recommendation system that provides personalized food suggestions based on user preferences, weather conditions, and time of day. The system uses natural language processing to understand user queries and provide contextual recommendations.

## Features 🌟

- **Intelligent Chat Interface**: Natural conversation with an AI chef for food recommendations
- **Context-Aware Recommendations**: 
  - Weather-based suggestions
  - Time-of-day appropriate meals
  - Holiday and special occasion recommendations
- **Personalized Experience**:
  - User preference learning
  - Dietary restriction consideration
  - Price range preferences
  - Spice level preferences
- **Interactive UI**:
  - Real-time chat with typing animation
  - Food cards with images and descriptions
  - Quick action buttons for common queries
  - Mobile-responsive design
- **Smart Follow-up Questions**: Contextual follow-up suggestions based on previous recommendations

## Tech Stack 💻

- **Backend**:
  - Python Flask
  - Google Gemini AI
  - Pinecone Vector Database
  - SQLAlchemy ORM
  - PostgreSQL Database

- **Frontend**:
  - HTML5
  - CSS3
  - JavaScript (Vanilla)
  - Responsive Design

- **APIs**:
  - Google Generative AI
  - OpenWeather API
  - Calendarific API (for holidays)

## Setup and Installation 🚀

1. Clone the repository:
```bash
git clone https://github.com/yourusername/food-ai.git
cd food-ai
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables in `.env`:
```
SECRET_KEY=your_secret_key
GOOGLE_API_KEY=your_google_api_key
WEATHER_API_KEY=your_weather_api_key
HOLIDAY_API_KEY=your_holiday_api_key
DATABASE_URL=your_database_url
```

5. Initialize the database:
```bash
flask db init
flask db migrate
flask db upgrade
```

6. Run the application:
```bash
python app.py
```

## Usage 📱

1. Open your browser and navigate to `http://localhost:5000`
2. Enter your name to start a chat session
3. Toggle weather and time-based recommendations if desired
4. Start chatting with the AI chef about food recommendations
5. Use quick action buttons for common queries
6. Click on food cards to add items to your order

## Features in Detail 🔍

### Smart Recommendations
- Considers weather conditions for appropriate food suggestions
- Time-aware recommendations (breakfast, lunch, dinner, snacks)
- Holiday and special occasion awareness
- Dietary restriction consideration
- Price range preferences

### Interactive Chat
- Natural language processing for understanding user queries
- Context-aware responses
- Follow-up question suggestions
- Real-time typing animation
- Emoji reactions

### User Interface
- Clean and modern design
- Mobile-responsive layout
- Food cards with images and descriptions
- Quick action buttons
- Toast notifications for actions

## Contributing 🤝

Contributions are welcome! Please feel free to submit a Pull Request.

## License 📄

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- Google Gemini AI for natural language processing
- OpenWeather API for weather data
- Calendarific API for holiday information
- All contributors and users of the project

## Contact 📧

For any queries or suggestions, please open an issue in the repository.

---
Made with ❤️ by [Your Name]