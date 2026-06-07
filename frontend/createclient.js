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

function submitForm() {
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
  const name = document.getElementById('biz-name').value.trim();
  showToast(name + ' added successfully');
  
  setTimeout(() => {
    window.location.href = 'dashboard.html';
  }, 1800);
}

function resetForm() {
  window.location.href = 'dashboard.html';
}

function showToast(msg) {
  const t = document.getElementById('toast');
  document.getElementById('toast-msg').textContent = msg;
  t.classList.add('show');
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.remove('show'), 2600);
}