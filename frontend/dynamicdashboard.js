let currentInvoices = [];
let currentClients = [];
let currentServices = [];
let currentSelectedInvoiceId = null;


if (!localStorage.getItem('access_token')) {
    window.location.replace('landingpage.html');
}


const _originalFetch = window.fetch;
window.fetch = async function(...args) {
    const response = await _originalFetch(...args);
    if (response.status === 401) {
        localStorage.removeItem('access_token');
        alert('Your session has expired. Please log in again.');
        window.location.replace('landingpage.html');
    }
    return response;
};


window.addEventListener('pageshow', function (event) {
    if (event.persisted) {
        if (!localStorage.getItem('access_token')) {
            window.location.replace('landingpage.html');
        }
    }
});

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
            const isMissingData = !profile.account_number || !profile.ifsc_code;
            const name = profile.display_name || 'User';
            const email = profile.email || 'No email';

            const initials = name.substring(0, 2).toUpperCase();

            document.getElementById('nav-avatar').textContent = initials;
            document.getElementById('nav-name').textContent = name;
            document.getElementById('nav-email').textContent = email;


            if (isMissingData) {
                
                window.location.href = 'profile.html';
                return false;
            }
            return true;
        } else {
            window.location.href = 'landingpage.html';
            return false;
        }
    } catch (error) {
        console.error("Gatekeeper error:", error);
        return false;
    }
}

async function protectedOpenModal(type) {
    const isComplete = await checkProfileCompletion();

    if (!isComplete) {
        toast("Please complete your profile to add your own data!");
        setTimeout(() => { window.location.href = 'profile.html'; }, 2000);
        return;
    }

    if (type === 'client') {
        const iframe = document.querySelector('#modal-client iframe');
        if (iframe) iframe.src = 'createclient.html';
    }
    if (type === 'service') {
        const iframe = document.querySelector('#modal-service iframe');
        if (iframe) iframe.src = 'createservice.html';
    }
    openModal(type);
}


async function fetchInvoices() {
    const tbody = document.getElementById('inv-tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="7"><div class="loading-overlay">Loading invoices…</div></td></tr>';
    try {
        const response = await fetch(`${BASE_API_URL}/invoices/`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            currentInvoices = await response.json();
            renderInvoices(currentInvoices);
            updateDashboardMetrics();
            updateDynamicCharts();
            updateReportChart();
        } else {
            if (tbody) tbody.innerHTML = '<tr><td colspan="7"><div class="error-state">Failed to load invoices. Please refresh.</div></td></tr>';
        }
    } catch (error) {
        console.error("Error fetching invoices:", error);
        if (tbody) tbody.innerHTML = '<tr><td colspan="7"><div class="error-state">Network error. Check your connection.</div></td></tr>';
    }
}

async function fetchClients() {
    const grid = document.getElementById('client-grid');
    if (grid) grid.innerHTML = '<div class="loading-overlay">Loading clients…</div>';
    try {
        const response = await fetch(`${BASE_API_URL}/clients/`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            currentClients = await response.json();
            renderClients(currentClients);
        } else {
            if (grid) grid.innerHTML = '<div class="error-state">Failed to load clients.</div>';
        }
    } catch (error) {
        console.error("Error fetching clients");
        if (grid) grid.innerHTML = '<div class="error-state">Network error.</div>';
    }
}

async function fetchServices() {
    const tbody = document.getElementById('service-tbody');
    if (tbody) tbody.innerHTML = '<tr><td colspan="4"><div class="loading-overlay">Loading services…</div></td></tr>';
    try {
        const response = await fetch(`${BASE_API_URL}/services/`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });
        if (response.ok) {
            currentServices = await response.json();
            renderServices(currentServices);
        } else {
            if (tbody) tbody.innerHTML = '<tr><td colspan="4"><div class="error-state">Failed to load services.</div></td></tr>';
        }
    } catch (error) {
        console.error("Error fetching services");
        if (tbody) tbody.innerHTML = '<tr><td colspan="4"><div class="error-state">Network error.</div></td></tr>';
    }
}


