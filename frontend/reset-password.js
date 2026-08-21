document.addEventListener('DOMContentLoaded', () => {
    // Extract token from URL
    const urlParams = new URLSearchParams(window.location.search);
    const token = urlParams.get('token');

    if (!token) {
        toast("Invalid or missing reset token. Please request a new link.", true);
        document.getElementById('submit-btn').disabled = true;
        return;
    }

    const resetForm = document.getElementById('reset-password-form');
    
    resetForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const newPassword = document.getElementById('new-password').value;
        const confirmPassword = document.getElementById('confirm-password').value;
        const submitBtn = document.getElementById('submit-btn');

        // Check if passwords match (Client-side validation)
        if (newPassword !== confirmPassword) {
            toast("Passwords do not match!", true);
            return;
        }

        if (newPassword.length < 8) {
            toast("Password must be at least 8 characters.", true);
            return;
        }

        submitBtn.textContent = 'Resetting Password...';
        submitBtn.disabled = true;

        try {
            const response = await fetch(`${BASE_API_URL}/reset-password/`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    token: token,
                    password: newPassword 
                })
            });

            const data = await response.json();

            if (response.ok) {
                toast("Password reset successfully! Redirecting to login...");
                
                setTimeout(() => {
                    window.location.replace('index.html');
                }, 2000);
            } else {
                toast(data.error || "Failed to reset password.", true);
                submitBtn.textContent = 'Reset Password';
                submitBtn.disabled = false;
            }
        } catch (error) {
            console.error("Reset Password Error:", error);
            toast("Server error. Please try again.", true);
            submitBtn.textContent = 'Reset Password';
            submitBtn.disabled = false;
        }
    });
});
