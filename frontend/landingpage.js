const BASE_API_URL = 'http://127.0.0.1:8000/api';

window.toast = function(msg, isError = false) {
    const el = document.getElementById('toast-el');
    if (!el) return;
    
    el.textContent = msg;
    el.style.background = isError ? '#D32F2F' : '#0D0D0B';
    el.classList.add('show');
    
    clearTimeout(el._t);
    el._t = setTimeout(() => el.classList.remove('show'), 3000);
};

document.addEventListener('DOMContentLoaded', () => {
    
    const loginForm = document.getElementById('login-form');
    if (loginForm) {
        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = loginForm.querySelector('input[type="email"]').value;
            const password = loginForm.querySelector('input[type="password"]').value;
            const submitBtn = loginForm.querySelector('.submit-btn');

            submitBtn.textContent = 'Authenticating...';
            submitBtn.disabled = true;

            try {
                // 1. Authenticate the User
                const response = await fetch(`${BASE_API_URL}/token/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username: email, password: password })
                });

                const data = await response.json();

                if (response.ok) {
                    // 2. Save Tokens
                    localStorage.setItem('access_token', data.access);
                    localStorage.setItem('refresh_token', data.refresh);
                    
                    toast("Login successful! Checking profile status...");
                    
                    // 3. Fetch Profile Status before routing
                    try {
                        const profileResponse = await fetch(`${BASE_API_URL}/profile/`, {
                            method: 'GET',
                            headers: {
                                'Authorization': 'Bearer ' + data.access
                            }
                        });

                        const profileData = await profileResponse.json();

                        // 4. The Routing Fork
                        setTimeout(() => {
                            if (profileData.is_complete === true) {
                                // Profile is done -> Go straight to the app
                                window.location.replace('dynamicdashboard.html');
                            } else {
                                // Profile is incomplete -> Force onboarding
                                window.location.replace('profile.html');
                            }
                        }, 1000);

                    } catch (profileError) {
                        console.error("Error checking profile:", profileError);
                        // Safe fallback: if the check fails, send them to setup
                        window.location.replace('profile.html'); 
                    }

                } else {
                    toast(data.detail || "Invalid email or password.", true);
                    submitBtn.textContent = 'Sign in to Dashboard';
                    submitBtn.disabled = false;
                }
            } catch (error) {
                console.error("Login Error:", error);
                toast("Server error. Is Django running?", true);
                submitBtn.textContent = 'Sign in to Dashboard';
                submitBtn.disabled = false;
            }
        });
    }

    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const email = registerForm.querySelector('input[type="email"]').value;
            const password = registerForm.querySelector('input[type="password"]').value;
            const submitBtn = registerForm.querySelector('.submit-btn');

            submitBtn.textContent = 'Creating Account...';
            submitBtn.disabled = true;

            try {
                const response = await fetch(`${BASE_API_URL}/register/`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ email, password })
                });

                const data = await response.json();

                if (response.ok) {
                    toast("Account created! Please sign in.");
                    registerForm.reset();
                    
                    setTimeout(() => {
                        document.getElementById('tab-login').click();
                        submitBtn.textContent = 'Create Free Account';
                        submitBtn.disabled = false;
                    }, 1500);
                } else {
                    const errorMsg = data.detail || Object.values(data)[0][0] || "Registration failed.";
                    toast(errorMsg, true);
                    submitBtn.textContent = 'Create Free Account';
                    submitBtn.disabled = false;
                }
            } catch (error) {
                console.error("Registration Error:", error);
                toast("Server error. Is Django running?", true);
                submitBtn.textContent = 'Create Free Account';
                submitBtn.disabled = false;
            }
        });
    }
});