function updateDashboardMetrics() {
    let totalBilled = 0;
    let totalCollected = 0;
    let totalOutstanding = 0;
    let totalOverdue = 0;
    let pendingCount = 0;
    let overdueCount = 0;

    let totalTaxable = 0;
    let totalCgst = 0;
    let totalSgst = 0;
    let totalIgst = 0;

    const clientStats = {};

    currentInvoices.forEach(inv => {
        const amount = parseFloat(inv.total_amount) || 0;
        const status = normalizeStatus(inv.status);
        const clientName = inv.client_name || 'Unknown Client';

        totalBilled += amount;

        if (status === 'paid') {
            totalCollected += amount;
        } else if (status === 'pending') {
            totalOutstanding += amount;
            pendingCount++;
        } else if (status === 'overdue') {
            totalOverdue += amount;
            overdueCount++;
        }

        if (status !== 'draft') {
            totalTaxable += parseFloat(inv.taxable_amount) || 0;
            totalCgst += parseFloat(inv.cgst) || 0;
            totalSgst += parseFloat(inv.sgst) || 0;
            totalIgst += parseFloat(inv.igst) || 0;
        }

        if (!clientStats[clientName]) {
            clientStats[clientName] = { billed: 0, collected: 0, pending: 0, overdue: 0, count: 0 };
        }

        clientStats[clientName].billed += amount;
        clientStats[clientName].count += 1;

        if (status === 'paid') clientStats[clientName].collected += amount;
        else if (status === 'pending') clientStats[clientName].pending += amount;
        else if (status === 'overdue') clientStats[clientName].overdue += amount;
    });

    let collectionRate = totalBilled > 0 ? Math.round((totalCollected / totalBilled) * 100) : 0;
    const fmt = n => `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    document.getElementById('dash-billed').textContent = fmt(totalBilled);
    document.getElementById('dash-collected').textContent = fmt(totalCollected);
    document.getElementById('dash-outstanding').textContent = fmt(totalOutstanding);
    document.getElementById('dash-overdue').textContent = fmt(totalOverdue);

    if (currentInvoices.length === 0) {
        document.getElementById('dash-billed-sub').innerHTML = `<span style="color:var(--gray-6)">No invoices yet</span>`;
        document.getElementById('dash-collected-sub').textContent = 'No invoices yet';
        document.getElementById('dash-outstanding-sub').innerHTML = `<span style="color:var(--gray-6)">No invoices yet</span>`;
        document.getElementById('dash-overdue-sub').innerHTML = `<span style="color:var(--gray-6)">No invoices yet</span>`;
    } else {
        document.getElementById('dash-billed-sub').innerHTML = `<i class="ti ti-trending-up" style="font-size:11px"></i> Updated Live`;
        document.getElementById('dash-collected-sub').textContent = `${collectionRate}% collection rate`;
        document.getElementById('dash-outstanding-sub').innerHTML = `<i class="ti ti-clock" style="font-size:11px"></i> ${pendingCount} pending`;
        document.getElementById('dash-overdue-sub').innerHTML = `<i class="ti ti-alert-triangle" style="font-size:11px"></i> ${overdueCount} invoices`;
    }

    const recentTbody = document.getElementById('dash-recent-inv');
    if (recentTbody) {
        const recentList = [...currentInvoices].sort((a, b) => new Date(b.issue_date) - new Date(a.issue_date)).slice(0, 6);
        if (recentList.length === 0) {
            recentTbody.innerHTML = `<tr><td colspan="4" style="text-align:center; padding:20px;">No recent invoices</td></tr>`;
        } else {
            recentTbody.innerHTML = recentList.map(inv => {
                const status = normalizeStatus(inv.status);
                const statusClass = bmap[status] || 'b-draft';
                return `
                <tr onclick="openInvoiceDetail(${inv.id}, '${inv.invoice_number}', '${escapeHtml(inv.client_name || '-')}', '${fmt(parseFloat(inv.total_amount))}', '${status}', '${inv.due_date}')">
                    <td>${escapeHtml(inv.client_name || '-')}</td>
                    <td>${fmt(parseFloat(inv.total_amount))}</td>
                    <td><span class="badge ${statusClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span></td>
                    <td>${inv.due_date || '-'}</td>
                </tr>`;
            }).join('');
        }
    }

    const progressContainer = document.getElementById('dash-collection-progress');
    if (progressContainer) {
        const topClientsProgress = Object.entries(clientStats)
            .sort((a, b) => b[1].billed - a[1].billed)
            .slice(0, 4);

        if (topClientsProgress.length === 0) {
            progressContainer.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 20px; color: var(--gray-6);">No client data yet</div>`;
        } else {
            progressContainer.innerHTML = topClientsProgress.map(([name, stats]) => {
                const percent = stats.billed > 0 ? Math.round((stats.collected / stats.billed) * 100) : 0;
                let statusText = '';
                let statusClass = '';
                let barColor = '';

                if (stats.overdue > 0) {
                    statusText = `${fmt(stats.overdue)} overdue`;
                    statusClass = 'danger';
                    barColor = 'background:var(--danger-txt)';
                } else if (stats.pending > 0) {
                    statusText = `${fmt(stats.pending)} pending`;
                    statusClass = 'warn';
                } else {
                    statusText = `${fmt(stats.collected)} paid`;
                    statusClass = 'up';
                }

                return `
                <div>
                    <div style="display:flex;justify-content:space-between;font-size:12px;margin-bottom:4px">
                        <span>${escapeHtml(name)}</span><span class="${statusClass}">${statusText}</span>
                    </div>
                    <div class="progress-bar"><div class="progress-fill" style="width:${percent}%;${barColor}"></div></div>
                </div>`;
            }).join('');
        }
    }

    const totalGst = totalCgst + totalSgst + totalIgst;

    const repTaxable = document.getElementById('rep-taxable');
    if (repTaxable) {
        repTaxable.textContent = fmt(totalTaxable);
        document.getElementById('rep-gst').textContent = fmt(totalGst);
        document.getElementById('rep-cgst').textContent = fmt(totalCgst);
        document.getElementById('rep-sgst').textContent = fmt(totalSgst);
        document.getElementById('rep-igst').textContent = fmt(totalIgst);
    }

    
    const rBilled = document.getElementById('r-billed');
    if (rBilled) {
        rBilled.textContent = fmt(totalBilled);
        document.getElementById('r-collected').textContent = fmt(totalCollected);
        document.getElementById('r-pending').textContent = fmt(totalOutstanding);
        document.getElementById('r-overdue').textContent = fmt(totalOverdue);
    }


    const repTbody = document.getElementById('report-clients');
    if (repTbody) {
        const sortedClients = Object.entries(clientStats)
            .sort((a, b) => b[1].billed - a[1].billed)
            .slice(0, 5);

        if (sortedClients.length === 0) {
            repTbody.innerHTML = `<tr><td colspan="5" style="text-align:center; padding:20px;">No client data yet</td></tr>`;
        } else {
            repTbody.innerHTML = sortedClients.map(([name, stats]) => {
                const rate = stats.billed > 0 ? Math.round((stats.collected / stats.billed) * 100) : 0;
                const rateClass = rate === 100 ? 'up' : (rate < 50 ? 'danger' : 'warn');
                return `
                <tr>
                    <td style="font-weight:500;">${escapeHtml(name)}</td>
                    <td>${stats.count}</td>
                    <td>${fmt(stats.billed)}</td>
                    <td>${fmt(stats.collected)}</td>
                    <td class="${rateClass}">${rate}%</td>
                </tr>`;
            }).join('');
        }
    }
}

