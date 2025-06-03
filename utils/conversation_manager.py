import google.generativeai as genai
from typing import List, Dict, Any
from datetime import datetime
import json

class ConversationManager:
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.context_window = 10
        self.user_preferences = {
            'dietary_restrictions': [],
            'price_range': None,
            'meal_type': None,
            'cuisine_preferences': [],
            'spice_level': None
        }
        self.conversation_state = {
            'current_topic': None,
            'last_recommendations': [],
            'last_meal_type': None,
            'last_cuisine': None,
            'last_price_range': None,
            'last_dietary': None
        }
        self.model = genai.GenerativeModel('gemini-1.5-flash')
        self.safety_settings = {
            "HARASSMENT": "block_none",
            "HATE_SPEECH": "block_none",
            "SEXUALLY_EXPLICIT": "block_none",
            "DANGEROUS_CONTENT": "block_none"
        }
        self.generation_config = {
            "temperature": 0.7,
            "top_p": 0.8,
            "top_k": 40,
            "max_output_tokens": 1024,
        }

    def add_exchange(self, user_input: str, ai_response: str, retrieved_foods: List[Dict[str, Any]]) -> None:
        """Add a conversation exchange to the history and update conversation state"""
        self.conversation_history.append({
            "user_input": user_input,
            "ai_response": ai_response,
            "retrieved_foods": retrieved_foods,
            "timestamp": datetime.utcnow()
        })
        
        if len(self.conversation_history) > self.context_window:
            self.conversation_history.pop(0)

        # Update user preferences using AI
        self._update_user_preferences(user_input)
        
        # Update conversation state
        self._update_conversation_state(user_input, ai_response, retrieved_foods)

    def _update_conversation_state(self, user_input: str, ai_response: str, retrieved_foods: List[Dict[str, Any]]) -> None:
        """Update the conversation state using AI analysis"""
        # Extract context using AI
        context = self._extract_context_with_ai(user_input)
        
        # Update state based on AI analysis
        if context.get('meal_type'):
            self.conversation_state['last_meal_type'] = context['meal_type']
        if context.get('dietary'):
            self.conversation_state['last_dietary'] = context['dietary']
        if context.get('price_range'):
            self.conversation_state['last_price_range'] = context['price_range']
        if context.get('cuisine'):
            self.conversation_state['last_cuisine'] = context['cuisine']

        # Update last recommendations
        if retrieved_foods:
            self.conversation_state['last_recommendations'] = retrieved_foods

    def _extract_context_with_ai(self, text: str) -> Dict[str, Any]:
        """Use AI to extract context and preferences from text"""
        prompt = f"""Analyze the following text and extract relevant food-related context.
        Text: {text}
        
        Return a JSON object with these fields:
        - meal_type: "breakfast", "lunch", "dinner", "snack", or null
        - dietary: "vegetarian", "vegan", "non-vegetarian", or null
        - price_range: "low", "medium", "high", or null
        - cuisine: list of mentioned cuisines
        - time_of_day: "morning", "afternoon", "evening", "night", or null
        - mood: "casual", "formal", "quick", "relaxed", or null
        - occasion: "regular", "special", "celebration", or null
        
        Return ONLY the JSON object, no other text."""

        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"Error extracting context: {str(e)}")
            return {}

    def _update_user_preferences(self, user_input: str) -> None:
        """Update user preferences using AI analysis"""
        prompt = f"""Analyze the following user input and extract their food preferences. 
        Consider the entire conversation context and previous preferences.
        
        Previous preferences: {self.user_preferences}
        Conversation history: {self.get_conversation_context()}
        
        User input: {user_input}
        
        Extract and return ONLY a JSON object with these fields:
        - dietary_restrictions: list of dietary restrictions (e.g., ["vegetarian", "vegan"])
        - price_range: "low", "medium", or "high" based on their budget preferences
        - meal_type: "breakfast", "lunch", "dinner", or "snack"
        - cuisine_preferences: list of preferred cuisines
        - spice_level: "mild", "medium", or "spicy"
        - time_preference: "morning", "afternoon", "evening", "night"
        - occasion: "regular", "special", "celebration"
        - mood: "casual", "formal", "quick", "relaxed"
        
        If any field cannot be determined, use null or empty list.
        Return ONLY the JSON object, no other text."""

        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            preferences = json.loads(response.text)
            
            # Update only the fields that were determined
            for key, value in preferences.items():
                if value is not None and value != []:
                    self.user_preferences[key] = value
        except Exception as e:
            print(f"Error updating preferences: {str(e)}")

    def analyze_user_intent(self, user_input: str) -> Dict[str, Any]:
        """Use AI to analyze user intent and context with improved follow-up detection"""
        prompt = f"""Analyze this conversation and determine if it's a follow-up question.
        
        Previous conversation:
        {self.get_conversation_context()}
        
        Current conversation state:
        - Last meal type: {self.conversation_state['last_meal_type']}
        - Last dietary preference: {self.conversation_state['last_dietary']}
        - Last price range: {self.conversation_state['last_price_range']}
        - Last recommendations: {[food['name'] for food in self.conversation_state['last_recommendations']]}
        
        Current user input: {user_input}
        
        Return a JSON object with these fields:
        - is_followup: boolean indicating if this is a follow-up question
        - followup_type: one of ["clarification", "modification", "comparison", "continuation", "preference", "reference", "pronoun"] or null
        - context_references: list of any specific items or topics referenced from previous conversation
        - intent: brief description of what the user is trying to achieve
        - referenced_items: list of specific food items or preferences referenced from previous conversation
        - sentiment: "positive", "negative", or "neutral"
        - urgency: "high", "medium", or "low"
        - confidence: number between 0 and 1 indicating confidence in the analysis
        
        Return ONLY the JSON object, no other text."""

        try:
            response = self.model.generate_content(
                prompt,
                safety_settings=self.safety_settings,
                generation_config=self.generation_config
            )
            intent_analysis = json.loads(response.text)
            
            # Add user preferences and conversation state to the analysis
            intent_analysis['user_preferences'] = self.user_preferences
            intent_analysis['conversation_state'] = self.conversation_state
            
            return intent_analysis
        except Exception as e:
            print(f"Error analyzing intent: {str(e)}")
            return {
                "is_followup": False,
                "followup_type": None,
                "context_references": [],
                "intent": "unknown",
                "referenced_items": [],
                "sentiment": "neutral",
                "urgency": "medium",
                "confidence": 0.0,
                "user_preferences": self.user_preferences,
                "conversation_state": self.conversation_state
            }

    def generate_contextual_prompt(self, user_input: str, retrieved_foods: List[Dict[str, Any]]) -> str:
        """Generate a prompt that includes conversation history and context with improved follow-up handling"""
        # Format the retrieved foods
        retrieved_text = "\n".join([
            f"[ID:{item.get('id', 'N/A')}] {item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']}, Price: {item.get('price', 'N/A')})"
            for item in retrieved_foods
        ])

        # Get conversation history and analyze intent
        conversation_context = self.get_conversation_context()
        intent_analysis = self.analyze_user_intent(user_input)

        # Create the full prompt with improved context handling
        prompt = f"""You are a food expert having a natural conversation with a user about food recommendations.
        
        Previous conversation:
        {conversation_context}

        Current conversation state:
        - Last meal type: {self.conversation_state['last_meal_type']}
        - Last dietary preference: {self.conversation_state['last_dietary']}
        - Last price range: {self.conversation_state['last_price_range']}
        - Last recommendations: {[food['name'] for food in self.conversation_state['last_recommendations']]}

        Current user query: {user_input}

        User's intent and context:
        - Intent: {intent_analysis['intent']}
        - Is follow-up question: {intent_analysis['is_followup']}
        - Follow-up type: {intent_analysis['followup_type']}
        - Context references: {intent_analysis['context_references']}
        - Referenced items: {intent_analysis.get('referenced_items', [])}
        - Sentiment: {intent_analysis.get('sentiment', 'neutral')}
        - Urgency: {intent_analysis.get('urgency', 'medium')}
        - User preferences: {intent_analysis['user_preferences']}

        Available food items:
        {retrieved_text}

        Instructions:
        1. Respond naturally as if you're having a friendly conversation
        2. Consider the entire conversation context and user's preferences
        3. If it's a follow-up question:
           - Acknowledge the connection to previous context
           - Reference specific items or preferences mentioned earlier
           - Maintain consistency with previous recommendations
        4. Make personalized recommendations based on user's preferences and constraints
        5. Keep the response concise but informative
        6. Do not use any HTML tags or special formatting
        7. IMPORTANT: At the end of your response, add a line with the recommended food IDs in this format:
           [RECOMMENDED_FOODS:ID1,ID2,ID3]
           Only include IDs of foods you actually recommend in your response.
        
        Provide your response:"""

        return prompt

    def get_conversation_context(self) -> str:
        """Get formatted conversation history for context with improved state tracking"""
        context = []
        
        # Add user preferences if they exist
        preferences = []
        if self.user_preferences['dietary_restrictions']:
            preferences.append(f"Dietary restrictions: {', '.join(self.user_preferences['dietary_restrictions'])}")
        if self.user_preferences['price_range']:
            preferences.append(f"Price range: {self.user_preferences['price_range']}")
        if self.user_preferences['meal_type']:
            preferences.append(f"Preferred meal type: {self.user_preferences['meal_type']}")
        if self.user_preferences['spice_level']:
            preferences.append(f"Preferred spice level: {self.user_preferences['spice_level']}")
        
        if preferences:
            context.append("User preferences:")
            context.extend(preferences)
            context.append("")

        # Add conversation state
        state_info = []
        if self.conversation_state['last_meal_type']:
            state_info.append(f"Last discussed meal type: {self.conversation_state['last_meal_type']}")
        if self.conversation_state['last_dietary']:
            state_info.append(f"Last dietary preference: {self.conversation_state['last_dietary']}")
        if self.conversation_state['last_price_range']:
            state_info.append(f"Last price range: {self.conversation_state['last_price_range']}")
        
        if state_info:
            context.append("Current conversation state:")
            context.extend(state_info)
            context.append("")

        # Add conversation history
        for exchange in self.conversation_history:
            context.append(f"User: {exchange['user_input']}")
            context.append(f"Assistant: {exchange['ai_response']}")
            
            # Add relevant food items from previous exchanges
            foods = exchange.get('retrieved_foods', [])
            if foods:
                food_context = "\nRelevant foods discussed:\n" + "\n".join([
                    f"- {food['name']}: {food['description']}"
                    for food in foods
                ])
                context.append(food_context)
        
        return "\n".join(context) 