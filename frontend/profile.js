const token = localStorage.getItem('access_token');
if (!token) {
    window.location.href = 'index.html';
}



window.toast = function(msg) {
    const el = document.getElementById('toast-el');
    el.textContent = msg; el.classList.add('show');
    clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove('show'), 3000);
};


const pincodeInput = document.getElementById('pincode');
if (pincodeInput) {
    pincodeInput.addEventListener('input', async () => {
        const val = pincodeInput.value.trim();
        if (val.length === 6 && /^\d{6}$/.test(val)) {
            try {
                const res = await fetch(`https://api.postalpincode.in/pincode/${val}`);
                const data = await res.json();
                if (data && data[0] && data[0].Status === 'Success' && data[0].PostOffice && data[0].PostOffice.length) {
                    const po = data[0].PostOffice[0];
                    document.getElementById('city').value = po.District || '';
                    document.getElementById('state').value = po.State || '';
                }
            } catch (error) {
                console.error('Pincode lookup failed:', error);
            }
        }
    });
}

document.addEventListener('DOMContentLoaded', async () => {
    try {
        const response = await fetch(`${BASE_API_URL}/profile/`, {
            method: 'GET',
            headers: { 'Authorization': `Bearer ${token}` }
        });

        if (response.ok) {
            const data = await response.json();

            const emailInput = document.getElementById('email');
            const nameInput = document.getElementById('display_name');

            if (emailInput) emailInput.value = data.email || localStorage.getItem('user_email') || 'Loading...';
            if (nameInput && data.display_name) nameInput.value = data.display_name;

            if (data.phone_number) document.getElementById('phone_number').value = data.phone_number;
            if (data.upi_id) document.getElementById('upi_id').value = data.upi_id;
            if (data.account_number) document.getElementById('account_number').value = data.account_number;
            if (data.ifsc_code) document.getElementById('ifsc_code').value = data.ifsc_code;
            if (data.gstin) document.getElementById('gstin').value = data.gstin;

            if (data.pincode) document.getElementById('pincode').value = data.pincode;
            if (data.street_address) document.getElementById('street_address').value = data.street_address;
            if (data.city) document.getElementById('city').value = data.city;
            if (data.state) document.getElementById('state').value = data.state;

            if (data.razorpay_key_id) document.getElementById('razorpay_key_id').value = data.razorpay_key_id;
            if (data.has_razorpay_secret) {
                const secretInput = document.getElementById('razorpay_key_secret');
                if (secretInput) {
                    secretInput.value = "••••••••••";
                }
            }


            const isComplete = data.account_number && data.ifsc_code;

            const titleEl = document.querySelector('.title');
            const subtitleEl = document.querySelector('.subtitle');
            const saveBtn = document.getElementById('save-profile-btn');
            const skipBtn = document.getElementById('skip-profile-btn');

            if (isComplete) {
                
                if (titleEl) titleEl.textContent = "Manage Business Profile";
                if (subtitleEl) subtitleEl.textContent = "Update your billing and bank details below.";

                if (saveBtn) saveBtn.textContent = "Update Profile";

                if (skipBtn) {
                    skipBtn.textContent = "Cancel / Back";
                    skipBtn.onclick = (e) => {
                        e.preventDefault();
                        window.location.replace('dynamicdashboard.html'); 
                    };
                }
            } else {
            
                if (titleEl) titleEl.textContent = "Business Details";
                if (subtitleEl) subtitleEl.textContent = "We need this to generate valid GST invoices.";

                if (saveBtn) saveBtn.textContent = "Save Profile";

                if (skipBtn) {
                    skipBtn.textContent = "Skip for now";
                    skipBtn.onclick = (e) => {
                        e.preventDefault();
                        window.location.replace('dynamicdashboard.html');
                    };
                }
            }
        }
    } catch (error) {
        console.error("Error fetching profile on load:", error);
    }
});

document.getElementById('profile-form').addEventListener('submit', async (e) => {
    e.preventDefault();

    document.querySelectorAll('.is-invalid').forEach(el => el.classList.remove('is-invalid'));
    document.querySelectorAll('.error-msg').forEach(el => el.classList.remove('visible'));

    const payload = {
        display_name: document.getElementById('display_name').value,
        phone_number: document.getElementById('phone_number').value,
        upi_id: document.getElementById('upi_id').value,
        account_number: document.getElementById('account_number').value,
        ifsc_code: document.getElementById('ifsc_code').value,
        gstin: document.getElementById('gstin').value || null,
        pincode: document.getElementById('pincode').value || null,
        street_address: document.getElementById('street_address').value || null,
        city: document.getElementById('city').value || null,
        state: document.getElementById('state').value || null,
        razorpay_key_id: document.getElementById('razorpay_key_id') ? document.getElementById('razorpay_key_id').value : null
    };

    const secretInput = document.getElementById('razorpay_key_secret');
    if (secretInput) {
        const val = secretInput.value.trim();
        if (val !== '' && val !== '••••••••••') {
            payload.razorpay_key_secret = val;
        }
    }

    const submitBtn = document.querySelector('.submit-btn');
    submitBtn.textContent = 'Saving...';

    try {
        const response = await fetch(`${BASE_API_URL}/profile/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify(payload)
        });

        const data = await response.json();

        if (response.ok) {
            toast("Profile saved securely!");
            setTimeout(() => {
                window.location.href = 'dynamicdashboard.html';
            }, 1000);
        } else {
            toast("Please fix the errors in the form.");
            submitBtn.textContent = 'Save & Go to Dashboard';

            for (const [field, messages] of Object.entries(data)) {
                const inputEl = document.getElementById(field);
                const errorEl = document.getElementById(`err-${field}`);

                if (inputEl && errorEl) {
                    inputEl.classList.add('is-invalid');
                    errorEl.textContent = messages[0];
                    errorEl.classList.add('visible');
                }
            }
        }
    } catch (error) {
        console.error("Profile Error:", error);
        toast("Cannot connect to server.");
        submitBtn.textContent = 'Save & Go to Dashboard';
    }
});

async function deleteAccount() {
    const confirmDelete = confirm("WARNING: This will permanently delete your account, clients, services, and all invoices. This action cannot be undone.\n\nAre you absolutely sure you want to proceed?");
    if (!confirmDelete) return;

    const password = prompt("Please enter your password to confirm deletion:");
    if (!password) {
        toast("Password is required to delete your account.");
        return;
    }

    try {
        const response = await fetch(`${BASE_API_URL}/delete-account/`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${token}`
            },
            body: JSON.stringify({ password })
        });

        const data = await response.json();

        if (response.ok) {
            alert("Your account and all associated data have been deleted.");
            localStorage.removeItem('access_token');
            localStorage.removeItem('refresh_token');
            window.location.replace('index.html');
        } else {
            toast(data.error || "Failed to delete account.");
        }
    } catch (error) {
        console.error("Delete Account Error:", error);
        toast("Network error. Could not connect to server.");
    }
}