function formatCompact(n) {
    if (n >= 100000) return '₹' + (n / 100000).toFixed(2) + 'L';
    if (n >= 1000) return '₹' + (n / 1000).toFixed(1) + 'K';
    return '₹' + n;
}

const bmap = { paid: 'b-paid', pending: 'b-pending', overdue: 'b-overdue', draft: 'b-draft' };
function normalizeStatus(rawStatus) {
    const s = (rawStatus || 'draft').toLowerCase();
    return s === 'sent' ? 'pending' : s;
}

function renderInvoices(list) {
    const tbody = document.getElementById('inv-tbody');
    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="7" style="text-align: center; padding: 40px;">No invoices found. Click 'New Invoice' to start.</td></tr>`;
        return;
    }

    tbody.innerHTML = list.map(inv => {
        const status = normalizeStatus(inv.status);
        const statusClass = bmap[status] || 'b-draft';
        const formattedAmt = parseFloat(inv.total_amount).toLocaleString('en-IN');

        return `
        <tr onclick="openInvoiceDetail(${inv.id}, '${inv.invoice_number}', '${escapeHtml(inv.client_name || '-')}', '₹${formattedAmt}', '${status}', '${inv.due_date}')">
            <td style="font-family:var(--mono);font-size:11px">${inv.invoice_number || '-'}</td>
            <td>${escapeHtml(inv.client_name || '-')}</td>
            <td>₹${formattedAmt}</td>
            <td>${inv.issue_date || '-'}</td>
            <td>${inv.due_date || '-'}</td>
            <td><span class="badge ${statusClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span></td>
            <td>
                <div style="display:flex;gap:4px">
                    <button class="icon-btn" onclick="event.stopPropagation();currentSelectedInvoiceId=${inv.id};doAction('download')" title="Download"><i class="ti ti-download"></i></button>
                    <button class="icon-btn" onclick="event.stopPropagation();currentSelectedInvoiceId=${inv.id};doAction('reminder')" title="Send/Remind"><i class="ti ti-bell"></i></button>
                    <button class="icon-btn" onclick="event.stopPropagation(); closeModal('detail'); openModal('invoice'); document.querySelector('#modal-invoice iframe').src = 'createinvoice.html?id=${inv.id}';" title="Edit"><i class="ti ti-pencil"></i></button>

                </div>
            </td>
        </tr>`;
    }).join('');
}

function renderClients(list) {
    const grid = document.getElementById('client-grid');
    if (list.length === 0) {
        grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; padding: 40px; background: white; border-radius: 8px;">No clients yet. Add your first client!</div>`;
        return;
    }

    grid.innerHTML = list.map(c => {
        const initials = c.name ? c.name.substring(0, 2).toUpperCase() : 'CL';

        const status = (c.status || 'active').toLowerCase();
        const isInactive = status === 'inactive';

        const badgeClass = isInactive ? 'b-inactive' : 'b-active';
        const cardOpacity = isInactive ? 'opacity: 0.6;' : 'opacity: 1;';
        const toggleIcon = isInactive ? 'ti-rotate-clockwise' : 'ti-archive';
        const toggleTitle = isInactive ? 'Restore to Active' : 'Mark Inactive';

        return `
        <div class="client-card" style="${cardOpacity} transition: opacity 0.3s;">
            <div class="client-avatar" style="background:var(--gray-2);color:var(--black)">${initials}</div>
            <div class="client-name" style="${isInactive ? 'text-decoration: line-through; color: var(--gray-5);' : ''}">${escapeHtml(c.name)}</div>
            <div class="client-meta">
                <i class="ti ti-map-pin" style="font-size:11px"></i> ${escapeHtml(c.address || 'No Address')}
                &nbsp;·&nbsp;
                <span class="badge ${badgeClass}">${status.charAt(0).toUpperCase() + status.slice(1)}</span>
            </div>
            <div style="margin-top:16px; border-top:1px solid var(--gray-2); padding-top:12px; display:flex; justify-content:space-between; align-items:center;">
                <div style="display:flex; gap:16px;">
                    <div>
                        <div style="font-size:13px; font-weight:600;">${c.invoice_count || 0}</div>
                        <div style="font-size:11px; color:var(--gray-6);">Invoices</div>
                    </div>
                    <div>
                        <div style="font-size:13px; font-weight:600;">${formatCompact(c.total_billed || 0)}</div>
                        <div style="font-size:11px; color:var(--gray-6);">Billed</div>
                    </div>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="icon-btn" style="width:28px;height:28px" onclick="event.stopPropagation(); openClientEdit(${c.id})" title="Edit client">
                        <i class="ti ti-pencil" style="font-size:14px"></i>
                    </button>
                    <button class="icon-btn" style="width:28px;height:28px" onclick="event.stopPropagation(); toggleClientStatus(${c.id}, '${status}')" title="${toggleTitle}">
                        <i class="ti ${toggleIcon}" style="font-size:14px"></i>
                    </button>
                </div>
            </div>
        </div>`;
    }).join('');
}

