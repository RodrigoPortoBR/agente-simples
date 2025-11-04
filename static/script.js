document.addEventListener('DOMContentLoaded', function() {
    const messageArea = document.getElementById('messageArea');
    const chatForm = document.getElementById('chatForm');
    const messageInput = document.getElementById('messageInput');
    const typingIndicator = document.getElementById('typingIndicator');

    // Auto-scroll chat to bottom
    function scrollToBottom() {
        messageArea.scrollTop = messageArea.scrollHeight;
    }

    // Add a new message to the chat
    function addMessage(content, type = 'user') {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${type}`;
        
        const contentDiv = document.createElement('div');
        contentDiv.className = 'message-content';
        contentDiv.innerHTML = content;
        
        messageDiv.appendChild(contentDiv);
        messageArea.appendChild(messageDiv);
        scrollToBottom();
    }

    // Show/hide typing indicator
    function setTypingIndicator(visible) {
        typingIndicator.classList.toggle('d-none', !visible);
    }

    // Handle form submission
    chatForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const message = messageInput.value.trim();
        if (!message) return;

        // Clear input
        messageInput.value = '';

        // Add user message
        addMessage(message, 'user');

        // Show typing indicator
        setTypingIndicator(true);

        try {
            const response = await fetch('/chat', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ message })
            });

            const data = await response.json();
            
            // Hide typing indicator
            setTypingIndicator(false);

            if (response.ok) {
                // Add system response
                addMessage(data.response, 'system');
            } else {
                // Add error message
                addMessage(
                    'Desculpe, ocorreu um erro ao processar sua mensagem. Por favor, tente novamente.',
                    'error'
                );
            }
        } catch (error) {
            setTypingIndicator(false);
            addMessage(
                'Erro de conexão. Por favor, verifique sua internet e tente novamente.',
                'error'
            );
        }
    });

    // Enable/disable submit button based on input
    messageInput.addEventListener('input', function() {
        const submitButton = chatForm.querySelector('button[type="submit"]');
        submitButton.disabled = !this.value.trim();
    });

    // Initial state - disable submit if empty
    const submitButton = chatForm.querySelector('button[type="submit"]');
    submitButton.disabled = !messageInput.value.trim();
});