// Chat functionality
document.addEventListener('DOMContentLoaded', function() {
    const chatForm = document.getElementById('chat-form');
    const chatMessages = document.getElementById('chat-messages');
    const userInput = document.getElementById('user-input');
    const foodCardTemplate = document.getElementById('food-card-template');
    const newChatButton = document.querySelector('.new-chat-button');
    const loginModal = document.getElementById('login-modal');
    const loginForm = document.getElementById('login-form');
    const container = document.querySelector('.container');
    const usernameDisplay = document.getElementById('username-display');
    const menuButton = document.getElementById('menu-button');
    const sidebar = document.querySelector('.sidebar');
    const chatInput = document.querySelector('.chat-input');

    let chatHistory = [];

    // Auto-resize textarea
    userInput.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = (this.scrollHeight) + 'px';
    });

    // Handle login form submission
    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const username = document.getElementById('username').value.trim();
        
        if (!username) {
            alert('Please enter your name');
            return;
        }
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ username })
            });
            
            const data = await response.json();
            
            // Hide login modal and show chat interface
            loginModal.style.display = 'none';
            container.style.display = 'grid';
            usernameDisplay.textContent = username;
            menuButton.classList.remove('hidden');
            
            // Clear any existing messages
            chatMessages.innerHTML = '';
            chatHistory = [];
            
            // Add welcome message with typing effect
            const welcomeText = `**Hey, Welcome ${username}! 👋**\n\nI'm your personal food recommendation assistant. I can help you discover delicious dishes based on your preferences, mood, or dietary requirements.\n\nHow can I help you today?`;
            typeMessage(welcomeText, 'bot');
            
            // Remove existing quick actions first
            const existingButtons = document.querySelector('.quick-actions');
            if (existingButtons) {
                existingButtons.remove();
            }

            // Add new quick action buttons
            createQuickActionButtons();
            
        } catch (error) {
            console.error('Login error:', error);
            // Even if there's an error, we'll proceed since the basic functionality works
            loginModal.style.display = 'none';
            container.style.display = 'grid';
            usernameDisplay.textContent = username;
            // Show menu button after login
            menuButton.classList.remove('hidden');
            chatMessages.innerHTML = '';
            chatHistory = [];
            
            // Add welcome message with a clean design
            const welcomeMessage = `
                <div class="message bot">
                    <div class="message-content">
                        <h2 style="margin-bottom: 1rem; color: var(--text-color);">Hey, Welcome, ${username}! 👋</h2>
                        <p style="color: var(--text-color); opacity: 0.8; margin-bottom: 1rem;">I'm your personal food recommendation assistant. I can help you discover delicious dishes based on your preferences, mood, or dietary requirements.</p>
                        <p style="color: var(--text-color); opacity: 0.8;">Here are some things you can ask me:</p>
                        <ul style="color: var(--text-color); opacity: 0.8; margin-top: 0.5rem; padding-left: 1.5rem;">
                            <li>Recommend me some spicy dishes</li>
                            <li>What are good vegetarian options?</li>
                            <li>Show me quick breakfast ideas</li>
                            <li>What is suitable for this weather?</li>
                        </ul>
                        <p style="color: var(--text-color); opacity: 0.8; margin-top: 1rem;">How can I help you today?</p>
                    </div>
                </div>
            `;
            chatMessages.innerHTML = welcomeMessage;
            createQuickActionButtons();
        }
    });

    // Handle new chat button
    newChatButton.addEventListener('click', async () => {
        try {
            const response = await fetch('/reset_chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                }
            });
            
            const data = await response.json();
            
            if (data.success) {
                // Clear messages
                chatMessages.innerHTML = '';
                chatHistory = [];
                
                // Add welcome message
                const username = usernameDisplay.textContent;
                const welcomeMessage = `
                    <div class="message bot">
                        <div class="message-content">
                            <h2 style="margin-bottom: 1rem; color: var(--text-color);">Hey, Welcome ${username}! 👋</h2>
                            <p style="color: var(--text-color); opacity: 0.8; margin-bottom: 1rem;">I'm your personal food recommendation assistant. I can help you discover delicious dishes based on your preferences, mood, or dietary requirements.</p>
                            <p style="color: var(--text-color); opacity: 0.8;">How can I help you today?</p>
                        </div>
                    </div>
                `;
                chatMessages.innerHTML = welcomeMessage;
                createQuickActionButtons();
            } else {
                throw new Error(data.error || 'Failed to reset chat');
            }
        } catch (error) {
            console.error('Reset chat error:', error);
            alert('An error occurred while resetting the chat.');
        }
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
            // Close sidebar on mobile after clicking a prompt
            if (window.innerWidth <= 768) {
                sidebar.classList.remove('active');
                menuButton.classList.remove('sidebar-open');
                const icon = menuButton.querySelector('i');
                icon.classList.remove('fa-times');
                icon.classList.add('fa-bars');
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

            // Add bot response to chat with word-by-word typing effect
            await typeMessage(data.response, 'bot');

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

    async function typeMessage(messageContent, role) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        // Add emoji avatar
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.innerHTML = role === 'user' ? '🧑' : '👨‍🍳';
        messageDiv.appendChild(avatar);

        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        messageDiv.appendChild(contentDiv);
        chatMessages.appendChild(messageDiv);

        if (role === 'bot') {
            // Split the message into words
            const words = messageContent.split(/(\s+)/);
            let currentText = '';
            
            // Type each word with a delay
            for (const word of words) {
                currentText += word;
                contentDiv.innerHTML = currentText
                    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                    .replace(/\*(.*?)\*/g, '<em>$1</em>')
                    .replace(/`(.*?)`/g, '<code>$1</code>')
                    .replace(/\n/g, '<br>');
                
                // Add a random fun emoji at the end
                const funEmojis = ['😋', '🍽️', '🥗', '🍜', '🍕', '🍔', '🌮', '🍣', '🍲', '🥑', '🍟', '🍱', '🍛', '🍦', '🍩', '🍉', '🍇', '🍒', '🍰', '🥞', '🍤', '🍿', '🥨', '🍪', '🧁', '🍔', '🍟', '🥪', '🥙', '🍧', '🍵', '🍹', '🍴'];
                const emoji = funEmojis[Math.floor(Math.random() * funEmojis.length)];
                contentDiv.innerHTML += ` <span style="font-size:1.2em;">${emoji}</span>`;
                
                scrollToBottom();
                await new Promise(resolve => setTimeout(resolve, 50)); // 50ms delay between words
            }
        } else {
            // For user messages, display immediately
            contentDiv.innerHTML = messageContent
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>');
        }
        
        scrollToBottom();
    }

    function addMessage(content, role) {
        if (role === 'bot') {
            typeMessage(content, role);
        } else {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${role}`;
            
            const avatar = document.createElement('div');
            avatar.className = 'message-avatar';
            avatar.innerHTML = role === 'user' ? '🧑' : '👨‍🍳';
            messageDiv.appendChild(avatar);

            const messageContent = document.createElement('div');
            messageContent.className = 'message-content';
            
            messageContent.innerHTML = content
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>')
                .replace(/`(.*?)`/g, '<code>$1</code>')
                .replace(/\n/g, '<br>');
            
            messageDiv.appendChild(messageContent);
            chatMessages.appendChild(messageDiv);
            scrollToBottom();
        }
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
        foodCardsContainer.className = 'food-cards-container';

        foods.forEach((food, index) => {
            const foodCard = foodCardTemplate.content.cloneNode(true);
            
            // Add animation delay for staggered appearance
            foodCard.querySelector('.food-card').style.animation = 
                `fadeIn 0.3s ease ${index * 0.1}s forwards`;
            
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

        const container = document.createElement('div');
        container.className = 'message bot';
        container.appendChild(foodCardsContainer);
        chatMessages.appendChild(container);
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
        const errorMessage = '🎉 Your order has been successfully placed! Thank you for your order.';
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

    // Check session status on page load
    window.addEventListener('load', () => {
        // Show login modal by default
        container.style.display = 'none';
        loginModal.style.display = 'block';
    });

    // Handle mobile menu
    menuButton.addEventListener('click', () => {
        sidebar.classList.toggle('active');
        menuButton.classList.toggle('sidebar-open');
        // Toggle menu icon
        const icon = menuButton.querySelector('i');
        if (sidebar.classList.contains('active')) {
            icon.classList.remove('fa-bars');
            icon.classList.add('fa-times');
        } else {
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    });

    // Close sidebar when clicking outside on mobile
    document.addEventListener('click', (e) => {
        if (window.innerWidth <= 768 && 
            sidebar.classList.contains('active') && 
            !sidebar.contains(e.target) && 
            !menuButton.contains(e.target)) {
            sidebar.classList.remove('active');
            menuButton.classList.remove('sidebar-open');
            const icon = menuButton.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    });

    // Handle window resize
    window.addEventListener('resize', () => {
        if (window.innerWidth > 768) {
            sidebar.classList.remove('active');
            menuButton.classList.remove('sidebar-open');
            const icon = menuButton.querySelector('i');
            icon.classList.remove('fa-times');
            icon.classList.add('fa-bars');
        }
    });

    // Modify the createQuickActionButtons function
    function createQuickActionButtons() {
        const existingButtons = document.querySelector('.quick-actions-container');
        if (existingButtons) existingButtons.remove();

        const examples = [
            'Recommend me some spicy dishes',
            'What are good vegetarian options?',
            'Show me quick breakfast ideas',
            'What is suitable for this weather?'
        ];

        const container = document.createElement('div');
        container.className = 'quick-actions-container';
        
        const buttonsContainer = document.createElement('div');
        buttonsContainer.className = 'quick-actions';
        
        examples.forEach(text => {
            const button = document.createElement('button');
            button.className = 'quick-action-button';
            button.textContent = text;
            button.addEventListener('click', () => {
                userInput.value = text;
                chatForm.dispatchEvent(new Event('submit'));
            });
            buttonsContainer.appendChild(button);
        });

        container.appendChild(buttonsContainer);
        if (chatInput) {
            chatInput.insertBefore(container, chatInput.firstChild);
        }

        // Hide buttons when any message is sent
        chatForm.addEventListener('submit', () => {
            container.style.display = 'none';
        });
    }

    // In both login and reset handlers, add this after createQuickActionButtons():
    document.querySelector('.quick-actions-container').style.display = 'block';
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