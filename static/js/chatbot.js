// Heathify Chatbot Widget
function toggleChatbot() {
    const panel = document.getElementById('chatbot-panel');
    if (!panel) return;
    panel.classList.toggle('hidden');
    if (!panel.classList.contains('hidden')) {
        document.getElementById('chatbot-input').focus();
    }
}

function sendChat() {
    const input = document.getElementById('chatbot-input');
    const message = input.value.trim();
    if (!message) return;

    // Display user message
    appendMessage(message, 'user');
    input.value = '';

    // Show typing indicator
    const typingEl = appendMessage('...', 'bot');
    typingEl.id = 'typing-indicator';
    typingEl.style.opacity = '0.6';
    typingEl.style.fontStyle = 'italic';

    // Call backend
    fetch('/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ message: message })
    })
        .then(r => r.json())
        .then(data => {
            // Remove typing indicator
            const ti = document.getElementById('typing-indicator');
            if (ti) ti.remove();
            appendMessage(data.reply, 'bot');

            // Update points badge if awarded
            if (data.points_awarded) {
                updatePointsBadge(data.new_points);
                showPointsToast('+5 pts — Health Consultation 🌿');
            }
        })
        .catch(() => {
            const ti = document.getElementById('typing-indicator');
            if (ti) ti.textContent = "Oops! Something went wrong. Try again.";
        });
}

function appendMessage(text, type) {
    const container = document.getElementById('chat-messages');
    if (!container) return null;
    const el = document.createElement('div');
    el.className = `chat-msg ${type}`;
    el.innerHTML = text.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>');
    container.appendChild(el);
    container.scrollTop = container.scrollHeight;
    return el;
}

function updatePointsBadge(points) {
    const badges = document.querySelectorAll('.nav-points');
    badges.forEach(b => { b.textContent = `⭐ ${points} pts`; });
}

function showPointsToast(msg) {
    const existing = document.querySelector('.points-toast');
    if (existing) existing.remove();
    const toast = document.createElement('div');
    toast.className = 'points-toast';
    toast.innerHTML = `⭐ ${msg}`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 4500);
}

// Make showPointsToast globally accessible
window.showPointsToast = showPointsToast;
window.updatePointsBadge = updatePointsBadge;
