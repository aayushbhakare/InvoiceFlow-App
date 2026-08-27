// Set to your EC2 public IP/domain in production, or /api if backend and frontend are hosted together
var BASE_API_URL = window.BASE_API_URL || '/api';


function getToken() {
    return localStorage.getItem('access_token') || '';
}

function authHeaders() {
    return { 'Authorization': `Bearer ${getToken()}` };
}

function authJsonHeaders() {
    return {
        'Authorization': `Bearer ${getToken()}`,
        'Content-Type': 'application/json'
    };
}


function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}


function toast(msg, duration = 3000) {
    
    const el = document.querySelector('.notify, #notify');
    if (!el) return;
    el.textContent = msg;
    el.classList.add('show');
    clearTimeout(el._toastTimer);
    el._toastTimer = setTimeout(() => el.classList.remove('show'), duration);
}


function formatINR(n) {
    return `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}
