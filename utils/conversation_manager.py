import google.generativeai as genai
from typing import List, Dict, Any

class ConversationManager:
    def __init__(self):
        self.conversation_history: List[Dict[str, Any]] = []
        self.context_window = 5  # Number of previous exchanges to maintain

    def add_exchange(self, user_input: str, ai_response: str, retrieved_foods: List[Dict[str, Any]]) -> None:
        """Add a conversation exchange to the history"""
        self.conversation_history.append({
            "user_input": user_input,
            "ai_response": ai_response,
            "retrieved_foods": retrieved_foods
        })
        
        # Keep only the last N exchanges
        if len(self.conversation_history) > self.context_window:
            self.conversation_history.pop(0)

    def get_conversation_context(self) -> str:
        """Get formatted conversation history for context"""
        context = []
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

    def generate_contextual_prompt(self, user_input: str, retrieved_foods: List[Dict[str, Any]]) -> str:
        """Generate a prompt that includes conversation history and context"""
        # Format the retrieved foods
        retrieved_text = "\n".join([
            f"{item['name']}: {item['description']} (Region: {item['region']}, Mood: {item['mood']}, Time: {item['time']}, Diet: {item['diet']})"
            for item in retrieved_foods
        ])

        # Get conversation history
        conversation_context = self.get_conversation_context()

        # Create the full prompt
        prompt = f"""Previous conversation:
{conversation_context}

Current user query: {user_input}

Here are relevant food items from the database:
{retrieved_text}

Based on the conversation history and current query, respond in a friendly, conversational way as if you're a food expert having a chat.
Make your response personal and engaging, like you're talking to a friend.
Keep it concise but informative. Reference previous parts of the conversation if relevant.
If the user is asking a follow-up question, make sure to connect it with the previous context.
Do not use any HTML tags, div elements, or special formatting in your response.
Just provide a clean, plain text response that maintains continuity with the previous conversation:
"""
        return prompt

    def analyze_user_intent(self, user_input: str) -> Dict[str, Any]:
        """Analyze user input to understand intent and extract key information"""
        # Get recent context
        recent_foods = []
        if self.conversation_history:
            last_exchange = self.conversation_history[-1]
            recent_foods = last_exchange.get('retrieved_foods', [])

        # Analyze if this is a follow-up question
        is_followup = any(phrase in user_input.lower() for phrase in [
            "what about", "how about", "and", "what else", "tell me more",
            "why", "which", "where", "when", "who", "how"
        ]) and self.conversation_history

        return {
            "is_followup": is_followup,
            "recent_foods": recent_foods,
            "mentioned_foods": [food['name'] for food in recent_foods]
        } 