
const AI_API_URL = 'http://127.0.0.1:8000/api/chat/';
let isChatOpen = false;
let historyLoaded = false;
let currentPendingActionId = null; 
let lastUserMessage = ''; 

function toggleChat() {
    const panel = document.getElementById('ai-chat-panel');
    const btn = document.getElementById('ai-btn-icon');
    isChatOpen = !isChatOpen;
    panel.style.display = isChatOpen ? 'flex' : 'none';
    btn.textContent = isChatOpen ? '×' : '✨';
}

function appendUserBubble(text) {
    const container = document.getElementById('chat-messages');
    const wrapper = document.createElement('div');
    wrapper.className = 'user-msg';
    wrapper.innerHTML = `<div class="user-msg-bubble">${escapeHtml(text)}</div>`;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

function appendAIBubble(text) {
    const container = document.getElementById('chat-messages');
    const wrapper = document.createElement('div');
    wrapper.className = 'ai-msg';
    wrapper.innerHTML = `<div class="ai-msg-bubble">${renderMarkdown(text)}</div>`;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

function renderMarkdown(text) {
    if (!text) return '';
    let html = escapeHtml(text);
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    html = html.replace(/`([^`]+)`/g, '<code>$1</code>');
    html = html.replace(/^[\-\*]\s+(.+)$/gm, '<li>$1</li>');
    html = html.replace(/(<li>.*<\/li>)/gs, '<ul>$1</ul>');
    html = html.replace(/<\/ul>\s*<ul>/g, '');
    html = html.replace(/\n/g, '<br>');
    return html;
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function showTypingIndicator() {
    const container = document.getElementById('chat-messages');
    const typing = document.createElement('div');
    typing.className = 'ai-msg';
    typing.id = 'ai-typing-indicator';
    typing.innerHTML = `<div class="ai-typing"><span></span><span></span><span></span></div>`;
    container.appendChild(typing);
    container.scrollTop = container.scrollHeight;
    document.getElementById('ai-status').textContent = 'Thinking...';
}

function hideTypingIndicator() {
    const el = document.getElementById('ai-typing-indicator');
    if (el) el.remove();
    document.getElementById('ai-status').textContent = 'Online';
}


function appendConfirmation(data) {
    const container = document.getElementById('chat-messages');
    currentPendingActionId = data.pending_action_id; // Store UUID safely

    const wrapper = document.createElement('div');
    wrapper.className = 'ai-msg';
    wrapper.innerHTML = `
        <div class="ai-confirm-box" id="confirm-box-active">
            <div class="ai-confirm-title">⚠️ Approval Required</div>
            <div class="ai-confirm-msg">${escapeHtml(data.message)}</div>
            <div class="ai-confirm-actions">
                <button class="ai-btn-approve" onclick="approveAction()">✓ Approve</button>
                <button class="ai-btn-cancel" onclick="cancelAction()">✗ Cancel</button>
            </div>
        </div>`;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

function approveAction() {
    const box = document.getElementById('confirm-box-active');
    if (box) {
        box.querySelector('.ai-confirm-actions').innerHTML = '<span style="color:#1D9E75; font-weight:500; font-size:12px;">✓ Approved — executing...</span>';
        box.removeAttribute('id');
    }
    const actionId = currentPendingActionId;
    currentPendingActionId = null;
    
    // Send only the UUID back to the server
    sendChatMessage(null, actionId); 
}

function cancelAction() {
    const box = document.getElementById('confirm-box-active');
    if (box) {
        box.querySelector('.ai-confirm-actions').innerHTML = '<span style="color:#ef4444; font-size:12px;">✗ Cancelled by user</span>';
        box.removeAttribute('id');
    }
    currentPendingActionId = null;
    appendAIBubble("Action cancelled. Let me know if you need anything else.");
}

function appendError(message) {
    const container = document.getElementById('chat-messages');
    const wrapper = document.createElement('div');
    wrapper.className = 'ai-msg';
    wrapper.innerHTML = `
        <div class="ai-error-box">
            <div class="ai-error-text">⚠️ ${escapeHtml(message)}</div>
            <button class="ai-btn-retry" onclick="retryLastMessage()">↻ Retry</button>
        </div>`;
    container.appendChild(wrapper);
    container.scrollTop = container.scrollHeight;
}

function retryLastMessage() {
    if (lastUserMessage) {
        document.getElementById('chat-input').value = lastUserMessage;
        sendChatMessage();
    }
}

function sendChip(text) {
    document.getElementById('chat-input').value = text;
    const suggestions = document.getElementById('suggested-actions');
    if (suggestions) suggestions.style.display = 'none';
    sendChatMessage();
}


async function sendChatMessage(userMessageOverride = null, approvedPendingActionId = null) {
    const inputEl = document.getElementById('chat-input');
    const message = userMessageOverride || (inputEl ? inputEl.value.trim() : '');

    // Ignore empty clicks unless approving an action
    if (!approvedPendingActionId && !message) return;

    // Show user message bubble
    if (!approvedPendingActionId && message) {
        appendUserBubble(message);
        lastUserMessage = message;
        inputEl.value = '';

        const suggestions = document.getElementById('suggested-actions');
        if (suggestions) suggestions.style.display = 'none';
    }

    showTypingIndicator();
    document.getElementById('ai-send-btn').disabled = true;

    try {
        const payload = {};
        if (message && !approvedPendingActionId) payload.message = message;
        
        
        if (approvedPendingActionId) payload.pending_action_id = approvedPendingActionId;

        
        const token = localStorage.getItem('access_token') || '';
        
        const res = await fetch(AI_API_URL, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}` 
            },
            body: JSON.stringify(payload)
        });

        hideTypingIndicator();

        if (!res.ok) {
            const errData = await res.json().catch(() => ({}));
            throw new Error(errData.error || `Server error (${res.status})`);
        }

        const data = await res.json();

     
        if (data.error) {
            appendError(data.error);
            return;
        }

       
        if (data.requires_confirmation) {
            appendConfirmation(data);
            return;
        }

       
        if (data.response) {
            appendAIBubble(data.response);
        }

    } catch (err) {
        hideTypingIndicator();
        appendError(err.message || 'Network error. Please check your connection.');
    } finally {
        document.getElementById('ai-send-btn').disabled = false;
    }
}
