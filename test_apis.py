import os
from dotenv import load_dotenv
import requests
from datetime import datetime
import pytz

# Load environment variables
load_dotenv()

def test_weather_api():
    """Test the OpenWeatherMap API"""
    api_key = os.getenv("WEATHER_API_KEY")
    if not api_key:
        print("❌ Weather API key not found in .env file")
        return

    print(f"\nTesting Weather API with key: {api_key[:5]}...{api_key[-5:] if len(api_key) > 10 else ''}")
    
    try:
        # Test API call for Hyderabad
        response = requests.get(
            "http://api.openweathermap.org/data/2.5/weather",
            params={
                'q': 'Hyderabad,IN',
                'appid': api_key,
                'units': 'metric'
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print("\n✅ Weather API Test Successful!")
            print(f"Location: {data['name']}")
            print(f"Temperature: {data['main']['temp']}°C")
            print(f"Weather: {data['weather'][0]['description']}")
            print(f"Humidity: {data['main']['humidity']}%")
        else:
            print(f"\n❌ Weather API Error: {response.status_code}")
            error_data = response.json()
            print(f"Error Message: {error_data.get('message', 'No message provided')}")
            
            if response.status_code == 401:
                print("\nPossible solutions:")
                print("1. Check if your API key is correct")
                print("2. Wait 2 hours after creating a new API key")
                print("3. Verify your API key in OpenWeatherMap dashboard")
                print("4. Make sure there are no spaces or quotes in your .env file")
            elif response.status_code == 404:
                print("\nCity not found. Check if 'Hyderabad,IN' is the correct format")
            else:
                print(f"Full error response: {error_data}")
    except Exception as e:
        print(f"\n❌ Weather API Test Failed: {str(e)}")
        print("\nTroubleshooting steps:")
        print("1. Check your internet connection")
        print("2. Verify your API key is correctly set in .env file")
        print("3. Make sure you're using the latest API key from OpenWeatherMap")
        print("4. Wait 2 hours after creating a new API key before testing")

def test_holiday_api():
    """Test the Calendarific API"""
    api_key = os.getenv("HOLIDAY_API_KEY")
    if not api_key:
        print("❌ Holiday API key not found in .env file")
        return

    try:
        # Get current date
        current_date = datetime.now()
        
        # Test API call for current month
        response = requests.get(
            "https://calendarific.com/api/v2/holidays",
            params={
                'api_key': api_key,
                'country': 'IN',
                'year': current_date.year,
                'month': current_date.month
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            holidays = data.get('response', {}).get('holidays', [])
            
            print("\n✅ Holiday API Test Successful!")
            print(f"Found {len(holidays)} holidays for {current_date.strftime('%B %Y')}")
            
            # Print next 3 upcoming holidays
            print("\nUpcoming Holidays:")
            for holiday in holidays[:3]:
                print(f"- {holiday['name']} ({holiday['date']['iso']})")
        else:
            print(f"❌ Holiday API Error: {response.status_code}")
            print(response.text)
    except Exception as e:
        print(f"❌ Holiday API Test Failed: {str(e)}")

if __name__ == "__main__":
    print("Testing APIs...")
    test_weather_api()
    test_holiday_api() 