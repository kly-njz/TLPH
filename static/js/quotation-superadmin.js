// Show draft preview modal for a quotation
async function openDraftPreview(quoteId) {
    const res = await fetch(`/superadmin/api/quotation/${quoteId}`);
    if (!res.ok) {
        alert('Failed to fetch quotation data.');
        return;
    }
    const data = await res.json();
    // Populate preview modal fields
    document.getElementById('draftPrevId').textContent = data.id || '—';
    document.getElementById('draftPrevDate').textContent = data.issue_date || '—';
    document.getElementById('draftPrevBuyer').textContent = data.buyer || '—';
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
