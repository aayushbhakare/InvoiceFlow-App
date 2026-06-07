const token = localStorage.getItem('access_token');
const BASE_API_URL = 'http://127.0.0.1:8000/api';

let globalClients = [];
let globalServices = [];
let rows = [];
let rowId = 0;
let selectedClient = null;

const myState = "Maharashtra"; // Your local business state for tax calculations

const fmt = n => "₹" + Math.round(n).toLocaleString("en-IN");
const showToast = msg => { const t = document.getElementById("toast"); t.textContent = msg; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 3000); }

async function init() {
  document.getElementById("issue-date").value = new Date().toISOString().split("T")[0];
  
  // Fetch Real Data from Django
  try {
    const [clientsRes, servicesRes] = await Promise.all([
      fetch(`${BASE_API_URL}/clients/`, { headers: {'Authorization': `Bearer ${token}`} }),
      fetch(`${BASE_API_URL}/services/`, { headers: {'Authorization': `Bearer ${token}`} })
    ]);

    globalClients = await clientsRes.json();
    globalServices = await servicesRes.json();

    // Populate Client Dropdown
    const select = document.getElementById('client-select');
    select.innerHTML = '<option value="">— Choose a client —</option>' + 
      globalClients.map(c => `<option value="${c.id}">${c.name}</option>`).join('');

  } catch(e) {
    showToast("Failed to connect to database");
  }
  
  addRow(); // Add first blank row
}

function loadClient() {
  const clientId = document.getElementById("client-select").value;
  selectedClient = globalClients.find(c => c.id == clientId);
  
  if (selectedClient) {
    document.getElementById("cp-name").textContent = selectedClient.name;
    document.getElementById("cp-detail").textContent = `${selectedClient.address || ''}, ${selectedClient.state || ''}`;
    document.getElementById("client-preview").classList.add("show");
  } else {
    document.getElementById("client-preview").classList.remove("show");
  }
  recalc(); // Recalculate taxes based on the new client's state!
}

// Service Row Logic
function addRow() {
  const id = ++rowId;
  rows.push({ id, name: "", qty: 1, price: 0 });
  renderRows();
}

function deleteRow(id) { rows = rows.filter(r => r.id !== id); renderRows(); recalc(); }

function renderRows() {
  const container = document.getElementById("service-rows");
  container.innerHTML = "";
  
  rows.forEach(r => {
    const div = document.createElement("div");
    div.className = "service-row";
    
    // Service Dropdown
    const svcSelect = document.createElement("select");
    svcSelect.innerHTML = '<option value="">Select service...</option>' + 
      globalServices.map(s => `<option value="${s.id}" ${r.name===s.name?'selected':''}>${s.name}</option>`).join('');
    
    svcSelect.onchange = (e) => {
      const svc = globalServices.find(s => s.id == e.target.value);
      if(svc) { r.name = svc.name; r.price = parseFloat(svc.rate); }
      document.getElementById("amt-" + r.id).textContent = fmt(r.qty * r.price);
      recalc();
    };

    // QTY Input
    const qtyInput = document.createElement("input");
    qtyInput.type = "number"; qtyInput.value = r.qty; qtyInput.min = "1";
    qtyInput.oninput = (e) => { 
      r.qty = parseFloat(e.target.value) || 1; 
      document.getElementById("amt-" + r.id).textContent = fmt(r.qty * r.price);
      recalc(); 
    };

    const amtCell = document.createElement("div");
    amtCell.className = "amount-cell"; amtCell.id = "amt-" + r.id;
    amtCell.textContent = fmt(r.qty * r.price);

    const delBtn = document.createElement("button");
    delBtn.className = "del-btn"; delBtn.innerHTML = "X";
    delBtn.onclick = () => deleteRow(r.id);

    div.append(svcSelect, qtyInput, amtCell, delBtn);
    container.appendChild(div);
  });
}

function recalc() {
  const sub = rows.reduce((s, r) => s + (r.qty * r.price), 0);
  const discPct = parseFloat(document.getElementById("discount-val").value) || 0;
  const discAmt = sub * (discPct / 100);
  const afterDisc = sub - discAmt;
  
  const gstRate = parseFloat(document.getElementById("gst-rate").value) || 0;
  const gst = afterDisc * (gstRate / 100);
  const total = afterDisc + gst;

  document.getElementById("s-sub").textContent = fmt(sub);
  document.getElementById("s-discount").textContent = fmt(discAmt);
  document.getElementById("s-gst").textContent = fmt(gst);
  document.getElementById("s-total").textContent = fmt(total);

  // --- SMART GST ENGINE ---
  // If the client is in your state, split into CGST/SGST. Otherwise, apply IGST.
  const isLocal = selectedClient && selectedClient.state && selectedClient.state.toLowerCase() === myState.toLowerCase();
  
  document.getElementById("cgst-row").style.display = (gstRate > 0 && isLocal) ? "flex" : "none";
  document.getElementById("sgst-row").style.display = (gstRate > 0 && isLocal) ? "flex" : "none";
  document.getElementById("igst-row").style.display = (gstRate > 0 && !isLocal) ? "flex" : "none";

  if (isLocal) {
    document.getElementById("s-cgst").textContent = fmt(gst / 2);
    document.getElementById("s-sgst").textContent = fmt(gst / 2);
  } else {
    document.getElementById("s-igst").textContent = fmt(gst);
  }
}

async function saveInvoice() {
  if (!selectedClient) return showToast("Please select a client.");
  
  // Compile the perfect "Snapshot Payload" for Django
  const payload = {
    client: selectedClient.id,
    client_name: selectedClient.name,
    client_state: selectedClient.state || '',
    client_address: selectedClient.address || '',
    invoice_number: document.getElementById('inv-num') ? document.getElementById('inv-num').value : '',
    status: document.getElementById('status').value,
    issue_date: document.getElementById('issue-date').value,
    due_date: document.getElementById('due-date').value || document.getElementById('issue-date').value,
    tax_rate: parseFloat(document.getElementById('gst-rate').value),
    discount_percentage: parseFloat(document.getElementById('discount-val').value) || 0,
    total_amount: parseFloat(document.getElementById("s-total").textContent.replace(/[^0-9.-]+/g,"")),
    notes: document.getElementById('notes').value,
    
    // The nested array our custom serializer expects
    lineitem_set: rows.filter(r => r.name).map(r => ({
      description: r.name,
      quantity: r.qty,
      rate: r.price,
      amount: r.qty * r.price
    }))
  };

  try {
    const res = await fetch(`${BASE_API_URL}/invoices/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: JSON.stringify(payload)
    });
    
    if (res.ok) {
      showToast("Invoice Saved Successfully!");
      setTimeout(() => window.location.href = "dashboard.html", 1500); // Redirect back to dash
    } else {
      showToast("Error saving invoice");
    }
  } catch (e) {
    showToast("Network error");
  }
}

init();