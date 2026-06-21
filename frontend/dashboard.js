const BASE_API_URL = 'http://127.0.0.1:8000/api';

const invoices = [
  {num:'INV-2026-041',client:'Mehta Textiles',  amount:45000,  issued:'May 15',due:'Jun 5', status:'pending'},
  {num:'INV-2026-040',client:'Sharma Builders', amount:120000, issued:'May 1', due:'May 28',status:'overdue'},
  {num:'INV-2026-039',client:'Patel Pharma',    amount:78500,  issued:'Apr 28',due:'May 20',status:'paid'},
  {num:'INV-2026-038',client:'Reddy Farms',     amount:15200,  issued:'May 20',due:'Jun 12',status:'draft'},
  {num:'INV-2026-037',client:'Joshi Exports',   amount:55000,  issued:'Apr 10',due:'May 10',status:'paid'},
  {num:'INV-2026-036',client:'Mehta Textiles',  amount:32000,  issued:'Mar 20',due:'Apr 20',status:'paid'},
  {num:'INV-2026-035',client:'Kapoor Retail',   amount:18500,  issued:'Mar 5', due:'Apr 5', status:'paid'},
  {num:'INV-2026-034',client:'Singh Logistics', amount:67000,  issued:'Feb 15',due:'Mar 15',status:'paid'},
];

const clients = [
  {name:'Mehta Textiles', initials:'MT',color:'#E6F1FB',tcolor:'#0C447C',city:'Ahmedabad',invoices:3,total:'₹1.22L',status:'active'},
  {name:'Sharma Builders',initials:'SB',color:'#FAEEDA',tcolor:'#633806',city:'Pune',      invoices:2,total:'₹1.55L',status:'active'},
  {name:'Patel Pharma',   initials:'PP',color:'#E1F5EE',tcolor:'#085041',city:'Mumbai',    invoices:4,total:'₹2.1L', status:'active'},
  {name:'Reddy Farms',    initials:'RF',color:'#EEEDFE',tcolor:'#3C3489',city:'Hyderabad', invoices:1,total:'₹15.2K',status:'active'},
  {name:'Joshi Exports',  initials:'JE',color:'#FCEBEB',tcolor:'#791F1F',city:'Surat',     invoices:2,total:'₹87K',  status:'active'},
  {name:'Kapoor Retail',  initials:'KR',color:'#EAF3DE',tcolor:'#27500A',city:'Delhi',     invoices:1,total:'₹18.5K',status:'inactive'},
];

const reportData = {
  may: {billed:'₹2.4L',collected:'₹1.8L',pending:'₹60K',overdue:'₹22K',taxable:'₹2.03L',gst:'₹36.5K',cgst:'₹18.2K',sgst:'₹18.2K'},
  apr: {billed:'₹1.9L',collected:'₹1.6L',pending:'₹30K',overdue:'₹0',  taxable:'₹1.61L',gst:'₹29K',  cgst:'₹14.5K',sgst:'₹14.5K'},
  q1:  {billed:'₹5.2L',collected:'₹4.4L',pending:'₹80K',overdue:'₹12K',taxable:'₹4.41L',gst:'₹79K',  cgst:'₹39.5K',sgst:'₹39.5K'},
  fy:  {billed:'₹18.6L',collected:'₹16.2L',pending:'₹2.4L',overdue:'₹45K',taxable:'₹15.76L',gst:'₹2.84L',cgst:'₹1.42L',sgst:'₹1.42L'},
};

const months  = ['Jan','Feb','Mar','Apr','May','Jun'];
const billed  = [160000,140000,180000,190000,240000,80000];
const collected=[140000,120000,170000,160000,180000,50000];

function makeChart(id) {
  const max = Math.max(...billed);
  return new Chart(document.getElementById(id), {
    type: 'bar',
    data: {
      labels: months,
      datasets: [
        { label:'Billed',    data:billed,    backgroundColor:'#9FE1CB', borderRadius:3, borderSkipped:false },
        { label:'Collected', data:collected, backgroundColor:'#1D9E75', borderRadius:3, borderSkipped:false },
      ]
    },
    options: {
      responsive:true, maintainAspectRatio:false,
      plugins:{ legend:{ display:false }, tooltip:{ callbacks:{ label: c => ` ${c.dataset.label}: ₹${(c.parsed.y/1000).toFixed(0)}K` } } },
      scales:{
        x:{ grid:{ display:false }, ticks:{ font:{ size:11 }, color:'#888' } },
        y:{ beginAtZero:true, grid:{ color:'rgba(0,0,0,.04)' },
            ticks:{ font:{ size:11 }, color:'#888', callback: v => '₹'+(v/1000)+'K' } }
      }
    }
  });
}