function renderServices(list) {
    const tbody = document.getElementById('service-tbody');
    if (list.length === 0) {
        tbody.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 40px;">No services yet.</td></tr>`;
        return;
    }

    tbody.innerHTML = list.map(s => {
        const safeName = escapeHtml(s.name || '');
        return `
        <tr>
            <td style="font-weight: 500;">${escapeHtml(s.name)}</td>
            <td style="color: var(--gray-6);">${escapeHtml(s.description || '-')}</td>
            <td>₹${parseFloat(s.rate).toLocaleString('en-IN')}</td>
            <td>
                <div style="display:flex;gap:4px">
                    <button class="icon-btn" onclick="openServiceEdit(${s.id})" title="Edit service">
                        <i class="ti ti-pencil"></i>
                    </button>
                    <button class="icon-btn" onclick="deleteService(${s.id}, '${safeName}')" title="Delete service">
                        <i class="ti ti-trash"></i>
                    </button>
                </div>
            </td>
        </tr>`;
    }).join('');
}

function openServiceEdit(serviceId) {
    closeAllModals();
    document.getElementById('modal-service').classList.add('open');
    const iframe = document.querySelector('#modal-service iframe');
    iframe.src = `createservice.html?id=${serviceId}`;
}

async function deleteService(serviceId, serviceName) {
    const confirmed = confirm(
        `Delete "${serviceName}"? This is permanent. Existing invoices that used it will keep showing its name and rate as they were at the time — this only removes it from the catalog for new invoices.`
    );
    if (!confirmed) return;

    try {
        const response = await fetch(`${BASE_API_URL}/services/${serviceId}/`, {
            method: 'DELETE',
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });

        if (response.ok) {
            toast('Service deleted successfully!');
            fetchServices();
        } else {
            toast('Failed to delete service.');
        }
    } catch (error) {
        console.error('Delete Error:', error);
        toast('Network error. Could not delete.');
    }
}

function filterInvoices() {
    const q = document.getElementById('inv-search').value.toLowerCase();
    const s = document.getElementById('inv-status').value.toLowerCase();
    const list = currentInvoices.filter(i =>
        (!q || (i.client_name && i.client_name.toLowerCase().includes(q)) || (i.invoice_number && i.invoice_number.toLowerCase().includes(q))) &&
        (!s || normalizeStatus(i.status) === s)
    );
    renderInvoices(list);
}

function filterClients() {
    const q = document.getElementById('client-search').value.toLowerCase();
    const f = document.getElementById('client-filter').value;
    renderClients(currentClients.filter(c =>
        (!q || c.name.toLowerCase().includes(q)) &&
        (!f || c.status === f)
    ));
}

function filterServices() {
    const q = document.getElementById('service-search').value.toLowerCase();
    const list = currentServices.filter(s =>
        (!q || (s.name && s.name.toLowerCase().includes(q)))
    );
    renderServices(list);
}


function showPage(name) {
    document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
    document.querySelectorAll('.nav-btn, .mobile-nav-btn').forEach(b => b.classList.remove('active'));
    
    document.getElementById('page-' + name).classList.add('active');
    
    document.querySelectorAll(`[onclick*="showPage('${name}'"]`).forEach(b => b.classList.add('active'));
    
    closeAllModals();

    const mobileNav = document.getElementById('mobile-nav');
    if (mobileNav && mobileNav.classList.contains('open')) {
        toggleMobileNav();
    }
}

function openModal(type) {
    closeAllModals();
    document.getElementById('modal-' + type).classList.add('open');
    if (type === 'invoice') {
        const iframe = document.querySelector('#modal-invoice iframe');
        iframe.src = iframe.src;
    }
}

