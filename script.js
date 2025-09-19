const chatWindow = document.getElementById('chat-window');
const textInput = document.getElementById('text-input');
const sendButton = document.getElementById('send-button');
const apiUrl = 'http://127.0.0.1:5000/analyze';

// --- Event Listeners ---
sendButton.addEventListener('click', handleUserMessage);
textInput.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
        event.preventDefault(); // Prevents adding a new line
        handleUserMessage();
    }
});

// --- Main Function to Handle User Input ---
async function handleUserMessage() {
    const messageText = textInput.value.trim();
    if (!messageText) return;

    // 1. Display user's message
    appendMessage('user', messageText);
    textInput.value = '';

    // 2. Disable input and show typing indicator
    toggleInput(false);
    const typingIndicatorId = showTypingIndicator();

    try {
        // 3. Send request to the backend
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({text: messageText}),
        });

        if (!response.ok) {
            throw new Error(`Server error: ${response.status}`);
        }
        const data = await response.json();

        // 4. Display bot's response
        const botResponse = `Bot: <span class="font-bold">${data.data}</span>`;
        appendMessage('bot', botResponse);

    } catch (error) {
        console.error('Error:', error);
        appendMessage('bot', 'Sorry, I couldn\'t get a response. Please check if the server is running.');
    } finally {
        // 5. Remove typing indicator and re-enable input
        document.getElementById(typingIndicatorId)?.remove();
        toggleInput(true);
    }
}

// --- UI Helper Functions ---

function appendMessage(sender, htmlContent) {
    const messageWrapper = document.createElement('div');
    messageWrapper.className = `flex ${sender === 'user' ? 'justify-end' : 'justify-start'}`;

    const messageBubble = document.createElement('div');
    const userClasses = 'bg-blue-600 text-white';
    const botClasses = 'bg-gray-200 dark:bg-gray-700 text-gray-900 dark:text-gray-200';
    messageBubble.className = `p-3 rounded-lg max-w-md text-sm ${sender === 'user' ? userClasses : botClasses}`;

    messageBubble.innerHTML = htmlContent;
    messageWrapper.appendChild(messageBubble);
    chatWindow.appendChild(messageWrapper);
    scrollToBottom();
}

function showTypingIndicator() {
    const uniqueId = `typing-${Date.now()}`;
    const indicatorHtml = `
        <div class="flex justify-start" id="${uniqueId}">
            <div class="bg-gray-200 dark:bg-gray-700 p-3 rounded-lg max-w-md">
                <div class="flex items-center space-x-1">
                    <span class="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.3s]"></span>
                    <span class="h-2 w-2 bg-gray-400 rounded-full animate-bounce [animation-delay:-0.15s]"></span>
                    <span class="h-2 w-2 bg-gray-400 rounded-full animate-bounce"></span>
                </div>
            </div>
        </div>
    `;
    chatWindow.insertAdjacentHTML('beforeend', indicatorHtml);
    scrollToBottom();
    return uniqueId; // Return the ID so we can remove it later
}

function toggleInput(enabled) {
    textInput.disabled = !enabled;
    sendButton.disabled = !enabled;
    if (enabled) {
        textInput.focus();
    }
}

function scrollToBottom() {
    chatWindow.scrollTop = chatWindow.scrollHeight;
}