const bmap = { paid:'b-paid', pending:'b-pending', overdue:'b-overdue', draft:'b-draft' };
const blbl = { paid:'Paid', pending:'Pending', overdue:'Overdue', draft:'Draft' };

function renderInvoices(list) {
  document.getElementById('inv-tbody').innerHTML = list.map(inv => `
    <tr onclick="openInvoiceDetail('${inv.num}','${inv.client}','₹${inv.amount.toLocaleString('en-IN')}','${inv.status}','${inv.due}')">
      <td style="font-family:var(--mono);font-size:11px">${inv.num}</td>
      <td>${inv.client}</td>
      <td>₹${inv.amount.toLocaleString('en-IN')}</td>
      <td>${inv.issued}</td>
      <td>${inv.due}</td>
      <td><span class="badge ${bmap[inv.status]}">${blbl[inv.status]}</span></td>
      <td>
        <div style="display:flex;gap:4px">
          <button class="icon-btn" onclick="event.stopPropagation();toast('PDF downloaded')" title="Download"><i class="ti ti-download"></i></button>
          <button class="icon-btn" onclick="event.stopPropagation();toast('Reminder sent')" title="Remind"><i class="ti ti-bell"></i></button>
          <button class="icon-btn" onclick="event.stopPropagation();toast('Link copied')" title="Copy"><i class="ti ti-copy"></i></button>
        </div>
      </td>
    </tr>`).join('');
}

function filterInvoices() {
  const q = document.getElementById('inv-search').value.toLowerCase();
  const s = document.getElementById('inv-status').value;
  const sort = document.getElementById('inv-sort').value;
  let list = invoices.filter(i =>
    (!q || i.client.toLowerCase().includes(q) || i.num.includes(q)) &&
    (!s || i.status === s)
  );
  if (sort === 'amount-desc') list.sort((a,b) => b.amount - a.amount);
  else if (sort === 'amount-asc') list.sort((a,b) => a.amount - b.amount);
  renderInvoices(list);
}

function renderClients(list) {
  document.getElementById('client-grid').innerHTML = list.map(c => {
    const isInactive = c.status === 'inactive';
    
    const badgeClass = isInactive ? 'b-inactive' : 'b-active';
    const cardOpacity = isInactive ? 'opacity: 0.6;' : 'opacity: 1;';
    const toggleIcon = isInactive ? 'ti-rotate-clockwise' : 'ti-archive';
    const toggleTitle = isInactive ? 'Restore to Active' : 'Mark Inactive';

    return `
    <div class="client-card" style="${cardOpacity} transition: opacity 0.3s;" onclick="toast('Opening ${c.name} profile')">
      <div class="client-avatar" style="background:${c.color};color:${c.tcolor}">${c.initials}</div>
      <div class="client-name" style="${isInactive ? 'text-decoration: line-through; color: var(--gray-5);' : ''}">${c.name}</div>
      <div class="client-meta">
        <i class="ti ti-map-pin" style="font-size:11px"></i> ${c.city}
        &nbsp;·&nbsp;
        <span class="badge ${badgeClass}">${c.status.charAt(0).toUpperCase() + c.status.slice(1)}</span>
      </div>
      
      <div class="stat-row-card">
        <div class="stat-item">
          <div class="stat-val">${c.invoices}</div>
          <div class="stat-lbl">Invoices</div>
        </div>
        <div class="stat-item">
          <div class="stat-val">${c.total}</div>
          <div class="stat-lbl">Billed</div>
        </div>
        <button class="icon-btn" style="width:28px;height:28px" onclick="event.stopPropagation(); openClientEdit(${c.id})" title="Edit client">
            <i class="ti ti-pencil" style="font-size:14px"></i>
        </button>
        <div class="stat-item" style="display:flex; align-items:center; justify-content:center;">
          <button class="icon-btn" style="width:26px;height:26px" onclick="event.stopPropagation(); toggleDummyClientStatus('${c.name}')" title="${toggleTitle}">
            <i class="ti ${toggleIcon}" style="font-size:13px"></i>
          </button>
        </div>
      </div>
    </div>`;
  }).join('');
}