function closeModal(type) {
    document.getElementById('modal-' + type).classList.remove('open');
    if (type === 'client') {
        const iframe = document.querySelector('#modal-client iframe');
        if (iframe) iframe.src = 'createclient.html';
    }
    if (type === 'service') {
        fetchServices();
    }
}

function closeAllModals() { document.querySelectorAll('.modal-backdrop').forEach(m => m.classList.remove('open')); }

document.querySelectorAll('.modal-backdrop').forEach(m => {
    m.addEventListener('click', e => { if (e.target === m) closeAllModals(); });
});

function openInvoiceDetail(id, num, client, amount, status, due) {
    currentSelectedInvoiceId = id;
    document.getElementById('detail-num').textContent = num;
    document.getElementById('detail-client').textContent = client;
    document.getElementById('detail-amount').textContent = amount;
    document.getElementById('detail-due').textContent = due;
    const badge = document.getElementById('detail-badge');
    badge.className = 'badge ' + (bmap[status] || 'b-draft');
    badge.textContent = status.charAt(0).toUpperCase() + status.slice(1);

    const invoice = currentInvoices.find(inv => inv.id === id);
    const statusSelect = document.getElementById('detail-status-select');
    if (statusSelect) statusSelect.value = invoice?.status || 'DRAFT';
    const container = document.getElementById('detail-line-items');
    const items = invoice?.items ?? [];
    const fmt = n => `₹${Number(n).toLocaleString('en-IN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

    if (items.length === 0) {
        container.innerHTML = `<div style="padding:16px;text-align:center;color:var(--gray-6);background:var(--gray-1);border-radius:8px;font-size:13px;">No line items found.</div>`;
    } else {
        container.innerHTML = `
            <div style="font-size:11px;font-weight:600;color:var(--gray-6);text-transform:uppercase;letter-spacing:.05em;margin-bottom:8px">Line Items</div>
            <table style="width:100%;border-collapse:collapse;font-size:13px">
                <thead>
                    <tr style="border-bottom:1px solid var(--border)">
                        <th style="text-align:left;padding:6px 8px;color:var(--gray-6);font-weight:500">Service</th>
                        <th style="text-align:center;padding:6px 8px;color:var(--gray-6);font-weight:500">Hrs/Qty</th>
                        <th style="text-align:right;padding:6px 8px;color:var(--gray-6);font-weight:500">Rate</th>
                        <th style="text-align:right;padding:6px 8px;color:var(--gray-6);font-weight:500">Total</th>
                    </tr>
                </thead>
                <tbody>
                    ${items.map(item => `
                        <tr style="border-bottom:1px solid var(--gray-1)">
                            <td style="padding:8px">${escapeHtml(item.service_name || item.name || '-')}</td>
                            <td style="padding:8px;text-align:center">${item.total_hours ?? item.quantity ?? '-'}</td>
                            <td style="padding:8px;text-align:right">${item.service_rate != null ? fmt(item.service_rate) : '-'}</td>
                            <td style="padding:8px;text-align:right;font-weight:600">${fmt(item.line_total ?? item.amount ?? 0)}</td>
                        </tr>`).join('')}
                </tbody>
            </table>`;
    }
    const editBtn = document.getElementById('detail-edit-btn');
    if (editBtn) {
        editBtn.onclick = function () {
            closeModal('detail');
            openModal('invoice');
            const iframe = document.querySelector('#modal-invoice iframe');
            iframe.src = `createinvoice.html?id=${id}`;
        };
    }
    openModal('detail');
    fetchTimeline(id);
}

async function doAction(type) {
    if (!currentSelectedInvoiceId) return;

    if (type === 'download') {
        toast("Generating PDF securely...");

        try {
            const response = await fetch(`${BASE_API_URL}/invoices/${currentSelectedInvoiceId}/download/`, {
                method: 'GET',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            });

            if (response.ok) {
                
                const blob = await response.blob();

                
                const downloadUrl = window.URL.createObjectURL(blob);

                
                const a = document.createElement('a');
                a.href = downloadUrl;

                
                const disposition = response.headers.get('Content-Disposition');
                let filename = `Invoice_${currentSelectedInvoiceId}.pdf`;
                if (disposition && disposition.indexOf('filename=') !== -1) {
                    filename = disposition.split('filename=')[1].replace(/"/g, '');
                }

                a.download = filename;
                document.body.appendChild(a);
                a.click();
                a.remove();
                window.URL.revokeObjectURL(downloadUrl);

                toast("PDF Downloaded successfully!");
            } else {
                toast("Failed to download PDF.");
            }
        } catch (error) {
            console.error("Download Error:", error);
            toast("Network error. Could not download.");
        }
    }
    else if (type === 'paid') {
        const btn = document.querySelector(`button[onclick="doAction('paid')"]`);
        const originalText = btn.innerHTML;
        btn.innerHTML = `<i class="ti ti-loader" style="font-size:12px"></i> Updating...`;

        try {
            const response = await fetch(`${BASE_API_URL}/invoices/${currentSelectedInvoiceId}/`, {
                method: 'PATCH',
                headers: {
                    'Content-Type': 'application/json',
                    'Authorization': `Bearer ${localStorage.getItem('access_token')}`
                },
                body: JSON.stringify({ status: 'PAID' })
            });

            if (response.ok) {
                toast("Invoice marked as paid! Revenue updated.");
                closeModal('detail');
                fetchInvoices();
            } else {
                const err = await response.json();
                toast(err.status ? err.status[0] : "Failed to update invoice.");
            }
        } catch (error) {
            console.error("Update Error:", error);
            toast("Network error. Could not update.");
        } finally {
            btn.innerHTML = originalText;
        }
    }

    else if (type === 'reminder') {
        if (!currentSelectedInvoiceId) return;

        toast("Sending...");

        try {
            const response = await fetch(`${BASE_API_URL}/invoices/${currentSelectedInvoiceId}/send/`, {
                method: 'POST',
                headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
            });

            if (response.ok) {
                const data = await response.json();
                toast(data.message || "Sent successfully!");
                closeModal('detail');
                fetchInvoices();
            } else {
                const err = await response.json();
                toast(err.error || "Failed to send.");
            }
        } catch (error) {
            console.error("Send Error:", error);
            toast("Network error. Could not send.");
        }
    }
}

async function fetchTimeline(invoiceId) {
    const container = document.getElementById('timeline-entries');
    container.innerHTML = '<div style="color:var(--gray-6); padding:8px 0;">Loading...</div>';

    try {
        const response = await fetch(`${BASE_API_URL}/invoices/${invoiceId}/timeline/`, {
            headers: { 'Authorization': `Bearer ${localStorage.getItem('access_token')}` }
        });

        if (!response.ok) {
            container.innerHTML = '<div style="color:var(--gray-6); padding:8px 0;">Unable to load timeline.</div>';
            return;
        }

        const logs = await response.json();

        if (logs.length === 0) {
            container.innerHTML = '<div style="color:var(--gray-6); padding:8px 0;">No activity yet.</div>';
            return;
        }

        const iconMap = {
            'INVOICE_SENT': { icon: 'ti-send', color: '#1D9E75' },
            'REMINDER_BEFORE_DUE': { icon: 'ti-bell', color: '#f59e0b' },
            'REMINDER_ON_DUE': { icon: 'ti-bell-ringing', color: '#f59e0b' },
            'REMINDER_AFTER_DUE': { icon: 'ti-alert-triangle', color: '#ef4444' },
            'PAYMENT_RECEIVED': { icon: 'ti-circle-check', color: '#1D9E75' },
            'STATUS_CHANGED': { icon: 'ti-refresh', color: '#6b7280' },
        };

        container.innerHTML = logs.map(log => {
            const info = iconMap[log.event_type] || { icon: 'ti-info-circle', color: '#6b7280' };
            const time = new Date(log.timestamp).toLocaleString('en-IN', {
                day: 'numeric', month: 'short', year: 'numeric',
                hour: '2-digit', minute: '2-digit',
            });
            const statusBadge = log.delivery_status === 'FAILED'
                ? `<span style="color:#ef4444; font-size:11px; margin-left:6px;">✗ Failed</span>`
                : '';

            return `
                <div style="display:flex; align-items:flex-start; gap:10px; padding:8px 0; border-bottom:1px solid #f3f4f6;">
                    <i class="ti ${info.icon}" style="color:${info.color}; font-size:16px; margin-top:2px;"></i>
                    <div style="flex:1;">
                        <div style="font-weight:500; color:#111827;">
                            ${escapeHtml(log.event_display)}${statusBadge}
                        </div>
                        <div style="font-size:11px; color:#9ca3af; margin-top:2px;">
                            ${time}${log.recipient_email ? ' · ' + escapeHtml(log.recipient_email) : ''}
                        </div>
                        ${log.error_message ? `<div style="font-size:11px; color:#ef4444; margin-top:2px;">${escapeHtml(log.error_message)}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');

    } catch (error) {
        console.error("Timeline Error:", error);
        container.innerHTML = '<div style="color:var(--gray-6); padding:8px 0;">Failed to load timeline.</div>';
    }
}

async function updateInvoiceStatus() {
    if (!currentSelectedInvoiceId) return;

    const select = document.getElementById('detail-status-select');
    const newStatus = select.value;

    const btn = document.querySelector(`button[onclick="updateInvoiceStatus()"]`);
    const originalText = btn.innerHTML;
    btn.innerHTML = `<i class="ti ti-loader" style="font-size:12px"></i> Updating...`;

    try {
        const response = await fetch(`${BASE_API_URL}/invoices/${currentSelectedInvoiceId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            toast("Invoice status updated!");
            closeModal('detail');
            fetchInvoices();
        } else {
            const err = await response.json();
            toast(err.status ? err.status[0] : "Failed to update invoice.");
        }
    } catch (error) {
        console.error("Update Error:", error);
        toast("Network error. Could not update.");
    } finally {
        btn.innerHTML = originalText;
    }
}

