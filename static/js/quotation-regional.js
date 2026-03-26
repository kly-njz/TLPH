// quotation-regional.js
// --- View Quotation Modal Logic ---
window.viewQuotation = function(btn) {
    const row = btn.closest('tr');
    document.getElementById('vqNumber').textContent = row.getAttribute('data-number') || 'N/A';
    document.getElementById('vqClient').textContent = row.getAttribute('data-client') || 'N/A';
    document.getElementById('vqMunicipality').textContent = row.getAttribute('data-municipality') || 'N/A';
    document.getElementById('vqStatus').textContent = row.getAttribute('data-status') || 'N/A';
    document.getElementById('vqDate').textContent = row.getAttribute('data-date') || 'N/A';
    let amt = row.getAttribute('data-amount') || '0';
    let formattedAmt = parseFloat(amt).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
    document.getElementById('vqAmount').textContent = '₱ ' + formattedAmt;
    // Add more fields here if needed for full parity
    const modal = document.getElementById('viewQuotationModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

function closeViewModal() {
    const modal = document.getElementById('viewQuotationModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

window.closeViewModal = closeViewModal;
}

// --- Forward Modal Logic ---
let currentForwardId = null;
window.openForwardModal = function(btn) {
    const row = btn.closest('tr');
    const id = row.getAttribute('data-id');
    const municipality = row.getAttribute('data-municipality') || '';
    currentForwardId = id;
    document.getElementById('forwardQuotationId').value = id;
    document.getElementById('forwardMunicipality').value = municipality;
    const modal = document.getElementById('forwardModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}
function closeForwardModal() {
    const modal = document.getElementById('forwardModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
    currentForwardId = null;
}

window.closeForwardModal = closeForwardModal;
}
// Forward form submit stub
function submitForward(e) {
    e.preventDefault();
    alert('Forwarding quotation (stub). Implement backend logic.');
    closeForwardModal();
}

window.submitForward = submitForward;
}

function closeHistoryModal() {
    const modal = document.getElementById('historyModal');
    modal.classList.add('hidden');
    modal.classList.remove('flex');
}

window.closeHistoryModal = closeHistoryModal;
}
// Show history modal and load content stub
function showHistoryModal(quoteId) {
    document.getElementById('historyContent').textContent = 'History for Quotation ID: ' + quoteId + ' (stub, implement backend fetch)';
    const modal = document.getElementById('historyModal');
    modal.classList.remove('hidden');
    modal.classList.add('flex');
}

window.showHistoryModal = showHistoryModal;
}
// Status form submit stub
function submitStatus(e) {
    e.preventDefault();
    alert('Status update (stub). Implement backend logic.');
    closeStatusModal();
}

window.submitStatus = submitStatus;
}
// --- Change Status Modal Logic ---
let currentStatusId = null;
window.openStatusModal = function(btn) {
    const row = btn.closest('tr');
    const id = row.getAttribute('data-id');
    const status = row.getAttribute('data-status') || 'PENDING';
    currentStatusId = id;
    document.getElementById('statusModal').classList.remove('hidden');
    document.getElementById('statusModal').classList.add('flex');
    document.getElementById('statusQuotationId').value = id;
    document.getElementById('statusSelect').value = status;
    document.getElementById('statusNotes').value = '';
}
function closeStatusModal() {
    document.getElementById('statusModal').classList.add('hidden');
    document.getElementById('statusModal').classList.remove('flex');
    currentStatusId = null;
}

window.closeStatusModal = closeStatusModal;
}
// Handles modal logic and workflow actions for regional quotation page

