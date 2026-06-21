const BASE_API_URL = 'http://127.0.0.1:8000/api';
const token = localStorage.getItem('access_token');

const params = new URLSearchParams(window.location.search);
const serviceId = params.get('id');
let isEditMode = false;

// Reusing your validation logic from createclient.js
function chk(id, val) {
  const f = document.getElementById(id);
  f.classList.toggle('invalid', val.trim().length === 0);
}

function showToast(msg, isError = false) {
  const t = document.getElementById('toast');
  const icon = t.querySelector('i');
  
  icon.className = isError ? 'ti ti-alert-circle' : 'ti ti-circle-check';
  t.style.background = isError ? '#D32F2F' : '#0D0D0B';
  
  document.getElementById('toast-msg').textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2600);
}

function closeIframe() {
    
    if (window.parent && window.parent.closeModal) {
        window.parent.closeModal('service');
    }
}

async function loadServiceForEdit() {
  if (!serviceId) return;
  isEditMode = true;

  document.querySelector('.card-title').textContent = 'Edit service';
  document.querySelector('.card-sub').textContent = 'Update this catalog item';
  document.querySelector('.btn-save').innerHTML = '<i class="ti ti-device-floppy"></i> Update service';

  try {
    const response = await fetch(`${BASE_API_URL}/services/${serviceId}/`, {
      headers: { 'Authorization': `Bearer ${token}` }
    });
    if (response.ok) {
      const svc = await response.json();
      document.getElementById('service-name').value = svc.name || '';
      document.getElementById('service-desc').value = svc.description || '';
      document.getElementById('service-rate').value = svc.rate ?? '';
    } else {
      showToast('Could not load this service.', true);
    }
  } catch (error) {
    showToast('Network error loading service.', true);
  }
}

async function submitService() {

  if (window.parent && window.parent.checkProfileCompletion) {
    const isComplete = await window.parent.checkProfileCompletion();
    
    if (!isComplete) {
      window.parent.toast("Please complete your profile to save data!");
      
      return; 
    }
  }

  const nameInput = document.getElementById('service-name');
  const descInput = document.getElementById('service-desc');
  const rateInput = document.getElementById('service-rate');
  
  let missing = false;
  if (!nameInput.value.trim()) { chk('f-name', ''); missing = true; }
  if (!rateInput.value.trim()) { chk('f-rate', ''); missing = true; }

  if (missing) {
    showToast('Please fill in required fields', true);
    return;
  }

  // Matches your Django ServicesSerializer exactly
  const payload = {
    name: nameInput.value.trim(),
    description: descInput.value.trim(),
    rate: parseFloat(rateInput.value)
  };

  const btn = document.querySelector('.btn-save');
  const originalBtnHTML = btn.innerHTML;
  btn.innerHTML = 'Saving...';
  btn.disabled = true;

  const url = isEditMode ? `${BASE_API_URL}/services/${serviceId}/` : `${BASE_API_URL}/services/`;
  const method = isEditMode ? 'PATCH' : 'POST';

  try {
    const response = await fetch(url, {
        method,
        headers: { 
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}` 
        },
        body: JSON.stringify(payload)
    });

    if (response.ok) {
        showToast(isEditMode ? 'Service updated successfully!' : 'Service added successfully!');
        
        setTimeout(() => {
            // Trigger the dashboard to fetch the new list of services
            if (window.parent && window.parent.fetchServices) {
                window.parent.fetchServices();
            }
            closeIframe();
        }, 1200);
    } else {
        const data = await response.json();
        showToast(data.detail || 'Failed to save service.', true);
        btn.innerHTML = originalBtnHTML;
        btn.disabled = false;
    }
  } catch (error) {
    showToast('Network error.', true);
    btn.innerHTML = originalBtnHTML;
    btn.disabled = false;
  }
}
loadServiceForEdit();