function toast(msg) {
    const n = document.getElementById('notify');
    n.textContent = msg;
    n.classList.add('show');
    clearTimeout(n._t);
    n._t = setTimeout(() => n.classList.remove('show'), 2500);
}

function toggleProfileMenu() {
    const dropdown = document.getElementById('profile-dropdown');
    dropdown.style.display = (dropdown.style.display === 'block') ? 'none' : 'block';
}

function openClientEdit(clientId) {
    closeAllModals();
    document.getElementById('modal-client').classList.add('open');
    const iframe = document.querySelector('#modal-client iframe');
    iframe.src = `createclient.html?id=${clientId}`;
}

async function toggleClientStatus(clientId, currentStatus) {
    
    const newStatus = currentStatus === 'active' ? 'inactive' : 'active';

    try {
        const response = await fetch(`${BASE_API_URL}/clients/${clientId}/`, {
            method: 'PATCH',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${localStorage.getItem('access_token')}`
            },
            body: JSON.stringify({ status: newStatus })
        });

        if (response.ok) {
            toast(`Client successfully marked as ${newStatus}!`);
            fetchClients();
        } else {
            const err = await response.json();
            toast("Failed to update client status.");
            console.error(err);
        }
    } catch (error) {
        console.error("Status Update Error:", error);
        toast("Network error. Could not update client.");
    }
}


window.addEventListener('click', function (e) {
    const dropdown = document.getElementById('profile-dropdown');
    const avatar = document.querySelector('.avatar');
    if (dropdown && avatar && !avatar.contains(e.target) && !dropdown.contains(e.target)) {
        dropdown.style.display = 'none';
    }
});

function logout() {
    localStorage.removeItem('access_token');
    window.location.replace('landingpage.html');
}


let dashChartInstance = null;


function updateDynamicCharts() {
    const ctx = document.getElementById('dash-chart');
    if (!ctx) return;

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const today = new Date();
    const labels = [];
    const billedData = [0, 0, 0, 0, 0, 0];
    const collectedData = [0, 0, 0, 0, 0, 0];

    for (let i = 5; i >= 0; i--) {
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        labels.push(monthNames[d.getMonth()]);
    }

    currentInvoices.forEach(inv => {
        if (!inv.issue_date) return;

        const invDate = new Date(inv.issue_date);
        const amount = parseFloat(inv.total_amount) || 0;
        const status = normalizeStatus(inv.status);

        const monthDiff = (today.getFullYear() - invDate.getFullYear()) * 12 + (today.getMonth() - invDate.getMonth());

        if (monthDiff >= 0 && monthDiff <= 5) {
            const index = 5 - monthDiff;

            billedData[index] += amount;

            if (status === 'paid') {
                collectedData[index] += amount;
            }
        }
    });

    const hasData = billedData.some(v => v > 0) || collectedData.some(v => v > 0);

    
    const chartWrap = ctx.closest('.chart-wrap');
    let emptyMsg = chartWrap.querySelector('.chart-empty-msg');
    if (!hasData) {
        if (!emptyMsg) {
            emptyMsg = document.createElement('div');
            emptyMsg.className = 'chart-empty-msg';
            emptyMsg.style.cssText = 'position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:var(--gray-6);font-size:13px;';
            emptyMsg.textContent = 'No billing data yet';
            chartWrap.appendChild(emptyMsg);
        }
        emptyMsg.style.display = 'flex';
    } else if (emptyMsg) {
        emptyMsg.style.display = 'none';
    }

    if (dashChartInstance) {
        dashChartInstance.destroy();
    }

    dashChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                { label: 'Billed', data: billedData, backgroundColor: '#9FE1CB', borderRadius: 3 },
                { label: 'Collected', data: collectedData, backgroundColor: '#1D9E75', borderRadius: 3 },
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ₹${c.raw.toLocaleString('en-IN')}` } }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true, grid: { color: 'rgba(0,0,0,.04)' },
                    ticks: { callback: v => '₹' + v.toLocaleString('en-IN') }
                }
            }
        }
    });
}