window.editQuotation = async function(btn) {
    const row = btn.closest('tr');
    // Use row data attributes for instant modal population
    document.getElementById('editMetaRow').classList.remove('hidden');
    document.getElementById('editQuoteDisplay').value = row.getAttribute('data-number') || row.getAttribute('data-id') || '';
    document.getElementById('editQuoteId').value = row.getAttribute('data-id') || '';
    let rawDate = row.getAttribute('data-date') || '';
    let formattedDate = rawDate.includes('T') ? rawDate.substring(0, 10) : rawDate;
    document.getElementById('editIssueDate').value = formattedDate;
    document.getElementById('newBuyer').value = row.getAttribute('data-client') || '';
    document.getElementById('newTitle').value = row.getAttribute('data-title') || '';
    document.getElementById('newCategory').value = row.getAttribute('data-category') || '';
    document.getElementById('newSupplier').value = row.getAttribute('data-supplier') || '';
    document.getElementById('newDeliverFrom').value = row.getAttribute('data-deliver_from') || '';
    document.getElementById('newDeliverTo').value = row.getAttribute('data-deliver_to') || '';
    document.getElementById('newStatusRow').classList.remove('hidden');
    document.getElementById('newStatus').value = (row.getAttribute('data-status') || 'pending').toLowerCase();
    document.getElementById('newBuyerType').value = row.getAttribute('data-buyer_type') || 'company';
    document.getElementById('newProd').value = row.getAttribute('data-product') || '';
    document.getElementById('newQty').value = row.getAttribute('data-quantity') || 0;
    document.getElementById('newPrice').value = row.getAttribute('data-unit_price') || 0;
    document.getElementById('newOtherCharges').value = row.getAttribute('data-other_charges') || 0;
    document.getElementById('newOtherChargesNote').value = row.getAttribute('data-other_charges_note') || '';
    // Show modal
    const modal = document.getElementById('quoteDrawer');
    modal.classList.remove('opacity-0');
    modal.classList.remove('pointer-events-none');
    setTimeout(() => {
        modal.classList.add('opacity-100');
    }, 10);
}

function closeQuoteDrawer() {
    const modal = document.getElementById('quoteDrawer');
    modal.classList.remove('opacity-100');
    modal.classList.add('opacity-0');
    modal.classList.add('pointer-events-none');
    // Optionally, after transition, you could reset fields if needed
}

window.closeQuoteDrawer = closeQuoteDrawer;
}
}

window.draftQuotation = function(btn) {
    const row = btn.closest('tr');
    document.getElementById('draftPrevId').textContent = row.getAttribute('data-id') || '—';
    document.getElementById('draftPrevDate').textContent = row.getAttribute('data-date') || '';
    document.getElementById('draftPrevBuyer').textContent = row.getAttribute('data-client') || '—';
    document.getElementById('draftPrevTitle').textContent = row.getAttribute('data-title') || '—';
    document.getElementById('draftPrevType').textContent = row.getAttribute('data-buyer_type') || '—';
    document.getElementById('draftPrevCategory').textContent = row.getAttribute('data-category') || '—';
    document.getElementById('draftPrevSupplier').textContent = row.getAttribute('data-supplier') || '—';
    document.getElementById('draftPrevProduct').textContent = row.getAttribute('data-product') || '—';
    document.getElementById('draftPrevQty').textContent = row.getAttribute('data-quantity') || '—';
    document.getElementById('draftPrevUnitPrice').textContent = row.getAttribute('data-unit_price') || '—';
    const qty = parseFloat(row.getAttribute('data-quantity')) || 0;
    const price = parseFloat(row.getAttribute('data-unit_price')) || 0;
    document.getElementById('draftPrevSubtotal').textContent = (qty && price) ? (qty * price).toFixed(2) : '—';
    document.getElementById('draftPrevOtherCharges').textContent = row.getAttribute('data-other_charges') || '—';
    document.getElementById('draftPrevOtherChargesNote').textContent = row.getAttribute('data-other_charges_note') || '—';
    const total = (qty * price) + (parseFloat(row.getAttribute('data-other_charges')) || 0);
    document.getElementById('draftPrevTotal').textContent = total.toFixed(2);
    document.getElementById('draftPrevDeliverFrom').textContent = row.getAttribute('data-deliver_from') || '—';
    document.getElementById('draftPrevDeliverTo').textContent = row.getAttribute('data-deliver_to') || '—';
    document.getElementById('draftPrevStatus').textContent = row.getAttribute('data-status') || '—';
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
