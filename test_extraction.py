import re

# Copied directly from app.py (after the bug fix was applied)
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
    
    recommended_foods_set = set() # Changed variable name to avoid confusion
    
    # First look for actively recommended foods
    for pattern in recommendation_patterns:
        matches = re.finditer(pattern, ai_response, re.IGNORECASE)
        for match in matches:
            food_name_match = match.group('food').strip().lower() # Renamed for clarity
            # Check if this food name or part of it matches our food list
            for known_food_key in food_names: # known_food_key is lowercase name from food_names dict
                if known_food_key in food_name_match: # Check if the known food is part of the extracted phrase
                    recommended_foods_set.add(known_food_key)
    
    # If no recommended foods found through patterns, fall back to direct mentions
    if not recommended_foods_set:
        for food_name_key in food_names: 
            pattern = r'\b{}\b'.format(re.escape(food_name_key))
            if re.search(pattern, ai_response, re.IGNORECASE):
                recommended_foods_set.add(food_name_key)
    
    # Convert back to food objects
    return [food_names[name_key] for name_key in recommended_foods_set]


# Test data as per subtask description
foods_for_extraction_test = [
    {'id': '1', 'name': 'Masala Dosa', 'description': 'Crispy crepe with potato filling', 'region': 'South India', 'mood': 'Comforting', 'diet': 'Vegetarian', 'time': 'Breakfast'},
    {'id': '2', 'name': 'Dosa', 'description': 'Plain Dosa', 'region': 'South India', 'mood': 'Light', 'diet': 'Vegetarian', 'time': 'Breakfast'},
    {'id': '40', 'name': 'Rasam', 'description': 'Tangy soup', 'region': 'South India', 'mood': 'Comforting', 'diet': 'Vegetarian', 'time': 'Lunch'}
]

# Corrected AI response as per self-correction in prompt
ai_response_test = "The Masala Dosa is excellent. Some people also enjoy Rasam. We do not have a plain Dosa."

print("--- Test Extraction Script Start ---")
extracted_food_objects = extract_food_names(ai_response_test, foods_for_extraction_test)
extracted_names = [food['name'] for food in extracted_food_objects]

print(f"Original AI Response: \"{ai_response_test}\"")
print(f"Foods available: {[f['name'] for f in foods_for_extraction_test]}")
print(f"Extracted food names: {sorted(extracted_names)}") # Sorted for consistent output order
print("--- Test Extraction Script End ---")