let reportChartInstance = null;

function updateReportChart() {
    const ctx = document.getElementById('report-chart');
    if (!ctx) return;

    const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
    const today = new Date();
    const labels = [];
    const billedData = [0, 0, 0, 0, 0, 0];
    const collectedData = [0, 0, 0, 0, 0, 0];

    for (let i = 5; i >= 0; i--) {
        const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
        labels.push(monthNames[d.getMonth()]);
    }

    currentInvoices.forEach(inv => {
        if (!inv.issue_date) return;
        const invDate = new Date(inv.issue_date);
        const amount = parseFloat(inv.total_amount) || 0;
        const status = normalizeStatus(inv.status);
        const monthDiff = (today.getFullYear() - invDate.getFullYear()) * 12 + (today.getMonth() - invDate.getMonth());
        if (monthDiff >= 0 && monthDiff <= 5) {
            const index = 5 - monthDiff;
            billedData[index] += amount;
            if (status === 'paid') collectedData[index] += amount;
        }
    });

    if (reportChartInstance) reportChartInstance.destroy();

    reportChartInstance = new Chart(ctx, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                { label: 'Billed', data: billedData, backgroundColor: '#9FE1CB', borderRadius: 3 },
                { label: 'Collected', data: collectedData, backgroundColor: '#1D9E75', borderRadius: 3 },
            ]
        },
        options: {
            responsive: true, maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { callbacks: { label: c => ` ${c.dataset.label}: ₹${c.raw.toLocaleString('en-IN')}` } }
            },
            scales: {
                x: { grid: { display: false } },
                y: {
                    beginAtZero: true, grid: { color: 'rgba(0,0,0,.04)' },
                    ticks: { callback: v => '₹' + v.toLocaleString('en-IN') }
                }
            }
        }
    });
}

