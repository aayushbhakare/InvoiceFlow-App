const token = localStorage.getItem('access_token');
const BASE_API_URL = 'http://127.0.0.1:8000/api';
const urlParams = new URLSearchParams(window.location.search);
const editInvoiceId = urlParams.get('id');


let globalClients = [];
let globalServices = [];
let rows = [];
let rowId = 0;
let selectedClient = null;

const myState = "Maharashtra"; 

const fmt = n => "₹" + Math.round(n).toLocaleString("en-IN");
const showToast = msg => { const t = document.getElementById("toast"); t.textContent = msg; t.classList.add("show"); setTimeout(() => t.classList.remove("show"), 3000); }

async function init() {
  document.getElementById("issue-date").value = new Date().toISOString().split("T")[0];
  
 
  try {
    const [clientsRes, servicesRes] = await Promise.all([
      fetch(`${BASE_API_URL}/clients/`, { headers: {'Authorization': `Bearer ${token}`} }),
      fetch(`${BASE_API_URL}/services/`, { headers: {'Authorization': `Bearer ${token}`} })
    ]);

    globalClients = await clientsRes.json();
    globalServices = await servicesRes.json();

    
    const select = document.getElementById('client-select');
    select.innerHTML = '<option value="">— Choose a client —</option>' + 
      globalClients.filter(c => c.is_active).map(c => `<option value="${c.id}">${c.name}</option>`).join('');

  } catch(e) {
    showToast("Failed to connect to database");
  }
  
  addRow(); 
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
  recalc(); 
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
    
    const svcSelect = document.createElement("select");
    svcSelect.innerHTML = '<option value="">Select service...</option>' + 
      globalServices.map(s => `<option value="${s.id}" ${r.name===s.name?'selected':''}>${s.name}</option>`).join('');
    
    svcSelect.onchange = (e) => {
        const svc = globalServices.find(s => s.id == e.target.value);
        if(svc) { 
            r.name = svc.name; 
            r.price = parseFloat(svc.rate); 
            r.service_id = svc.id; // <-- ADD THIS LINE!
        }
        document.getElementById("amt-" + r.id).textContent = fmt(r.qty * r.price);
        recalc();
    };

  
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

async function createInvoice() {
  // Shared logic: validates and saves invoice, returns invoice data or null

  if (window.parent && window.parent.checkProfileCompletion) {
    const isComplete = await window.parent.checkProfileCompletion();
    if (!isComplete) {
      window.parent.toast("Please complete your profile to save data!");
      return null;
    }
  }

  if (!selectedClient) { showToast("Please select a client."); return null; }

  const payload = {
    client: selectedClient.id,
    client_name: selectedClient.name,
    client_state: selectedClient.state || '',
    client_address: selectedClient.address || '',
    status: 'DRAFT',
    issue_date: document.getElementById('issue-date').value,
    due_date: document.getElementById('due-date').value || document.getElementById('issue-date').value,
    tax_rate: parseFloat(document.getElementById('gst-rate').value),
    discount_percentage: parseFloat(document.getElementById('discount-val').value) || 0,
    total_amount: parseFloat(document.getElementById("s-total").textContent.replace(/[^0-9.-]+/g, "")),
    notes: document.getElementById('notes').value,
    items: rows.filter(r => r.name).map(r => ({
      services: parseInt(r.service_id),
      service_name: r.name,
      total_hours: parseFloat(r.qty) || 1,
      rate: parseFloat(r.price) || 0,
      amount: parseFloat(r.qty * r.price) || 0
    }))
  };

  try {

    const url = editInvoiceId 
        ? `${BASE_API_URL}/invoices/${editInvoiceId}/` 
        : `${BASE_API_URL}/invoices/`;
        const method = editInvoiceId ? 'PUT' : 'POST';

        const res = await fetch(url, {
        method: method,
        headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
        body: JSON.stringify(payload)
        });


    if (res.ok) {
      const data = await res.json();
      return data;  
    } else {
      const err = await res.json();
      showToast(err.detail || "Failed to save invoice.");
      return null;
    }
  } catch (e) {
    showToast("Network error");
    return null;
  }
}

async function saveInvoice() {
    const isRecurring = document.getElementById('is-recurring')?.checked;

    if (isRecurring) {

        await saveRecurringTemplate();
    } else {
        
        const invoice = await createInvoice();
        if (invoice) {
            showToast("Invoice Saved Successfully!");
            setTimeout(() => {
                if (window.parent && window.parent.closeModal) {
                    window.parent.closeModal('invoice');
                    if (window.parent.fetchInvoices) window.parent.fetchInvoices();
                    if (window.parent.fetchClients) window.parent.fetchClients();
                }
            }, 1500);
        }
    }
}

async function saveRecurringTemplate() {
    if (!selectedClient) { showToast("Please select a client."); return; }

    const endType = document.querySelector('input[name="recurring-end"]:checked')?.value;

    const payload = {
        client: selectedClient.id,
        frequency: document.getElementById('recurring-freq').value,
        next_issue_date: document.getElementById('recurring-start').value,
        end_date: endType === 'end_date' ? document.getElementById('recurring-end-date').value : null,
        max_occurrences: endType === 'occurrences' ? parseInt(document.getElementById('recurring-occurrences').value) : null,
        is_active: true,
        template_data: {
            items: rows.filter(r => r.name).map(r => ({
                service_id: parseInt(r.service_id),
                service_name: r.name,
                hours: parseFloat(r.qty) || 1,
                rate: parseFloat(r.price) || 0
            })),
            discount_percentage: parseFloat(document.getElementById('discount-val').value) || 0,
            tax_rate: parseFloat(document.getElementById('gst-rate').value) || 18,
            notes: document.getElementById('notes').value || ''
        }
    };

    if (!payload.next_issue_date) { showToast("Please set a start date."); return; }

    try {
        const res = await fetch(`${BASE_API_URL}/recurring-invoices/`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
            body: JSON.stringify(payload)
        });

        if (res.ok) {
            showToast("Recurring invoice scheduled!");
            setTimeout(() => {
                if (window.parent && window.parent.closeModal) {
                    window.parent.closeModal('invoice');
                    if (window.parent.fetchInvoices) window.parent.fetchInvoices();
                }
            }, 1500);
        } else {
            const err = await res.json();
            showToast(err.detail || "Failed to schedule.");
        }
    } catch (e) {
        showToast("Network error.");
    }
}


