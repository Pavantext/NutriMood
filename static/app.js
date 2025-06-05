// Chat System Core Functionality
const chatInterface = (() => {
    // Configuration
    const config = {
        chefResponses: {
            greetings: ["Bon appétit!", "Let's cook up something delicious!", "Yum yum!"],
            suggestions: {
                spicy: ["Spicy Chicken Curry", "Szechuan Noodles", "Hot Wings"],
                vegetarian: ["Paneer Tikka", "Vegetable Biryani", "Falafel Wrap"],
                breakfast: ["Masala Dosa", "Poha", "Upma"]
            }
        },
        responseDelay: 1500 // 1.5 seconds
    };

    // DOM Elements
    const elements = {
        input: document.querySelector('.message-input'),
        sendBtn: document.querySelector('.send-btn'),
        chatMessages: document.querySelector('.chat-messages'),
        suggestions: document.querySelectorAll('.suggestion-btn'),
        actionBtns: document.querySelectorAll('.action-btn')
    };

    // Message Handling
    const createMessageElement = (text, isUser = false) => {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message${isUser ? ' user-message' : ''}`;
        
        messageDiv.innerHTML = `
            ${!isUser ? `
            <div class="chef-avatar">
                <svg class="icon" viewBox="0 0 24 24">
                    <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
                    <line x1="3" y1="6" x2="21" y2="6"></line>
                    <path d="M16 10a4 4 0 0 1-8 0"></path>
                </svg>
            </div>` : ''}
            <div class="message-content">
                ${!isUser ? '<div class="chef-name">Chef</div>' : ''}
                <div class="message-bubble">
                    <div class="message-text">${text}</div>
                    <div class="message-timestamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
                </div>
            </div>
        `;
        return messageDiv;
    };

    // Process User Input
    const processMessage = async (message) => {
        try {
            const response = await fetch('/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded',
                },
                body: `query=${encodeURIComponent(message)}`
            });
            const result = await response.text();
            return result;
        } catch (error) {
            console.error('Error:', error);
            return "Sorry, I'm having trouble connecting to the kitchen. Please try again later!";
        }
    };

    // Simulate Chef Response
    const simulateChefResponse = async (message) => {
        const typingIndicator = createMessageElement('<div class="typing-indicator"></div>');
        elements.chatMessages.appendChild(typingIndicator);
        
        try {
            const response = await processMessage(message);
            typingIndicator.remove();
            elements.chatMessages.appendChild(createMessageElement(response));
        } catch (error) {
            typingIndicator.remove();
            elements.chatMessages.appendChild(createMessageElement("Oops! The chef is busy right now. Please try again later."));
        }
        
        elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
    };

    // Event Handlers
    const handleSendMessage = () => {
        const message = elements.input.value.trim();
        if (message) {
            elements.chatMessages.appendChild(createMessageElement(message, true));
            elements.input.value = '';
            simulateChefResponse(message);
            elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        }
    };

    const handleSuggestionClick = (btn) => {
        elements.input.value = btn.textContent;
        handleSendMessage();
    };

    const handleActionButton = (action) => {
        switch(action) {
            case 'Reset':
                elements.chatMessages.innerHTML = document.querySelector('.message').outerHTML;
                break;
            case 'View My Data':
                // Add actual data fetching logic here
                elements.chatMessages.appendChild(createMessageElement("Your preferences: Spicy food lover, Vegetarian"));
                break;
            case 'View Menu':
                // Add actual menu fetching logic here
                elements.chatMessages.appendChild(createMessageElement("Today's Special: Butter Chicken, Dal Makhani, Naan"));
                break;
        }
    };

    // Initialize Event Listeners
    const init = () => {
        elements.sendBtn.addEventListener('click', handleSendMessage);
        elements.input.addEventListener('keypress', (e) => e.key === 'Enter' && handleSendMessage());
        
        elements.suggestions.forEach(btn => {
            btn.addEventListener('click', () => handleSuggestionClick(btn));
        });

        elements.actionBtns.forEach(btn => {
            btn.addEventListener('click', () => handleActionButton(btn.textContent.trim()));
        });
    };

    return { init };
})();

// Initialize the chat interface
document.addEventListener('DOMContentLoaded', chatInterface.init);

document.addEventListener("DOMContentLoaded", function() {
    const nameModal = document.getElementById("nameModal");
    const nameInput = document.getElementById("nameInput");
    const saveNameBtn = document.getElementById("saveNameBtn");
    const usernameDiv = document.querySelector(".username");

    // Function to set username in sidebar
    function setUsername(name) {
        usernameDiv.textContent = name;
        // Update welcome message
        const welcomeSpan = document.getElementById('welcomeUsername');
        if (welcomeSpan) {
            welcomeSpan.textContent = name;
        }
    }

    // Check if name is in localStorage
    let storedName = localStorage.getItem("username");
    if (!storedName) {
        nameModal.style.display = "flex";
    } else {
        setUsername(storedName);
    }

    // Save name and update UI
    saveNameBtn.addEventListener("click", function() {
        const name = nameInput.value.trim();
        if (name) {
            localStorage.setItem("username", name);
            setUsername(name);
            nameModal.style.display = "none";
        }
    });

    // Optional: allow Enter key to submit
    nameInput.addEventListener("keydown", function(e) {
        if (e.key === "Enter") {
            saveNameBtn.click();
        }
    });
});