function filterClients() {
  const q = document.getElementById('client-search').value.toLowerCase();
  const f = document.getElementById('client-filter').value;
  renderClients(clients.filter(c =>
    (!q || c.name.toLowerCase().includes(q)) &&
    (!f || c.status === f)
  ));
}

function renderReportClients() {
  const rows = [
    ['Patel Pharma',    '4','₹2.1L', '₹2.1L','100%'],
    ['Sharma Builders', '2','₹1.55L','₹35K', '22%'],
    ['Mehta Textiles',  '3','₹1.22L','₹97K', '79%'],
    ['Joshi Exports',   '2','₹87K',  '₹87K', '100%'],
    ['Kapoor Retail',   '1','₹18.5K','₹18.5K','100%'],
  ];
  document.getElementById('report-clients').innerHTML = rows.map(r =>
    `<tr><td>${r[0]}</td><td>${r[1]}</td><td>${r[2]}</td><td>${r[3]}</td><td class="up">${r[4]}</td></tr>`
  ).join('');
}

function updateReports() {
  const p = reportData[document.getElementById('report-period').value];
  document.getElementById('r-billed').textContent   = p.billed;
  document.getElementById('r-collected').textContent = p.collected;
  document.getElementById('r-pending').textContent  = p.pending;
  document.getElementById('r-overdue').textContent  = p.overdue;
  document.getElementById('r-taxable').textContent  = p.taxable;
  document.getElementById('r-gst').textContent      = p.gst;
  document.getElementById('r-cgst').textContent     = p.cgst;
  document.getElementById('r-sgst').textContent     = p.sgst;
}

function showPage(name, btn) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  if (btn) btn.classList.add('active');
  closeAllModals();
}

function openModal(type) { closeAllModals(); document.getElementById('modal-' + type).classList.add('open'); }

function closeModal(type) {
    document.getElementById('modal-' + type).classList.remove('open');
    if (type === 'client') {
        const iframe = document.querySelector('#modal-client iframe');
        if (iframe) iframe.src = 'createclient.html';
    }
}

function closeAllModals() { document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.remove('open')); }

document.querySelectorAll('.modal-backdrop').forEach(m => {
  m.addEventListener('click', e => { if (e.target === m) closeAllModals(); });
});

function openInvoiceDetail(num, client, amount, status, due) {
  document.getElementById('detail-num').textContent    = num;
  document.getElementById('detail-client').textContent = client;
  document.getElementById('detail-amount').textContent = amount;
  document.getElementById('detail-due').textContent    = due;
  const badge = document.getElementById('detail-badge');
  badge.className = 'badge ' + bmap[status];
  badge.textContent = blbl[status];
  openModal('detail');
}

function doAction(type) {
  const msgs = { reminder:'Reminder sent via WhatsApp & email', download:'Invoice PDF downloaded', paid:'Invoice marked as paid' };
  toast(msgs[type]);
  if (type === 'paid') closeModal('detail');
}

function toast(msg) {
  const n = document.getElementById('notify');
  n.textContent = msg;
  n.classList.add('show');
  clearTimeout(n._t);
  n._t = setTimeout(() => n.classList.remove('show'), 2500);
}

// --- SMART PINCODE ENGINE ---
async function fetchPincodeData(pincode) {
    // Only search when the user types exactly 6 digits
    if (pincode.length === 6) {
        document.getElementById('c-city').value = "Loading...";
        document.getElementById('c-state').value = "Loading...";

        try {
            const response = await fetch(`https://api.postalpincode.in/pincode/${pincode}`);
            const data = await response.json();

            if (data[0].Status === "Success") {
                // Grab the exact District and State from the Post Office database
                const location = data[0].PostOffice[0];
                document.getElementById('c-city').value = location.District;
                document.getElementById('c-state').value = location.State;
            } else {
                toast("Invalid Pincode");
                document.getElementById('c-city').value = "";
                document.getElementById('c-state').value = "";
            }
        } catch (error) {
            toast("Network error. Please type manually.");
            document.getElementById('c-city').removeAttribute('readonly');
            document.getElementById('c-state').removeAttribute('readonly');
        }
    }
}



// Toggle the dropdown
function toggleProfileMenu() {
  document.getElementById('profile-dropdown').classList.toggle('show');
}