async function saveAndSendInvoice() {
  const invoice = await createInvoice();
  if (!invoice) return;

  showToast("Sending invoice...");

  try {
    const sendRes = await fetch(`${BASE_API_URL}/invoices/${invoice.id}/send/`, {
      method: 'POST',
      headers: { 'Authorization': `Bearer ${token}` }
    });

    if (sendRes.ok) {
      showToast("Invoice saved & sent successfully!");
    } else {
      const err = await sendRes.json();
      showToast(err.error || "Invoice saved but email failed.");
    }
  } catch (e) {
    showToast("Invoice saved but failed to send email.");
  }

  setTimeout(() => {
    if (window.parent && window.parent.closeModal) {
      window.parent.closeModal('invoice');
      if (window.parent.fetchInvoices) window.parent.fetchInvoices();
      if (window.parent.fetchClients) window.parent.fetchClients();
    }
  }, 1500);
}

function toggleRecurring() {
    const isOn = document.getElementById('is-recurring').checked;
    const options = document.getElementById('recurring-options');
    const dot = document.getElementById('toggle-dot');
    const toggle = document.getElementById('is-recurring').parentElement.querySelector('span');
    
    options.style.display = isOn ? 'block' : 'none';
    dot.style.left = isOn ? '23px' : '3px';
    toggle.style.background = isOn ? '#1D9E75' : '#ccc';

    document.querySelectorAll('.primary-btn, .save-btn').forEach(btn => {
        if (btn.textContent.includes('Save') || btn.textContent.includes('Schedule')) {
            btn.textContent = isOn ? 'Schedule Recurring Invoice' : 'Save Invoice';
        }
    });

  
    const sendBtn = document.querySelector('.send-btn');
    if (sendBtn) sendBtn.style.display = isOn ? 'none' : '';
}

