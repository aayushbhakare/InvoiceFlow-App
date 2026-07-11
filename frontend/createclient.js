
const urlParams  = new URLSearchParams(window.location.search);
const editId     = urlParams.get('id');
const isEditMode = !!editId;

window.addEventListener('DOMContentLoaded', async () => {
    if (!isEditMode) return;
    document.querySelector('.card-title').textContent = 'Edit client';
    document.querySelector('.card-sub').textContent   = 'Update client details below';
    document.querySelector('.btn-save').innerHTML     = '<i class="ti ti-device-floppy"></i> Save changes';

    const token = localStorage.getItem('access_token');
    try {
        const res = await fetch(`${BASE_API_URL}/clients/${editId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        const c = await res.json();
        document.getElementById('biz-name').value  = c.name           || '';
        document.getElementById('contact').value   = c.contact_person || '';
        document.getElementById('mobile').value    = c.phone          || '';
        document.getElementById('email').value     = c.email          || '';
        document.getElementById('c-address').value = c.address        || '';
        document.getElementById('c-pincode').value = c.pincode        || '';
        document.getElementById('c-city').value    = c.city           || '';
        document.getElementById('c-state').value   = c.state          || '';
    } catch { showToast('Network error loading client'); }
});

function chk(id, val) {
  const f = document.getElementById(id);
  f.classList.toggle('invalid', val.trim().length === 0);
}

function chkEmail(val) {
  const f = document.getElementById('f-email');
  const ok = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(val);
  if (val.length === 0) { f.classList.remove('invalid'); return; }
  f.classList.toggle('invalid', !ok);
}

function chkMobile(val) {
  const digits = val.replace(/\D/g, '');
  const f = document.getElementById('f-mobile');
  if (val.length === 0) { f.classList.remove('invalid'); return; }
  f.classList.toggle('invalid', digits.length !== 10);
}

function chkGstin(val) {
  const f = document.getElementById('f-gstin');
  if (val.length === 0) { f.classList.remove('invalid'); return; }
  const ok = /^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(val.toUpperCase());
  f.classList.toggle('invalid', !ok);
}

async function fetchPincodeData(pincode) {
  const digits = pincode.replace(/\D/g, '');
  
  if (digits.length === 6) {
      document.getElementById('c-city').value = "Loading...";
      document.getElementById('c-state').value = "Loading...";

      try {
          const response = await fetch(`https://api.postalpincode.in/pincode/${digits}`);
          const data = await response.json();

          if (data[0].Status === "Success") {
              const location = data[0].PostOffice[0];
              document.getElementById('c-city').value = location.District;
              document.getElementById('c-state').value = location.State;
              showToast('City & state filled automatically');
          } else {
              showToast("Invalid Pincode");
              document.getElementById('c-city').value = "";
              document.getElementById('c-state').value = "";
          }
      } catch (error) {
          showToast("Network error");
          document.getElementById('c-city').value = "";
          document.getElementById('c-state').value = "";
      }
  } else {
      document.getElementById('c-city').value = "";
      document.getElementById('c-state').value = "";
  }
}

async function submitForm() {
  
  if (window.parent && window.parent.checkProfileCompletion) {
    const isComplete = await window.parent.checkProfileCompletion();
    
    if (!isComplete) {
      window.parent.toast("Please complete your profile to save data!");
      return; 
    }
  }

  let missing = false;
  const required = {
    'f-biz':     document.getElementById('biz-name'),
    'f-contact': document.getElementById('contact'),
    'f-mobile':  document.getElementById('mobile'),
    'f-email':   document.getElementById('email'),
  };
  
  Object.entries(required).forEach(([fid, inp]) => {
    if (!inp.value.trim()) {
      document.getElementById(fid).classList.add('invalid');
      missing = true;
    }
  });
  
  if (missing) {
    showToast('Please fill in all required fields');
    return;
  }

  
  const gstinVal = (document.getElementById('c-gstin') ? document.getElementById('c-gstin').value.trim() : '').toUpperCase();
  if (gstinVal && !/^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$/.test(gstinVal)) {
    document.getElementById('f-gstin').classList.add('invalid');
    showToast('Please enter a valid GSTIN');
    return;
  }

  const city    = document.getElementById('c-city').value.trim();
  const state   = document.getElementById('c-state').value.trim();
  const street  = document.getElementById('c-address').value.trim();
  const pincode = document.getElementById('c-pincode') ? document.getElementById('c-pincode').value.trim() : '';

  const payload = {
    name:            document.getElementById('biz-name').value.trim(),
    contact_person:  document.getElementById('contact').value.trim(),
    email:           document.getElementById('email').value.trim(),
    phone:           document.getElementById('mobile').value.trim(),
    address:         street,
    city:            city,
    state:           state,
    pincode:         pincode,
    gstin:           gstinVal || null,
};

  try {
    const token = localStorage.getItem('access_token');
    const url    = isEditMode ? `${BASE_API_URL}/clients/${editId}/` : `${BASE_API_URL}/clients/`;
    const method = isEditMode ? 'PATCH' : 'POST';
    const response = await fetch(url, {
        method,
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(payload)
    }); 
    

    if (response.ok) {
      const name = document.getElementById('biz-name').value.trim();
      showToast(isEditMode ? 'Client updated successfully!' : name + ' added successfully!');
      
      setTimeout(() => {
        if (window.parent && window.parent.closeModal) {
          window.parent.closeModal('client'); 
          
          if (window.parent.fetchClients) {
            window.parent.fetchClients(); 
          }
        }
      }, 1500);

    } else {
      const errorData = await response.json();
      console.error(errorData);
      showToast('Failed to save client');
    }
  } catch (error) {
    console.error("Error saving client:", error);
    showToast('Network error');
  }
}

function resetForm() {
  if (window.parent && window.parent.closeModal) {
    window.parent.closeModal('client');
  }
}

function showToast(msg) {
  const t = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2600);
}