// Close the menu if user clicks outside
window.onclick = function(event) {
  if (!event.target.matches('.avatar')) {
    var dropdowns = document.getElementsByClassName("profile-dropdown");
    for (var i = 0; i < dropdowns.length; i++) {
      dropdowns[i].classList.remove('show');
    }
  }
}

// Placeholder logout function
function logout() {
  localStorage.removeItem('access_token');
  window.location.href = 'landingpage.html'; // Redirect to login
}

function toggleProfileMenu() {
    const dropdown = document.getElementById('profile-dropdown');
    // Toggle between none and block
    dropdown.style.display = (dropdown.style.display === 'block') ? 'none' : 'block';
}

function openClientEdit(clientId) {
    closeAllModals();
    document.getElementById('modal-client').classList.add('open');
    const iframe = document.querySelector('#modal-client iframe');
    iframe.src = `createclient.html?id=${clientId}`;
}

function toggleDummyClientStatus(clientName) {
    const client = clients.find(c => c.name === clientName);
    
    if (client) {
        client.status = client.status === 'active' ? 'inactive' : 'active';
        toast(`Client marked as ${client.status}`);
        filterClients();
    }
}

// Optional: Close the menu when clicking outside
window.addEventListener('click', function(e) {
    const dropdown = document.getElementById('profile-dropdown');
    const avatar = document.querySelector('.avatar');
    if (!avatar.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.style.display = 'none';
    }
});

// async function checkProfileCompletion() {
//     try {
//         const response = await fetch(`${BASE_API_URL}/profile/`, {
//             method: 'GET', 
//             headers: { 
//                 'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
//                 'Content-Type': 'application/json'
//             }
//         });

//         if (response.ok) {
//             const profile = await response.json();
            
//             const isMissingData = !profile.account_number || !profile.ifsc_code;
            
//             if (isMissingData) {
//                 console.warn("Profile incomplete. Redirecting...");
//                 toast("Please complete your profile to access all features.");
//                 return false;
//             }
//             return true;
//         }
//     } catch (error) {
//         console.error("Gatekeeper error:", error);
//     }
// }

async function checkProfileCompletion() {
    try {
        const response = await fetch(`${BASE_API_URL}/profile/`, {
            method: 'GET', 
            headers: { 
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`,
                'Content-Type': 'application/json'
            }
        });

        if (response.ok) {
            const profile = await response.json();
            
            // --- 1. INSTANT UI HYDRATION (Directly from Django) ---
            const name = profile.display_name || (profile.email ? profile.email.split('@')[0] : 'User');
            const email = profile.email || '';
            const initials = name.substring(0, 2).toUpperCase();

            const navAvatar = document.getElementById('nav-avatar');
            const navName = document.getElementById('nav-name');
            const navEmail = document.getElementById('nav-email');

            if (navAvatar) navAvatar.textContent = initials;
            if (navName) navName.textContent = name;
            if (navEmail) navEmail.textContent = email;
            // ------------------------------------------------------

            // 2. Check if they need to finish onboarding
            const isMissingData = !profile.account_number || !profile.ifsc_code;
            if (isMissingData) {
                console.warn("Profile incomplete. User is in Demo Mode.");
                return false;
            }
            return true;
        }
    } catch (error) {
        console.error("Gatekeeper error:", error);
    }
}


async function protectedOpenModal(type) {
    const isComplete = await checkProfileCompletion();
    
    if (!isComplete) {
        toast("Please complete your profile to add your own data!");
        
        setTimeout(() => { 
            window.location.href = 'profile.html'; 
        }, 2500);
        
        return;
    }
    
    openModal(type);
}

async function initializeDashboard() {
    const isPersonalizedMode = await checkProfileCompletion();

    if (isPersonalizedMode) {
        console.log("Profile complete: Loading Personalized Dashboard");
        
        // 1. Wipe the hardcoded demo data clean
        document.getElementById('service-tbody').innerHTML = '';
        document.getElementById('inv-tbody').innerHTML = '';
        // document.getElementById('client-grid').innerHTML = '';
        
        // 2. Fetch the user's real data from the API
        // loadRealServices();
        // loadRealInvoices();
        
    } else {
        console.log("Profile incomplete: Running in Demo Mode");
       
    }
}

document.addEventListener("DOMContentLoaded", initializeDashboard);


// Initialization
checkProfileCompletion();

renderInvoices(invoices);
renderClients(clients);
renderReportClients();
setTimeout(() => { makeChart('dash-chart'); makeChart('report-chart'); }, 100);