async function initializeDashboard() {
    const isComplete = await checkProfileCompletion();
    if (isComplete) {
        await Promise.all([
            fetchInvoices(),
            fetchClients(),
            fetchServices()
        ]);

        updateDynamicCharts();
    }
}

function exportReportCSV() {
    if (!currentInvoices || currentInvoices.length === 0) {
        toast('No invoice data to export yet.');
        return;
    }

    let totalBilled = 0, totalCollected = 0, totalOutstanding = 0, totalOverdue = 0;
    let totalTaxable = 0, totalCgst = 0, totalSgst = 0, totalIgst = 0;
    const clientStats = {};

    currentInvoices.forEach(inv => {
        const amount = parseFloat(inv.total_amount) || 0;
        const status = normalizeStatus(inv.status);
        const clientName = inv.client_name || 'Unknown Client';

        totalBilled += amount;
        if (status === 'paid') totalCollected += amount;
        else if (status === 'pending') totalOutstanding += amount;
        else if (status === 'overdue') totalOverdue += amount;

        if (status !== 'draft') {
            totalTaxable += parseFloat(inv.taxable_amount) || 0;
            totalCgst += parseFloat(inv.cgst) || 0;
            totalSgst += parseFloat(inv.sgst) || 0;
            totalIgst += parseFloat(inv.igst) || 0;
        }

        if (!clientStats[clientName]) {
            clientStats[clientName] = { billed: 0, collected: 0, count: 0 };
        }
        clientStats[clientName].billed += amount;
        clientStats[clientName].count += 1;
        if (status === 'paid') clientStats[clientName].collected += amount;
    });

    const totalGst = totalCgst + totalSgst + totalIgst;
    const fmt2 = n => Number(n || 0).toFixed(2);
    const rows = [];

    rows.push(['Revenue Summary']);
    rows.push(['Billed', 'Collected', 'Pending', 'Overdue']);
    rows.push([fmt2(totalBilled), fmt2(totalCollected), fmt2(totalOutstanding), fmt2(totalOverdue)]);
    rows.push([]);

    rows.push(['GST Summary']);
    rows.push(['Taxable Value', 'Total GST', 'CGST', 'SGST', 'IGST']);
    rows.push([fmt2(totalTaxable), fmt2(totalGst), fmt2(totalCgst), fmt2(totalSgst), fmt2(totalIgst)]);
    rows.push([]);

    rows.push(['Top Clients by Revenue']);
    rows.push(['Client', 'Invoices', 'Total Billed', 'Collected', 'Collection Rate']);
    Object.entries(clientStats)
        .sort((a, b) => b[1].billed - a[1].billed)
        .forEach(([name, stats]) => {
            const rate = stats.billed > 0 ? Math.round((stats.collected / stats.billed) * 100) : 0;
            rows.push([name, stats.count, fmt2(stats.billed), fmt2(stats.collected), rate + '%']);
        });
    rows.push([]);

    rows.push(['Invoice Detail']);
    rows.push(['Invoice #', 'Client', 'State', 'Issue Date', 'Due Date', 'Status', 'Subtotal', 'Discount', 'Taxable Value', 'CGST', 'SGST', 'IGST', 'Total']);
    [...currentInvoices]
        .sort((a, b) => new Date(b.issue_date) - new Date(a.issue_date))
        .forEach(inv => {
            const statusLabel = normalizeStatus(inv.status);
            rows.push([
                inv.invoice_number || '',
                inv.client_name || '',
                inv.client_state || '',
                inv.issue_date || '',
                inv.due_date || '',
                statusLabel.charAt(0).toUpperCase() + statusLabel.slice(1),
                fmt2(inv.subtotal),
                fmt2(inv.discount_amount),
                fmt2(inv.taxable_amount),
                fmt2(inv.cgst),
                fmt2(inv.sgst),
                fmt2(inv.igst),
                fmt2(inv.total_amount)
            ]);
        });

    const csvContent = rows.map(row =>
        row.map(cell => {
            const str = String(cell ?? '');
            return /[",\n]/.test(str) ? `"${str.replace(/"/g, '""')}"` : str;
        }).join(',')
    ).join('\n');

    const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    const todayStr = new Date().toISOString().split('T')[0];
    a.href = url;
    a.download = `InvoiceFlow_Report_${todayStr}.csv`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    toast('Report downloaded!');
}

function toggleMobileNav() {
    const nav = document.getElementById('mobile-nav');
    nav.classList.toggle('open');
}

document.addEventListener("DOMContentLoaded", initializeDashboard);