function toggleEndType() {
    const selected = document.querySelector('input[name="recurring-end"]:checked').value;
    document.getElementById('recurring-occurrences').disabled = (selected !== 'occurrences');
    document.getElementById('recurring-end-date').disabled = (selected !== 'end_date');
}



async function loadInvoiceForEdit(invoiceId) {
    try {
        const response = await fetch(`${BASE_API_URL}/invoices/${invoiceId}/`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (!response.ok) return;
        const inv = await response.json();

      
        document.getElementById('client-name').value = inv.client_name || '';
        document.getElementById('issue-date').value = inv.issue_date || '';
        document.getElementById('due-date').value = inv.due_date || '';
        document.getElementById('discount').value = inv.discount_percentage || 0;
        document.getElementById('tax-rate').value = inv.tax_rate || 18;
        if (document.getElementById('notes')) document.getElementById('notes').value = inv.notes || '';

        
        const container = document.getElementById('line-items-container');
        if (container) container.innerHTML = '';
        
        inv.items.forEach(item => {
            
            addLineItem();
            const rows = container.querySelectorAll('.line-item-row');
            const lastRow = rows[rows.length - 1];
            const serviceSelect = lastRow.querySelector('.service-select');
            const hoursInput = lastRow.querySelector('.hours-input');
            if (serviceSelect) serviceSelect.value = item.services || '';
            if (hoursInput) hoursInput.value = item.total_hours || '';
        });


        const submitBtn = document.querySelector('button[type="submit"], .submit-btn');
        if (submitBtn) submitBtn.textContent = 'Update Invoice';

        // Lock if PAID
        if (inv.status === 'PAID') {
            document.querySelectorAll('input, select, textarea, button[type="submit"]')
                .forEach(el => el.disabled = true);
        }
    } catch (error) {
        console.error('Error loading invoice for edit:', error);
    }
}



init().then(() => {
    if (editInvoiceId) {
        loadInvoiceForEdit(editInvoiceId);
    }
});

async function loadInvoiceForEdit(invoiceId) {
    try {
        const response = await fetch(`${BASE_API_URL}/invoices/${invoiceId}/`, {
            headers: { 'Authorization': `Bearer ${token}` }
        });
        if (!response.ok) return;
        const inv = await response.json();

        const clientSelect = document.getElementById('client-select');
        if (clientSelect && inv.client) {
            clientSelect.value = inv.client;
            loadClient();
        }


        document.getElementById('issue-date').value = inv.issue_date || '';
        document.getElementById('due-date').value = inv.due_date || '';
        document.getElementById('discount-val').value = inv.discount_percentage || 0;
        document.getElementById('gst-rate').value = inv.tax_rate || 18;
        document.getElementById('notes').value = inv.notes || '';

        rows = [];
        rowId = 0;
        if (inv.items && inv.items.length > 0) {
            inv.items.forEach(item => {
                const id = ++rowId;
                rows.push({
                    id: id,
                    name: item.service_name || '',
                    qty: parseFloat(item.total_hours) || 1,
                    price: parseFloat(item.service_rate) || 0,
                    service_id: item.services || null
                });
            });
        }
        renderRows();
        recalc();

        document.querySelectorAll('.primary-btn, .save-btn').forEach(btn => {
            if (btn.textContent.includes('Save')) btn.textContent = 'Update Invoice';
        });

        if (inv.status === 'PAID') {
            document.querySelectorAll('input, select, textarea').forEach(el => el.disabled = true);
            document.querySelectorAll('.primary-btn, .save-btn, .del-btn').forEach(btn => btn.disabled = true);
            showToast('This invoice is paid and locked.');
        }
    } catch (error) {
        console.error('Error loading invoice for edit:', error);
        showToast('Failed to load invoice for editing.');
    }
}
