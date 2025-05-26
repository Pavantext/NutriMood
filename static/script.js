// Chat functionality
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const foodCardTemplate = document.getElementById('food-card-template');
    const newChatButton = document.querySelector('.new-chat-button');

    let chatHistory = [];

    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Handle new chat button
    newChatButton.addEventListener('click', function() {
        chatHistory = [];
        chatMessages.innerHTML = `
            <div class="message bot">
                <div class="message-content">
                    <h2 style="margin-bottom: 1rem; color: var(--text-color);">Welcome to Food AI Chat</h2>
                    <p style="color: var(--text-color); opacity: 0.8;">I'm your personal food recommendation assistant. I can help you discover dishes based on your preferences, mood, or dietary requirements. How can I assist you today?</p>
                </div>
            </div>
        `;
        userInput.value = '';
        userInput.style.height = 'auto';
    });

    // Handle example clicks
    document.querySelectorAll('.tips-list li').forEach(tip => {
        tip.addEventListener('click', function() {
            const exampleText = this.textContent.trim();
            if (exampleText.startsWith('"') && exampleText.endsWith('"')) {
                userInput.value = exampleText.slice(1, -1);
                userInput.dispatchEvent(new Event('input'));
                chatForm.dispatchEvent(new Event('submit'));
            }
        });
    });

    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        const message = userInput.value.trim();
        if (!message) return;

        // Add user message to chat
        addMessage(message, 'user');
        userInput.value = '';
        userInput.style.height = 'auto';

        // Show typing indicator
        const typingIndicator = addTypingIndicator();

        try {
            // Send message to backend
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    message: message,
                    history: chatHistory
                })
            });

            const data = await response.json();
            
            // Remove typing indicator
            typingIndicator.remove();

            // Add bot response to chat
            addMessage(data.response, 'bot');

            // Add food cards if any
            if (data.foods && data.foods.length > 0) {
                addFoodCards(data.foods);
            }

            // Update chat history
            chatHistory.push({
                role: 'user',
                content: message
            });
            chatHistory.push({
                role: 'assistant',
                content: data.response
            });

            // Scroll to bottom
            scrollToBottom();

        } catch (error) {
            console.error('Error:', error);
            typingIndicator.remove();
            addMessage('Sorry, I encountered an error. Please try again.', 'bot');
        }
    });

    function addMessage(content, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Convert markdown-like syntax to HTML
        const formattedContent = content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/`(.*?)`/g, '<code>$1</code>')
            .replace(/\n/g, '<br>');
        
        messageContent.innerHTML = formattedContent;
        
        messageDiv.appendChild(messageContent);
        chatMessages.appendChild(messageDiv);
        
        scrollToBottom();
    }

    function addTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'message bot';
        indicator.innerHTML = `
            <div class="message-content">
                <div class="typing-indicator">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        chatMessages.appendChild(indicator);
        scrollToBottom();
        return indicator;
    }

    function addFoodCards(foods) {
        const foodCardsContainer = document.createElement('div');
        foodCardsContainer.className = 'message bot';

        foods.forEach(food => {
            const foodCard = foodCardTemplate.content.cloneNode(true);
            
            // Fill in food card details
            foodCard.querySelector('.food-card-title').textContent = food.name;
            foodCard.querySelector('.food-card-price').textContent = food.price || 'Price N/A';
            foodCard.querySelector('.food-card-description').textContent = food.description;
            
            const foodImage = foodCard.querySelector('.food-card-image');
            foodImage.src = food.image_url || 'default-food-image.jpg';
            foodImage.alt = food.name;

            // Add order button functionality
            const orderButton = foodCard.querySelector('.order-button');
            const quantityInput = foodCard.querySelector('.quantity-input');

            orderButton.addEventListener('click', () => {
                const quantity = parseInt(quantityInput.value);
                handleOrder(food, quantity);
            });

            foodCardsContainer.appendChild(foodCard);
        });

        chatMessages.appendChild(foodCardsContainer);
        scrollToBottom();
    }

    async function handleOrder(food, quantity) {
        try {
            const response = await fetch('/order', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    food_id: food.id,
                    quantity: quantity
                })
            });

            const data = await response.json();
            
            if (data.success) {
                showOrderSuccess(food.name, quantity);
            } else {
                showOrderError();
            }
        } catch (error) {
            console.error('Error placing order:', error);
            showOrderError();
        }
    }

    function showOrderSuccess(foodName, quantity) {
        const successMessage = `🎉 Successfully ordered ${quantity} ${foodName}(s)!`;
        addMessage(successMessage, 'bot');
    }

    function showOrderError() {
        const errorMessage = 'Sorry, there was an error processing your order. Please try again.';
        addMessage(errorMessage, 'bot');
    }

    function scrollToBottom() {
        chatMessages.scrollTop = chatMessages.scrollHeight;
    }

    // Handle Enter key in textarea
    userInput.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            chatForm.dispatchEvent(new Event('submit'));
        }
    });
});

// Add some nice animations and transitions
document.addEventListener('DOMContentLoaded', function() {
    // Animate welcome message
    const welcomeMessage = document.querySelector('.message.bot');
    welcomeMessage.style.opacity = '0';
    setTimeout(() => {
        welcomeMessage.style.transition = 'opacity 0.5s ease-in-out';
        welcomeMessage.style.opacity = '1';
    }, 100);

    // Animate sidebar tips
    const tips = document.querySelectorAll('.tips-list li');
    tips.forEach((tip, index) => {
        tip.style.opacity = '0';
        tip.style.transform = 'translateX(-20px)';
        setTimeout(() => {
            tip.style.transition = 'all 0.3s ease-in-out';
            tip.style.opacity = '1';
            tip.style.transform = 'translateX(0)';
        }, 200 + (index * 100));
    });
}); 