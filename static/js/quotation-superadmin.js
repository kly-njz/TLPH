// quotation-superadmin.js
// Handles modal logic and workflow actions for superadmin quotation page

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
    document.getElementById('editIssueDate').value = data.issue_date || '';
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

// Handle form submit for updating quotation
const quoteForm = document.getElementById('newQuoteForm');
if (quoteForm) {
    quoteForm.onsubmit = async function(e) {
        e.preventDefault();
        const quoteId = document.getElementById('editQuoteId').value;
        const payload = {
            buyer: document.getElementById('newBuyer').value,
            title: document.getElementById('newTitle').value,
            category: document.getElementById('newCategory').value,
            supplier: document.getElementById('newSupplier').value,
            deliver_from: document.getElementById('newDeliverFrom').value,
            deliver_to: document.getElementById('newDeliverTo').value,
            status: document.getElementById('newStatus').value,
            buyer_type: document.getElementById('newBuyerType').value,
            product: document.getElementById('newProd').value,
            quantity: document.getElementById('newQty').value,
            unit_price: document.getElementById('newPrice').value,
            other_charges: document.getElementById('newOtherCharges').value,
            other_charges_note: document.getElementById('newOtherChargesNote').value
        };
        const res = await fetch(`/superadmin/api/quotation/${quoteId}/update`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        const data = await res.json();
        if (res.ok && data.success) {
            alert('Quotation updated successfully.');
            closeQuoteDrawer();
            window.location.reload();
        } else {
            alert(data.error || 'Failed to update quotation.');
        }
    }
}
