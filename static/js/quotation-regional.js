// quotation-regional.js
// --- Change Status Modal Logic ---
let currentStatusId = null;
function openStatusModal(id, status) {
    currentStatusId = id;
    document.getElementById('statusModal').classList.remove('hidden');
    document.getElementById('statusModal').classList.add('flex');
    document.getElementById('statusQuotationId').value = id;
    document.getElementById('statusSelect').value = status ? status.toUpperCase() : 'PENDING';
    document.getElementById('statusNotes').value = '';
}
function closeStatusModal() {
    document.getElementById('statusModal').classList.add('hidden');
    document.getElementById('statusModal').classList.remove('flex');
    currentStatusId = null;
}
// Handles modal logic and workflow actions for regional quotation page

async function editQuotation(quoteId) {
    const modal = document.getElementById('quoteDrawer');
    document.getElementById('editQuoteId').value = quoteId;
    // Fetch quotation data from backend
    const res = await fetch(`/regional/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    // Populate modal fields
    document.getElementById('editMetaRow').classList.remove('hidden');
    document.getElementById('editQuoteDisplay').value = data.id || '';
    document.getElementById('editIssueDate').value = data.issue_date || '';
    document.getElementById('newBuyer').value = data.buyer || data.client || '';
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
    // Show modal
    modal.classList.remove('opacity-0', 'pointer-events-none');
    modal.classList.add('opacity-100');
}

function closeQuoteDrawer() {
    const modal = document.getElementById('quoteDrawer');
    modal.classList.add('opacity-0', 'pointer-events-none');
    setTimeout(() => {
        modal.classList.remove('opacity-100');
    }, 300);
}

async function draftQuotation(quoteId) {
    const res = await fetch(`/regional/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    document.getElementById('draftPrevId').textContent = data.id || '—';
    document.getElementById('draftPrevDate').textContent = data.issue_date || '';
    document.getElementById('draftPrevBuyer').textContent = data.buyer || data.client || '—';
    document.getElementById('draftPrevTitle').textContent = data.title || '—';
    document.getElementById('draftPrevType').textContent = data.buyer_type || '—';
    document.getElementById('draftPrevCategory').textContent = data.category || '—';
    document.getElementById('draftPrevSupplier').textContent = data.supplier || '—';
    document.getElementById('draftPrevProduct').textContent = data.product || '—';
    document.getElementById('draftPrevQty').textContent = data.quantity || '—';
    document.getElementById('draftPrevUnitPrice').textContent = data.unit_price || '—';
    document.getElementById('draftPrevSubtotal').textContent = (data.quantity && data.unit_price) ? (data.quantity * data.unit_price).toFixed(2) : '—';
    document.getElementById('draftPrevOtherCharges').textContent = data.other_charges || '—';
    document.getElementById('draftPrevOtherChargesNote').textContent = data.other_charges_note || '—';
    document.getElementById('draftPrevTotal').textContent = (data.quantity && data.unit_price ? (data.quantity * data.unit_price) : 0) + (parseFloat(data.other_charges) || 0);
    document.getElementById('draftPrevDeliverFrom').textContent = data.deliver_from || '—';
    document.getElementById('draftPrevDeliverTo').textContent = data.deliver_to || '—';
    document.getElementById('draftPrevStatus').textContent = data.status || '—';
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

function showHistoryModal(quoteId) {
    alert('Show history for Quotation ID: ' + quoteId + '\n(This feature is under development.)');
}
