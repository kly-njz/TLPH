// Show draft preview modal for a quotation
async function openDraftPreview(quoteId) {
    const res = await fetch(`/superadmin/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    const buyer = data.buyer || data.buyer_entity || data.client || '';
    const buyerType = data.buyer_type || data.buyerType || data.buyer_category || '';
    const title = data.title || data.description || '';
    const category = data.category || '';
    const supplier = data.supplier || '';
    const product = data.product || data.item || '';
    const quantity = toNumber(data.quantity ?? data.qty ?? 0);
    const unitPrice = toNumber(data.unit_price ?? data.unitPrice ?? 0);
    const otherCharges = toNumber(data.other_charges ?? data.otherCharges ?? 0);
    const subtotal = quantity * unitPrice;
    const total = toNumber(data.total ?? (subtotal + otherCharges));
    const issueDate = data.issue_date || data.date || data.created_at || '';
    const statusLabel = formatStatus(data.status);
    // Populate preview modal fields
    document.getElementById('draftPrevId').textContent = data.id || '—';
    document.getElementById('draftPrevDate').textContent = issueDate ? formatDate(issueDate) : '—';
    document.getElementById('draftPrevBuyer').textContent = buyer || '—';
    document.getElementById('draftPrevTitle').textContent = title || '—';
    document.getElementById('draftPrevType').textContent = buyerType || '—';
    document.getElementById('draftPrevCategory').textContent = category || '—';
    document.getElementById('draftPrevSupplier').textContent = supplier || '—';
    document.getElementById('draftPrevProduct').textContent = product || '—';
    document.getElementById('draftPrevQty').textContent = quantity ? String(quantity) : '—';
    document.getElementById('draftPrevUnitPrice').textContent = formatMoney(unitPrice);
    document.getElementById('draftPrevSubtotal').textContent = formatMoney(subtotal);
    document.getElementById('draftPrevOtherCharges').textContent = formatMoney(otherCharges);
    document.getElementById('draftPrevOtherChargesNote').textContent = data.other_charges_note || data.otherChargesNote || '—';
    document.getElementById('draftPrevTotal').textContent = formatMoney(total);
    document.getElementById('draftPrevDeliverFrom').textContent = data.deliver_from || '—';
    document.getElementById('draftPrevDeliverTo').textContent = data.deliver_to || '—';
    const statusEl = document.getElementById('draftPrevStatus');
    statusEl.textContent = statusLabel || '—';
    applyStatusBadge(statusEl, data.status);
    // Show modal
    const modal = document.getElementById('draftPreviewModal');
    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('opacity-100'), 10);
}
function closeDraftPreview() {
    const modal = document.getElementById('draftPreviewModal');
    modal.classList.remove('opacity-100');
    setTimeout(() => modal.classList.add('hidden'), 300);
}

// Download delivery details as PDF (simple implementation)
async function downloadDeliveryDetails(quoteId) {
    const res = await fetch(`/superadmin/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    // Use jsPDF to generate a simple PDF
    const doc = new window.jspdf.jsPDF();
    doc.setFontSize(12);
    doc.text('Delivery Details', 10, 10);
    doc.setFontSize(10);
    doc.text(`Quotation ID: ${data.id || ''}`, 10, 20);
    doc.text(`Buyer: ${data.buyer || ''}`, 10, 28);
    doc.text(`Supplier: ${data.supplier || ''}`, 10, 36);
    doc.text(`Deliver From: ${data.deliver_from || ''}`, 10, 44);
    doc.text(`Deliver To: ${data.deliver_to || ''}`, 10, 52);
    doc.text(`Product: ${data.product || ''}`, 10, 60);
    doc.text(`Quantity: ${data.quantity || ''}`, 10, 68);
    doc.text(`Status: ${data.status || ''}`, 10, 76);
    doc.save(`delivery-details-${data.id || quoteId}.pdf`);
}
// quotation-superadmin.js
// Handles modal logic and workflow actions for superadmin quotation page

function toNumber(value) {
    const parsed = parseFloat(value);
    return Number.isFinite(parsed) ? parsed : 0;
}

function computeTotal(quantity, unitPrice, otherCharges) {
    return (toNumber(quantity) * toNumber(unitPrice)) + toNumber(otherCharges);
}

function formatDate(value) {
    if (!value) return '';
    const text = String(value);
    return text.split('T')[0];
}

function formatMoney(value) {
    const num = toNumber(value);
    return `₱${num.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

function formatStatus(value) {
    if (!value) return '';
    return String(value)
        .replace(/[_-]+/g, ' ')
        .replace(/\b\w/g, (m) => m.toUpperCase());
}

function applyStatusBadge(el, status) {
    if (!el) return;
    const key = String(status || '').toLowerCase();
    let cls = 'status-badge bg-amber-100 text-amber-700 border border-amber-300';
    if (key === 'delivered') cls = 'status-badge bg-emerald-100 text-emerald-700 border border-emerald-300';
    if (key === 'in-transit') cls = 'status-badge bg-blue-100 text-blue-700 border border-blue-300';
    if (key === 'for-delivery') cls = 'status-badge bg-indigo-100 text-indigo-700 border border-indigo-300';
    if (key === 'cancelled') cls = 'status-badge bg-rose-100 text-rose-700 border border-rose-300';
    el.className = cls;
}

function setFieldLock(el, locked) {
    if (!el) return;
    if (el.tagName === 'SELECT') {
        el.disabled = locked;
    } else {
        el.readOnly = locked;
    }
    if (locked) {
        el.classList.add('bg-slate-100', 'text-slate-500', 'cursor-not-allowed');
    } else {
        el.classList.remove('bg-slate-100', 'text-slate-500', 'cursor-not-allowed');
    }
}

function toggleEditLocks(locked) {
    setFieldLock(document.getElementById('newIssueDate'), locked);
    setFieldLock(document.getElementById('newBuyer'), locked);
}

function getQuotePayload() {
    const quantity = toNumber(document.getElementById('newQty').value);
    const unitPrice = toNumber(document.getElementById('newPrice').value);
    const otherCharges = toNumber(document.getElementById('newOtherCharges').value);
    const buyerType = document.getElementById('newBuyerType').value;
    return {
        issue_date: document.getElementById('newIssueDate').value,
        buyer: document.getElementById('newBuyer').value,
        title: document.getElementById('newTitle').value,
        category: document.getElementById('newCategory').value,
        supplier: document.getElementById('newSupplier').value,
        deliver_from: document.getElementById('newDeliverFrom').value,
        deliver_to: document.getElementById('newDeliverTo').value,
        status: document.getElementById('newStatus').value,
        buyer_type: buyerType,
        deliver_to_type: buyerType,
        product: document.getElementById('newProd').value,
        quantity,
        unit_price: unitPrice,
        other_charges: otherCharges,
        other_charges_note: document.getElementById('newOtherChargesNote').value,
        total: computeTotal(quantity, unitPrice, otherCharges)
    };
}

function showQuoteDrawer() {
    const modal = document.getElementById('quoteDrawer');
    const overlay = document.getElementById('drawerOverlay');
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.add('opacity-100'), 10);
    modal.classList.remove('opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100');
    modal.classList.replace('scale-95', 'scale-100');
}

function resetQuoteForm() {
    toggleEditLocks(false);
    document.getElementById('editQuoteId').value = '';
    document.getElementById('editMetaRow').classList.add('hidden');
    document.getElementById('newStatusRow').classList.add('hidden');
    document.getElementById('quoteDrawerTitle').textContent = 'Generate Quotation';
    document.getElementById('quoteSubmitBtn').textContent = 'Draft Quotation';

    document.getElementById('newIssueDate').value = new Date().toISOString().slice(0, 10);
    document.getElementById('newBuyer').value = '';
    document.getElementById('newTitle').value = '';
    document.getElementById('newCategory').value = '';
    document.getElementById('newSupplier').value = '';
    document.getElementById('newDeliverFrom').value = '';
    document.getElementById('newDeliverTo').value = '';
    document.getElementById('newStatus').value = 'pending';
    document.getElementById('newBuyerType').value = 'company';
    document.getElementById('newProd').value = '';
    document.getElementById('newQty').value = '';
    document.getElementById('newPrice').value = '';
    document.getElementById('newOtherCharges').value = 0;
    document.getElementById('newOtherChargesNote').value = '';
}

function openQuoteDrawer() {
    resetQuoteForm();
    showQuoteDrawer();
}

// Open the edit modal and populate fields
async function openEditDrawer(quoteId) {
    const modal = document.getElementById('quoteDrawer');
    document.getElementById('editQuoteId').value = quoteId;
    // Fetch quotation data from backend
    const res = await fetch(`/superadmin/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    // Populate modal fields
    document.getElementById('editMetaRow').classList.remove('hidden');
    document.getElementById('editQuoteDisplay').value = data.id || '';
    document.getElementById('newIssueDate').value = data.issue_date || data.date || '';
    document.getElementById('newBuyer').value = data.buyer || '';
    document.getElementById('newTitle').value = data.title || '';
    document.getElementById('newCategory').value = data.category || '';
    document.getElementById('newSupplier').value = data.supplier || '';
    document.getElementById('newDeliverFrom').value = data.deliver_from || '';
    document.getElementById('newDeliverTo').value = data.deliver_to || '';
    document.getElementById('newStatusRow').classList.remove('hidden');
    document.getElementById('newStatus').value = data.status || 'pending';
    document.getElementById('newBuyerType').value = data.buyer_type || 'company';
    document.getElementById('newProd').value = data.product || '';
    document.getElementById('newQty').value = data.quantity || 0;
    document.getElementById('newPrice').value = data.unit_price || 0;
    document.getElementById('newOtherCharges').value = data.other_charges || 0;
    document.getElementById('newOtherChargesNote').value = data.other_charges_note || '';
    document.getElementById('quoteDrawerTitle').textContent = 'Edit Quotation';
    document.getElementById('quoteSubmitBtn').textContent = 'Update Quotation';
    toggleEditLocks(true);
    // Show modal
    const overlay = document.getElementById('drawerOverlay');
    overlay.classList.remove('hidden');
    setTimeout(() => overlay.classList.add('opacity-100'), 10);
    modal.classList.remove('opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100');
    modal.classList.replace('scale-95', 'scale-100');
}

function closeQuoteDrawer() {
    const modal = document.getElementById('quoteDrawer');
    const overlay = document.getElementById('drawerOverlay');
    overlay.classList.remove('opacity-100');
    setTimeout(() => overlay.classList.add('hidden'), 300);
    modal.classList.add('opacity-0', 'pointer-events-none');
    modal.classList.replace('scale-100', 'scale-95');
    setTimeout(() => {
        modal.classList.remove('opacity-100');
    }, 300);
}

// Handle form submit for updating quotation
const quoteForm = document.getElementById('newQuoteForm');
if (quoteForm) {
    quoteForm.onsubmit = async function(e) {
        e.preventDefault();
        const quoteId = document.getElementById('editQuoteId').value;
        const payload = getQuotePayload();
        const isEdit = Boolean(quoteId);
        const url = isEdit
            ? `/superadmin/api/quotation/${quoteId}/update`
            : '/superadmin/api/quotation/create';
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert(isEdit ? 'Quotation updated successfully.' : 'Quotation created successfully.');
            closeQuoteDrawer();
            window.location.reload();
        } else {
            alert(data.error || (isEdit ? 'Failed to update quotation.' : 'Failed to create quotation.'));
        }
    }
}
