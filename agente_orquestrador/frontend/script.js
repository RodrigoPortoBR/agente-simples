// Gerar ID de sessão único
const sessionId = 'session_' + Math.random().toString(36).substr(2, 9);
const chatContainer = document.getElementById('chat-container');
const chatHistory = document.getElementById('chat-history');
const userInput = document.getElementById('user-input');
const sendBtn = document.getElementById('send-btn');
const typingIndicator = document.getElementById('typing-indicator');
const suggestionsGrid = document.getElementById('suggestions-grid');

// Ajustar altura do textarea automaticamente
userInput.addEventListener('input', function () {
    this.style.height = 'auto';
    this.style.height = (this.scrollHeight) + 'px';
    if (this.value === '') this.style.height = 'auto';
});

function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function sendSuggestion(text) {
    userInput.value = text;
    sendMessage();
}

async function sendMessage() {
    const message = userInput.value.trim();
    if (!message) return;

    // Limpar input e esconder sugestões
    userInput.value = '';
    userInput.style.height = 'auto';
    suggestionsGrid.style.display = 'none';

    // Adicionar mensagem do usuário
    appendMessage('user', message);

    // Mostrar indicador de digitando
    showTyping(true);
    sendBtn.disabled = true;

    try {
        const response = await fetch('/webhook/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: message,
                sessionId: sessionId
            })
        });

        const data = await response.json();

        if (data.success) {
            appendMessage('assistant', data.response);
        } else {
            appendMessage('assistant', 'Desculpe, ocorreu um erro ao processar sua mensagem.');
        }

    } catch (error) {
        console.error('Error:', error);
        appendMessage('assistant', 'Erro de conexão com o servidor.');
    } finally {
        showTyping(false);
        sendBtn.disabled = false;
        userInput.focus();
    }
}

function appendMessage(role, text) {
    const messageDiv = document.createElement('div');
    messageDiv.className = `message ${role}`;

    const contentDiv = document.createElement('div');
    contentDiv.className = 'message-content';

    // Converter quebras de linha para <br> se necessário, mas CSS white-space: pre-wrap já resolve
    contentDiv.textContent = text;

    messageDiv.appendChild(contentDiv);
    chatHistory.appendChild(messageDiv);

    // Scroll para o final
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

function showTyping(show) {
    typingIndicator.style.display = show ? 'flex' : 'none';
    if (show) {
        chatContainer.scrollTop = chatContainer.scrollHeight;
    }
}
