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

    // Simulate Chef Response
    const simulateChefResponse = (message) => {
        // Add typing indicator
        const typingIndicator = createMessageElement('<div class="typing-indicator"></div>');
        elements.chatMessages.appendChild(typingIndicator);
        
        setTimeout(() => {
            typingIndicator.remove();
            const response = processMessage(message);
            elements.chatMessages.appendChild(createMessageElement(response));
            elements.chatMessages.scrollTop = elements.chatMessages.scrollHeight;
        }, config.responseDelay);
    };

    // Process User Input
    const processMessage = (message) => {
        const lowerMsg = message.toLowerCase();
        let response = "I recommend trying: ";

        if (lowerMsg.includes('spicy')) {
            response += config.chefResponses.suggestions.spicy.join(', ');
        } else if (lowerMsg.includes('vegetarian')) {
            response += config.chefResponses.suggestions.vegetarian.join(', ');
        } else if (lowerMsg.includes('breakfast')) {
            response += config.chefResponses.suggestions.breakfast.join(', ');
        } else {
            response = "Let me think about that... Why not try one of our signature dishes?";
        }

        return response;
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

// Open menu in new tab when View Menu is clicked
document.addEventListener('DOMContentLoaded', function() {
    const viewMenuBtn = document.getElementById('viewMenuBtn');
    if (viewMenuBtn) {
        viewMenuBtn.addEventListener('click', function() {
            window.open('/menu', '_blank');
        });
    }
});

// Fetch and show menu grouped by category
async function fetchAndShowMenu() {
    const chatMessages = document.querySelector('.chat-messages');
    // Fetch menu data
    const res = await fetch('/menu-data');
    const menu = await res.json();

    // Group by category
    const grouped = {};
    menu.forEach(item => {
        if (!grouped[item.category]) grouped[item.category] = [];
        grouped[item.category].push(item);
    });

    // Build HTML
    let html = '<div><strong>Menu:</strong></div>';
    for (const [category, items] of Object.entries(grouped)) {
        html += `<div style="margin-top:12px;"><strong>${category}</strong><ul>`;
        items.forEach(item => {
            html += `<li><b>${item.name}</b>: ${item.description}</li>`;
        });
        html += '</ul></div>';
    }

    // Show in chat
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message';
    messageDiv.innerHTML = `
        <div class="chef-avatar">
            <svg class="icon" viewBox="0 0 24 24">
                <path d="M6 2L3 6v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2V6l-3-4z"></path>
                <line x1="3" y1="6" x2="21" y2="6"></line>
                <path d="M16 10a4 4 0 0 1-8 0"></path>
            </svg>
        </div>
        <div class="message-content">
            <div class="chef-name">Chef</div>
            <div class="message-bubble">
                <div class="message-text">${html}</div>
                <div class="message-timestamp">${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
        </div>
    `;
    chatMessages.appendChild(messageDiv);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}
